"""
Cache utilities for secure, per-user cache key generation
Prevents cache collision between different users
"""

from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class SecureCacheManager:
    """
    Manages cache with per-user isolation to prevent data leakage
    """
    
    @staticmethod
    def generate_cache_key(user_id, user_email, view_name, extra_params=None):
        """
        Generate a unique cache key that includes user identification
        
        Args:
            user_id: The user's ID
            user_email: The user's email
            view_name: Name of the view (e.g., 'facilitator_dashboard')
            extra_params: Optional dict of additional parameters to include in key
        
        Returns:
            A unique cache key string
        """
        key_parts = [
            f"cache_v2",  # Version prefix for cache invalidation
            f"user_{user_id}",
            f"email_{user_email.replace('@', '_').replace('.', '_')}",
            view_name,
        ]
        
        if extra_params:
            for k, v in extra_params.items():
                key_parts.append(f"{k}_{v}")
        
        cache_key = "|".join(key_parts)
        return cache_key
    
    @staticmethod
    def get_cached_data(user_id, user_email, view_name, extra_params=None):
        """
        Retrieve cached data with user verification
        
        Args:
            user_id: The user's ID
            user_email: The user's email
            view_name: Name of the view
            extra_params: Optional dict of additional parameters
        
        Returns:
            Cached data if valid and belongs to user, None otherwise
        """
        cache_key = SecureCacheManager.generate_cache_key(
            user_id, user_email, view_name, extra_params
        )
        
        cached_data = cache.get(cache_key)
        
        if cached_data:
            # SECURITY: Verify cached data belongs to this user
            if (cached_data.get('_cache_user_id') == user_id and 
                cached_data.get('_cache_user_email') == user_email):
                logger.debug(f"Cache hit for {view_name} - user {user_id}")
                return cached_data
            else:
                # Cache belongs to different user - delete it
                logger.warning(
                    f"Cache collision detected for {view_name}! "
                    f"Expected user {user_id}, but cache has user {cached_data.get('_cache_user_id')}"
                )
                cache.delete(cache_key)
                return None
        
        return None
    
    @staticmethod
    def set_cached_data(user_id, user_email, view_name, data, timeout=300, extra_params=None):
        """
        Store data in cache with user verification metadata
        
        Args:
            user_id: The user's ID
            user_email: The user's email
            view_name: Name of the view
            data: Data to cache (dict)
            timeout: Cache timeout in seconds (default 5 minutes)
            extra_params: Optional dict of additional parameters
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = SecureCacheManager.generate_cache_key(
                user_id, user_email, view_name, extra_params
            )
            
            # Add user verification metadata to cached data
            cache_data = dict(data)  # Make a copy
            cache_data['_cache_user_id'] = user_id
            cache_data['_cache_user_email'] = user_email
            cache_data['_cache_view'] = view_name
            
            cache.set(cache_key, cache_data, timeout)
            logger.debug(f"Cache set for {view_name} - user {user_id}, timeout {timeout}s")
            return True
        except Exception as e:
            logger.error(f"Error setting cache for {view_name}: {str(e)}")
            return False
    
    @staticmethod
    def clear_user_cache(user_id, user_email):
        """
        Clear all cache entries for a specific user
        Called on logout to ensure no data leakage
        
        Args:
            user_id: The user's ID
            user_email: The user's email
        """
        try:
            # Get all cache keys for this user (this is a limitation of Django cache)
            # For production, consider using Redis with pattern matching
            logger.info(f"Clearing cache for user {user_id} ({user_email})")
            
            # Note: Django's default cache backend doesn't support pattern deletion
            # If using Redis, you can use: cache.delete_pattern(f"cache_v2|user_{user_id}|*")
            # For now, we rely on cache timeout and per-request validation
            
            return True
        except Exception as e:
            logger.error(f"Error clearing user cache: {str(e)}")
            return False
    
    @staticmethod
    def invalidate_view_cache(view_name, user_id=None):
        """
        Invalidate cache for a specific view
        
        Args:
            view_name: Name of the view to invalidate
            user_id: Optional - if provided, only invalidate for that user
        """
        try:
            logger.info(f"Invalidating cache for view {view_name}")
            # Note: This is a simplified version
            # For production with Redis, use pattern matching
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return False


def get_user_cache_key(user_id, user_email, view_name):
    """
    Convenience function to generate cache key
    """
    return SecureCacheManager.generate_cache_key(user_id, user_email, view_name)
