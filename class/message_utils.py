"""
Utility functions for message handling
"""

from django.contrib import messages
import time


def add_timestamped_message(request, level, message_text):
    """
    Add a message with a timestamp for tracking age
    """
    timestamp = str(time.time())
    
    if level == 'success':
        messages.success(request, message_text, extra_tags=timestamp)
    elif level == 'error':
        messages.error(request, message_text, extra_tags=timestamp)
    elif level == 'warning':
        messages.warning(request, message_text, extra_tags=timestamp)
    elif level == 'info':
        messages.info(request, message_text, extra_tags=timestamp)
    else:
        messages.add_message(request, messages.INFO, message_text, extra_tags=timestamp)


def clear_old_messages(request, max_age_seconds=60):
    """
    Clear messages older than max_age_seconds
    """
    storage = messages.get_messages(request)
    current_time = time.time()
    
    fresh_messages = []
    cleared_count = 0
    
    for message in storage:
        if hasattr(message, 'extra_tags') and message.extra_tags:
            try:
                message_time = float(message.extra_tags)
                if (current_time - message_time) <= max_age_seconds:
                    fresh_messages.append(message)
                else:
                    cleared_count += 1
            except (ValueError, TypeError):
                fresh_messages.append(message)  # Keep if invalid timestamp
        else:
            fresh_messages.append(message)  # Keep if no timestamp
    
    # Replace messages with fresh ones
    storage._loaded_messages = fresh_messages
    
    return cleared_count


def suppress_debug_messages(request):
    """
    Remove debug-related messages from the message storage
    """
    from django.conf import settings
    
    if not settings.DEBUG:
        storage = messages.get_messages(request)
        
        filtered_messages = []
        for message in storage:
            message_text = str(message).lower()
            
            # Skip debug-related messages
            if any(debug_term in message_text for debug_term in [
                'debug', 'traceback', 'sql', 'query', 'warning:', 'error:'
            ]):
                continue
            
            filtered_messages.append(message)
        
        storage._loaded_messages = filtered_messages