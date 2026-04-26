"""
Custom middleware for CLAS application
"""

from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
import time


class MessageCleanupMiddleware(MiddlewareMixin):
    """
    Middleware to automatically clean up old messages and prevent message spam
    """
    
    def process_request(self, request):
        """
        Clean up old messages before processing the request
        """
        # Check if this is a fresh page load (not an AJAX request)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # If it's been more than 30 seconds since last message, clear old success messages
        current_time = time.time()
        last_message_time = request.session.get('last_message_time', 0)
        
        if current_time - last_message_time > 30:  # 30 seconds
            # Clear messages by consuming them (this is the proper way)
            storage = messages.get_messages(request)
            # Consume all messages to clear them
            for message in storage:
                pass  # Just iterate through to consume them
        
        return None
    
    def process_response(self, request, response):
        """
        Update message timestamp after processing response
        """
        # Update last message time if there are messages
        storage = messages.get_messages(request)
        if len(storage._queued_messages) > 0:
            request.session['last_message_time'] = time.time()
        
        return response


class DebugMessageSuppressMiddleware(MiddlewareMixin):
    """
    Middleware to suppress debug messages in production
    """
    
    def process_request(self, request):
        """
        Filter out debug messages if not in debug mode
        """
        from django.conf import settings
        
        if not settings.DEBUG:
            # Get current messages
            storage = messages.get_messages(request)
            
            # Filter out debug-related messages by consuming and re-adding only valid ones
            valid_messages = []
            for message in storage:
                message_text = str(message).lower()
                
                # Skip debug-related messages
                if not any(debug_term in message_text for debug_term in [
                    'debug', 'traceback', 'error:', 'warning:', 'info:'
                ]):
                    valid_messages.append((message.level, message.message, message.extra_tags))
            
            # Re-add valid messages
            for level, message_text, extra_tags in valid_messages:
                messages.add_message(request, level, message_text, extra_tags=extra_tags)
        
        return None