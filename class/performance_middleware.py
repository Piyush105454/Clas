"""
Performance optimization middleware for faster page loads and smooth interactions.
Handles HTTP caching headers, compression, and response optimization.
"""

from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.http import condition
from django.http import HttpResponse
import gzip
import io


class PerformanceOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware to optimize performance with:
    - HTTP caching headers
    - Response compression
    - Browser caching directives
    """
    
    def process_response(self, request, response):
        """Add performance optimization headers to response"""
        
        # Add cache control headers for static files
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['X-Content-Type-Options'] = 'nosniff'
        
        # Security and other headers follow...
        
        # Add security headers
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add performance headers
        response['X-UA-Compatible'] = 'IE=edge'
        response['Vary'] = 'Accept-Encoding'
        
        # Enable compression for text-based responses
        if response.get('Content-Type', '').startswith('text/'):
            if 'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', ''):
                response['Content-Encoding'] = 'gzip'
        
        return response


class BrowserCachingMiddleware(MiddlewareMixin):
    """
    Middleware to handle browser caching for improved performance.
    """
    
    def process_response(self, request, response):
        """Set appropriate caching headers based on content type"""
        
        # Cache images for 1 year
        if request.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Expires'] = 'Thu, 31 Dec 2099 23:59:59 GMT'
        
        # Cache fonts for 1 year
        elif request.path.endswith(('.woff', '.woff2', '.ttf', '.eot')):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Expires'] = 'Thu, 31 Dec 2099 23:59:59 GMT'
        
        # Cache CSS and JS for 1 year
        elif request.path.endswith(('.css', '.js')):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Expires'] = 'Thu, 31 Dec 2099 23:59:59 GMT'
        
        # Don't cache HTML pages (except static pages)
        elif request.path.endswith('.html') or not request.path.startswith('/static/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response


class ResponseCompressionMiddleware(MiddlewareMixin):
    """
    Middleware to compress responses for faster transfer.
    """
    
    def process_response(self, request, response):
        """Compress response if client supports gzip"""
        
        # Check if client accepts gzip
        if 'gzip' not in request.META.get('HTTP_ACCEPT_ENCODING', ''):
            return response
        
        # [STRICT SAFETY] Only compress text-based content
        content_type = response.get('Content-Type', '').lower()
        if not any(t in content_type for t in ['text/', 'json', 'javascript', 'xml']):
            return response
            
        # [STRICT SAFETY] Skip streaming responses (FileResponse, etc.)
        if getattr(response, 'streaming', False):
            return response
            
        try:
            # Don't compress small responses
            if len(response.content) < 1024:
                return response
                
            gzip_buffer = io.BytesIO()
            gzip_file = gzip.GzipFile(mode='wb', fileobj=gzip_buffer)
            gzip_file.write(response.content)
            gzip_file.close()
            
            response.content = gzip_buffer.getvalue()
            response['Content-Encoding'] = 'gzip'
            response['Content-Length'] = len(response.content)
        except (AttributeError, Exception):
            # Fallback for any unexpected response types
            pass
        
        return response
