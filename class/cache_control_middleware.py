"""
Cache Control Middleware - Prevents stale content from being served
Ensures HTML pages are never cached, but static assets are cached aggressively
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse


class CacheControlMiddleware(MiddlewareMixin):
    """
    Sets appropriate Cache-Control headers based on content type.
    
    - HTML pages: No caching (always fresh)
    - Static assets (CSS, JS, images): Cache for 1 year
    - API responses: No caching
    """
    
    def process_response(self, request, response):
        # Don't cache HTML pages - MOST IMPORTANT
        if response.get('Content-Type', '').startswith('text/html'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['ETag'] = None  # Remove ETag to force revalidation
        
        # Cache static assets for 1 year (they have version numbers)
        elif any(request.path.startswith(prefix) for prefix in ['/static/', '/media/']):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        
        # Don't cache API responses
        elif request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Don't cache service worker
        elif request.path == '/service-worker.js' or request.path.endswith('service-worker.js'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
