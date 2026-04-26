"""
Custom error handlers for user-friendly error pages
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseNotFound, HttpResponseForbidden, HttpResponseServerError
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


def custom_404_handler(request, exception=None):
    """
    Custom 404 handler that provides user-friendly error pages
    """
    # Log the 404 for monitoring
    logger.warning(f"404 error on {request.path} for user {request.user}")
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        # For unauthenticated users, redirect to login with helpful message
        request.session['next_url'] = request.get_full_path()
        messages.info(
            request,
            "The page you're looking for requires authentication. Please log in to continue."
        )
        return redirect('login')
    
    # For authenticated users, show user-friendly 404 page
    context = {
        'error_title': 'Page Not Found',
        'error_message': 'The page you\'re looking for doesn\'t exist or may have been moved.',
        'suggestions': [
            'Check the URL for typos',
            'Use the navigation menu to find what you\'re looking for',
            'Go back to your dashboard and try again',
            'Contact support if you believe this page should exist'
        ],
        'show_dashboard_link': True,
        'requested_url': request.get_full_path(),
    }
    
    return render(request, 'errors/user_friendly_404.html', context, status=404)


def custom_403_handler(request, exception=None):
    """
    Custom 403 handler for permission denied errors
    """
    # Log the permission denied for security monitoring
    logger.warning(f"403 error on {request.path} for user {request.user}")
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        # Redirect unauthenticated users to login
        request.session['next_url'] = request.get_full_path()
        messages.info(
            request,
            "Please log in to access this page."
        )
        return redirect('login')
    
    # For authenticated users, show permission denied page
    context = {
        'error_title': 'Access Denied',
        'error_message': 'You don\'t have permission to access this page.',
        'suggestions': [
            'Contact your administrator if you need access to this page',
            'Make sure you\'re logged in with the correct account',
            'Check if your account has the necessary permissions',
            'Return to your dashboard to access available features'
        ],
        'show_dashboard_link': True,
        'requested_url': request.get_full_path(),
    }
    
    return render(request, 'errors/user_friendly_403.html', context, status=403)


def custom_500_handler(request):
    """
    Custom 500 handler for server errors
    """
    # Log the server error
    logger.error(f"500 error on {request.path} for user {request.user}")
    
    context = {
        'error_title': 'Something Went Wrong',
        'error_message': 'We encountered an unexpected error. Our team has been notified and is working to fix it.',
        'suggestions': [
            'Try refreshing the page',
            'Go back and try again',
            'Clear your browser cache and cookies',
            'Contact support if the problem persists'
        ],
        'show_dashboard_link': request.user.is_authenticated if hasattr(request, 'user') else False,
        'error_id': getattr(request, 'session', {}).get('session_key', 'unknown')[:8] if hasattr(request, 'session') else 'unknown',
    }
    
    return render(request, 'errors/user_friendly_500.html', context, status=500)


def custom_400_handler(request, exception=None):
    """
    Custom 400 handler for bad requests
    """
    logger.warning(f"400 error on {request.path} for user {getattr(request, 'user', 'anonymous')}")
    
    context = {
        'error_title': 'Bad Request',
        'error_message': 'The request could not be processed due to invalid data.',
        'suggestions': [
            'Check that all required fields are filled out correctly',
            'Make sure you\'re using the correct format for dates and numbers',
            'Try refreshing the page and submitting again',
            'Contact support if you continue to have issues'
        ],
        'show_dashboard_link': request.user.is_authenticated if hasattr(request, 'user') else False,
    }
    
    return render(request, 'errors/user_friendly_400.html', context, status=400)