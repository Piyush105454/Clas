"""
Middleware to bypass authentication for PWA files.
This ensures service worker and manifest can be accessed without login.
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
import os
from django.conf import settings


class PWAAuthBypassMiddleware(MiddlewareMixin):
    """
    Bypass authentication for PWA-related files.
    This must run BEFORE authentication middleware.
    """
    
    PWA_PATHS = [
        '/service-worker.js',
        '/manifest.json',
        '/offline/',
        '/offline-sync.js',
        '/resource-prioritization.js',
        '/static/manifest.json',
        '/static/icons/',
    ]
    
    def process_request(self, request):
        """
        Check if request is for a PWA file and bypass auth if needed.
        """
        path = request.path
        
        # Check if this is a PWA file request
        for pwa_path in self.PWA_PATHS:
            if path.startswith(pwa_path) or path == pwa_path:
                # Mark request as PWA file so auth middleware can skip it
                request.is_pwa_file = True
                return None
        
        return None
