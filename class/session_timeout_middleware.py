"""
Session timeout and user-friendly error handling middleware
"""

from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth import logout
from django.http import Http404, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
import time
import logging

logger = logging.getLogger(__name__)


class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Middleware to handle session timeouts gracefully with user-friendly messages
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        # Timeout in seconds (default: 1 hour)
        self.timeout = getattr(settings, 'SESSION_TIMEOUT', 3600)
        
        # URLs that don't require authentication
        self.exempt_urls = [
            '/',  # Root path is the login page
            '/admin/login/',  # Django admin login
            '/static/',
            '/media/',
        ]
        
        # Role-based dashboard URLs
        self.dashboard_urls = {
            'ADMIN': '/admin/dashboard/',
            'SUPERVISOR': '/supervisor/dashboard/',
            'FACILITATOR': '/facilitator/dashboard/',
        }
    
    def process_request(self, request):
        """
        Check session timeout and handle expired sessions
        """
        # Skip for exempt URLs
        if any(request.path.startswith(url) for url in self.exempt_urls):
            return None
        
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return self._handle_unauthenticated_access(request)
        
        # Check session timeout
        current_time = time.time()
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            time_since_activity = current_time - last_activity
            
            if time_since_activity > self.timeout:
                return self._handle_session_timeout(request)
        
        # Update last activity time
        request.session['last_activity'] = current_time
        
        return None
    
    def _handle_unauthenticated_access(self, request):
        """
        Handle access by unauthenticated users to protected URLs
        """
        # Store the original URL for post-login redirect
        request.session['next_url'] = request.get_full_path()
        
        # Only add message for non-login pages
        if not request.path.startswith('/login'):
            messages.info(
                request, 
                "Please log in to access this page."
            )
        
        return redirect('/login/')
    
    def _handle_session_timeout(self, request):
        """
        Handle session timeout with user-friendly messaging
        """
        # Store the original URL for post-login redirect
        original_url = request.get_full_path()
        
        # Log out the user
        logout(request)
        
        # Store redirect URL in new session
        request.session['next_url'] = original_url
        request.session['session_expired'] = True
        
        # Add user-friendly timeout message
        messages.warning(
            request,
            "Your session has expired due to inactivity. Please log in again to continue where you left off."
        )
        
        logger.info(f"Session timeout for user accessing {original_url}")
        
        return redirect('/')
    
    def _redirect_to_appropriate_dashboard(self, request, message=None):
        """
        Redirect user to their appropriate dashboard based on role
        """
        if message:
            messages.info(request, message)
        
        if request.user.is_authenticated:
            role_name = request.user.role.name.upper()
            dashboard_url = self.dashboard_urls.get(role_name, '/admin/dashboard/')
            return redirect(dashboard_url)
        else:
            return redirect('/')


class UserFriendlyErrorMiddleware(MiddlewareMixin):
    """
    Middleware to convert technical errors into user-friendly messages
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_exception(self, request, exception):
        """
        Convert technical exceptions to user-friendly responses
        """
        # Don't handle in debug mode - let Django show the technical error
        if settings.DEBUG:
            return None
        
        # Log the actual error for debugging
        logger.error(f"Error on {request.path}: {str(exception)}", exc_info=True)
        
        # Handle different types of errors
        if isinstance(exception, Http404):
            return self._handle_user_friendly_404(request)
        elif isinstance(exception, PermissionDenied):
            return self._handle_user_friendly_permission_denied(request)
        else:
            return self._handle_generic_error(request)
    
    def _handle_user_friendly_404(self, request):
        """
        Handle 404 with user-friendly response
        """
        # Check if user is authenticated
        if not request.user.is_authenticated:
            # For unauthenticated users, redirect to login with helpful message
            request.session['next_url'] = request.get_full_path()
            messages.info(
                request,
                "The page you're looking for requires authentication. Please log in to continue."
            )
            return redirect('/')
        
        # For authenticated users, show user-friendly message and redirect to dashboard
        messages.error(
            request,
            "The page you're looking for doesn't exist or may have been moved. You've been redirected to your dashboard."
        )
        
        # Redirect to appropriate dashboard
        role_name = request.user.role.name.upper()
        dashboard_urls = {
            'ADMIN': '/admin/dashboard/',
            'SUPERVISOR': '/supervisor/dashboard/',
            'FACILITATOR': '/facilitator/dashboard/',
        }
        dashboard_url = dashboard_urls.get(role_name, '/admin/dashboard/')
        return redirect(dashboard_url)
    
    def _handle_user_friendly_permission_denied(self, request):
        """
        Handle permission denied with user-friendly response
        """
        if not request.user.is_authenticated:
            return self._handle_unauthenticated_access(request)
        else:
            messages.error(
                request,
                "You don't have permission to access that page. Contact your administrator if you believe this is an error."
            )
            # Redirect to appropriate dashboard
            role_name = request.user.role.name.upper()
            dashboard_urls = {
                'ADMIN': '/admin/dashboard/',
                'SUPERVISOR': '/supervisor/dashboard/',
                'FACILITATOR': '/facilitator/dashboard/',
            }
            dashboard_url = dashboard_urls.get(role_name, '/admin/dashboard/')
            return redirect(dashboard_url)
    
    def _handle_generic_error(self, request):
        """
        Handle generic errors with user-friendly response
        """
        messages.error(
            request,
            "We encountered an unexpected error. Our team has been notified. Please try again or contact support if the problem persists."
        )
        
        # Redirect to appropriate page
        if request.user.is_authenticated:
            role_name = request.user.role.name.upper()
            dashboard_urls = {
                'ADMIN': '/admin/dashboard/',
                'SUPERVISOR': '/supervisor/dashboard/',
                'FACILITATOR': '/facilitator/dashboard/',
            }
            dashboard_url = dashboard_urls.get(role_name, '/admin/dashboard/')
            return redirect(dashboard_url)
        else:
            return redirect('/')
    
    def _handle_unauthenticated_access(self, request):
        """
        Handle access by unauthenticated users
        """
        request.session['next_url'] = request.get_full_path()
        messages.info(
            request,
            "Please log in to access this page."
        )
        return redirect('/')


class PostLoginRedirectMiddleware(MiddlewareMixin):
    """
    Middleware to handle post-login redirects intelligently
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Handle post-login redirect logic
        """
        # Only process for login page (root path)
        if request.path != '/':
            return None
        
        # Only for POST requests (actual login attempts)
        if request.method != 'POST':
            return None
        
        # This will be handled in the login view itself
        return None