"""
Middleware to handle file upload errors gracefully.
Provides better error messages for 413 and other upload-related errors.
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.views.decorators.http import condition
import logging

logger = logging.getLogger(__name__)


class FileUploadErrorMiddleware(MiddlewareMixin):
    """
    Middleware to catch and handle file upload errors.
    Provides user-friendly error messages for upload failures.
    """
    
    def process_exception(self, request, exception):
        """
        Handle exceptions during file upload.
        """
        
        # Check if this is a file upload request
        if not request.path.startswith('/api/upload-') and not request.path.startswith('/api/save-'):
            return None
        
        # Handle request entity too large (413)
        if hasattr(exception, 'status_code') and exception.status_code == 413:
            logger.warning(f"File upload too large from {request.user.email if request.user.is_authenticated else 'anonymous'}")
            
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'success': False,
                    'error': 'File too large. Maximum size is 100MB. Please check your Nginx configuration if this persists.',
                    'error_code': 'FILE_TOO_LARGE'
                }, status=413)
        
        return None
    
    def process_request(self, request):
        """
        Pre-process upload requests to validate early.
        """
        
        # Check if this is a file upload request
        if not request.method == 'POST':
            return None
        
        if not (request.path.startswith('/api/upload-') or request.path.startswith('/api/save-')):
            return None
        
        # Check content length header
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                content_length = int(content_length)
                # 100MB limit
                max_size = 100 * 1024 * 1024
                
                if content_length > max_size:
                    logger.warning(
                        f"Upload request exceeds limit: {content_length} bytes "
                        f"from {request.user.email if request.user.is_authenticated else 'anonymous'}"
                    )
                    
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'success': False,
                            'error': f'File too large ({content_length / (1024*1024):.1f}MB). Maximum size is 100MB.',
                            'error_code': 'FILE_TOO_LARGE'
                        }, status=413)
            except (ValueError, TypeError):
                pass
        
        return None
