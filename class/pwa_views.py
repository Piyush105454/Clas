"""
PWA (Progressive Web App) views for offline support.
Note: Manifest is served as static file (static/manifest.json) via Nginx
"""

from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import os


# Manifest is now served as static file - no Django view needed
# This keeps it clean and avoids conflicts between static and dynamic serving


def pwa_exempt(view_func):
    """
    Decorator to exempt a view from login_required and other auth checks.
    Used for PWA files that must be accessible without authentication.
    """
    view_func.pwa_exempt = True
    return view_func


@require_http_methods(["GET"])
@csrf_exempt
@pwa_exempt
def service_worker(request):
    """
    Serve service worker from root with proper headers.
    This allows the service worker to control the entire app scope (/).
    
    Requirements: 1.2, 1.3, 1.4, 1.5
    """
    service_worker_path = os.path.join(settings.BASE_DIR, 'static', 'service-worker.js')
    
    try:
        with open(service_worker_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
        # Critical headers for service worker
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)


@require_http_methods(["GET"])
@csrf_exempt
@pwa_exempt
def manifest(request):
    """
    Serve PWA manifest with proper headers.
    
    Requirements: 1.1
    """
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        response = JsonResponse(content)
        response['Cache-Control'] = 'public, max-age=3600'
        response['Content-Type'] = 'application/manifest+json'
        return response
    except FileNotFoundError:
        return JsonResponse({'error': 'Manifest not found'}, status=404)


@require_http_methods(["GET"])
def offline(request):
    """
    Serve offline fallback page when user navigates to uncached routes while offline.
    
    Requirements: 4.2, 4.4
    """
    from django.shortcuts import render
    return render(request, 'offline.html')
