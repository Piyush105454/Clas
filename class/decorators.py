"""
Custom decorators for CLAS application
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def _is_admin(user):
    """Internal helper to check if a user should have full Admin access"""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    
    # Robust check for role (handle both str '0' and int 0)
    role_id = getattr(user.role, 'id', None)
    role_name = getattr(user.role, 'name', '') or ""
    
    # Support both Role ID 0 and name 'ADMIN'
    # Convert to string to avoid int vs UUID vs string issues
    return (role_id is not None and str(role_id) == '0') or role_name.upper() == 'ADMIN'


def facilitator_required(view_func):
    """
    Decorator to ensure only facilitators can access the view
    Handles both regular requests and AJAX requests
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role.name.upper() != "FACILITATOR":
            # For AJAX requests, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            # For regular requests, redirect to no_permission page
            messages.error(request, "You do not have permission to access this page.")
            return redirect("no_permission")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator to ensure only admins can access the view
    Handles both regular requests and AJAX requests
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not _is_admin(request.user):
            # For AJAX requests, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            # For regular requests, redirect to no_permission page
            messages.error(request, "You do not have permission to access this page.")
            return redirect("no_permission")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def supervisor_required(view_func):
    """
    Decorator to ensure only supervisors (or admins) can access the view.
    Admins are also allowed since they have full system access.
    Handles both regular requests and AJAX requests.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Allow any Admin (Role ID 0, name 'Admin', Superuser, or Staff)
        if _is_admin(request.user):
            return view_func(request, *args, **kwargs)
        
        # Check standard Supervisor role
        role_id = request.user.role.id if request.user.role else None
        user_role = (request.user.role.name or "").upper()
        
        if role_id == 1 or user_role == "SUPERVISOR":
            return view_func(request, *args, **kwargs)
            
        # For AJAX requests, return JSON error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # For regular requests, redirect to no_permission page
        messages.error(request, "You do not have permission to access this page.")
        return redirect("no_permission")
    return _wrapped_view


def role_required(*allowed_roles):
    """
    Decorator to ensure only users with specific roles can access the view
    Usage: @role_required('ADMIN', 'SUPERVISOR')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Always allow Admins
            if _is_admin(request.user):
                return view_func(request, *args, **kwargs)
                
            user_role = (request.user.role.name or "").upper()
            allowed_roles_upper = [role.upper() for role in allowed_roles]
            
            if user_role not in allowed_roles_upper:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("no_permission")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator