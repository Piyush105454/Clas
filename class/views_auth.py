"""
Authentication views with proper session and localStorage management
"""

from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .services.session_auth_fix import SessionCleanupService
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    Improved login view with proper session management
    """
    if request.method == 'GET':
        # If already logged in, redirect to dashboard
        if request.user.is_authenticated:
            return redirect_to_dashboard(request.user)
        
        return render(request, 'auth/login.html')
    
    # POST request - process login
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    
    if not email or not password:
        messages.error(request, "Please enter both email and password.")
        return render(request, 'auth/login.html')
    
    try:
        # Authenticate user
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            # Clear any old session data
            request.session.flush()
            
            # Login user
            login(request, user)
            
            # Set session activity
            import time
            request.session['last_activity'] = time.time()
            request.session.modified = True
            
            logger.info(f"User {email} logged in successfully")
            messages.success(request, f"Welcome back, {user.full_name}!")
            
            # Redirect to appropriate dashboard
            return redirect_to_dashboard(user)
        else:
            logger.warning(f"Failed login attempt for {email}")
            messages.error(request, "Invalid email or password.")
            return render(request, 'auth/login.html')
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        messages.error(request, "An error occurred during login. Please try again.")
        return render(request, 'auth/login.html')


@require_http_methods(["GET", "POST"])
@login_required(login_url='/login/')
def logout_view(request):
    """
    Improved logout view with proper cleanup
    """
    from django.core.cache import cache
    
    try:
        user_email = request.user.email
        user_id = request.user.id
        
        # Clear user-specific cache entries before logout
        cache_keys_to_clear = [
            f"admin_dashboard_{user_id}",
            f"admin_dashboard_optimized_{user_id}",
            f"facilitator_dashboard_{user_id}",
            f"facilitator_dashboard_optimized_{user_id}",
            f"supervisor_dashboard_optimized_{user_id}",
            f"reports_dashboard_{user_id}",
            f"dashboard_stats_{user_id}",
            f"recent_sessions_{user_id}",
            f"curriculum_updates_{user_id}",
        ]
        
        for cache_key in cache_keys_to_clear:
            cache.delete(cache_key)
        
        # Use the cleanup service
        SessionCleanupService.logout_user(request)
        
        logger.info(f"User {user_email} logged out successfully and cache cleared")
        messages.success(request, "You have been logged out successfully.")
        
        # Redirect to login with clear storage signal
        response = redirect('/login/')
        response['X-Clear-Storage'] = 'true'
        return response
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        messages.error(request, "An error occurred during logout.")
        return redirect('/login/')


@login_required(login_url='/login/')
def session_check_view(request):
    """
    API endpoint to check if session is still valid
    Used by JavaScript to detect session expiration
    """
    if request.user.is_authenticated:
        # Refresh session activity
        import time
        request.session['last_activity'] = time.time()
        request.session.modified = True
        
        return JsonResponse({
            'status': 'valid',
            'user': request.user.email,
            'role': request.user.role.name if request.user.role else 'Unknown'
        })
    else:
        return JsonResponse({'status': 'expired'}, status=401)


@login_required(login_url='/login/')
def clear_session_view(request):
    """
    API endpoint to manually clear session data
    """
    try:
        SessionCleanupService.clear_session_data(request)
        return JsonResponse({'status': 'success', 'message': 'Session data cleared'})
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def redirect_to_dashboard(user):
    """
    Redirect user to appropriate dashboard based on role
    """
    if not user.role:
        logger.error(f"User {user.email} has no role assigned")
        return redirect('/login/')
    
    role_name = user.role.name.lower()
    
    dashboard_urls = {
        'admin': '/admin/dashboard/',
        'supervisor': '/supervisor/dashboard/',
        'facilitator': '/facilitator/dashboard/',
    }
    
    dashboard_url = dashboard_urls.get(role_name, '/login/')
    return redirect(dashboard_url)


# JavaScript helper to include in base template
def get_session_management_script():
    """
    Returns JavaScript code for session management
    Include this in your base template
    """
    return """
    <script>
    // Session Management Script
    (function() {
        // Clear localStorage on logout
        function clearStorage() {
            try {
                localStorage.clear();
                sessionStorage.clear();
                console.log('Storage cleared');
            } catch (e) {
                console.error('Error clearing storage:', e);
            }
        }
        
        // Check if server sent clear storage signal
        document.addEventListener('DOMContentLoaded', function() {
            const clearStorageHeader = document.querySelector('meta[name="X-Clear-Storage"]');
            if (clearStorageHeader) {
                clearStorage();
            }
            
            // Add logout link handlers
            const logoutLinks = document.querySelectorAll('a[href*="logout"], button[data-logout]');
            logoutLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    clearStorage();
                });
            });
        });
        
        // Check session validity every 5 minutes
        setInterval(function() {
            fetch('/api/session/check/', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.status === 401) {
                    // Session expired
                    clearStorage();
                    window.location.href = '/login/';
                }
                return response.json();
            })
            .catch(error => {
                console.error('Session check error:', error);
                // On error, assume session is invalid
                clearStorage();
                window.location.href = '/login/';
            });
        }, 300000); // Check every 5 minutes
        
        // Prevent back button after logout
        window.addEventListener('pageshow', function(event) {
            if (event.persisted) {
                // Page was restored from cache
                fetch('/api/session/check/', {
                    method: 'GET',
                    credentials: 'include'
                })
                .then(response => {
                    if (response.status === 401) {
                        clearStorage();
                        window.location.href = '/login/';
                    }
                });
            }
        });
    })();
    </script>
    """
