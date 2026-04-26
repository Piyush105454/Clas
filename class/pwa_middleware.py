"""
PWA Middleware for setting proper HTTP headers for Service Worker and Manifest.
"""

from django.utils.deprecation import MiddlewareMixin


class PWAHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to set proper HTTP headers for PWA files.
    
    Ensures:
    - Service Worker is served with no-cache headers
    - Manifest is served with correct MIME type
    - Proper cache control headers
    
    Requirements: 3.3
    """
    
    def process_response(self, request, response):
        """
        Add PWA-specific headers to responses.
        """
        
        # Service Worker should never be cached (served from root now)
        if request.path == '/service-worker.js':
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Content-Type'] = 'application/javascript; charset=utf-8'
            response['Service-Worker-Allowed'] = '/'
        
        # Manifest should be cached but checked frequently
        if request.path == '/manifest.json':
            response['Cache-Control'] = 'public, max-age=3600'
            response['Content-Type'] = 'application/manifest+json'
        
        # Offline page should not be cached
        if request.path == '/offline/':
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Icons should be cached long-term
        if '/static/icons/' in request.path:
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 year
            response['Content-Type'] = 'image/png'
        
        return response
