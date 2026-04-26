"""
Custom template tags for message handling
"""

from django import template
from django.contrib import messages
import time

register = template.Library()


@register.filter
def is_recent_message(message, max_age_seconds=30):
    """
    Check if a message is recent (within max_age_seconds)
    """
    # If message has a timestamp in extra_tags, check if it's recent
    if hasattr(message, 'extra_tags') and message.extra_tags:
        try:
            message_time = float(message.extra_tags)
            current_time = time.time()
            return (current_time - message_time) <= max_age_seconds
        except (ValueError, TypeError):
            pass
    
    # If no timestamp, consider it recent
    return True


@register.filter
def filter_debug_messages(message_list):
    """
    Filter out debug messages from the message list
    """
    filtered = []
    for message in message_list:
        message_text = str(message).lower()
        
        # Skip debug-related messages
        if any(debug_term in message_text for debug_term in [
            'debug', 'traceback', 'sql', 'query'
        ]):
            continue
            
        filtered.append(message)
    
    return filtered


@register.simple_tag
def clean_old_messages(request):
    """
    Clean old messages from the request - simplified version
    """
    # Just return empty string - actual cleanup is handled by middleware
    return ""