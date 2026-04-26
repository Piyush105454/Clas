"""
Database Connection Error Handling Middleware
Handles stale database connections and reconnects automatically
"""

from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


class DatabaseConnectionMiddleware(MiddlewareMixin):
    """
    Middleware to handle database connection errors
    Automatically reconnects if connection is stale
    """
    
    def process_request(self, request):
        """
        Ensure database connection is active before processing request.
        For remote databases (e.g. Neon), we validate the connection instead of 
        forcibly closing/opening it to avoid SSL/TLS handshake latency.
        """
        try:
            # ONLY ensure connection is active (reconnects only if needed)
            # DONT call connection.close() here as it adds 2-3s of lag per request
            connection.ensure_connection()
            return None
        
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            
            # Try to reconnect
            try:
                connection.close()
                connection.ensure_connection()
                logger.info("Database connection re-established")
                return None
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to database: {str(reconnect_error)}")
                messages.error(request, "Database connection error. Please try again.")
                return None
    
    def process_exception(self, request, exception):
        """
        Handle database-related exceptions
        """
        exception_str = str(exception).lower()
        
        # Check for common database connection errors
        if any(error in exception_str for error in [
            'connection refused',
            'connection reset',
            'connection timeout',
            'lost connection',
            'server closed the connection',
            'connection pool exhausted',
            'no connection',
        ]):
            logger.warning(f"Database connection issue detected: {str(exception)}")
            
            # Try to reconnect
            try:
                connection.close()
                connection.ensure_connection()
                logger.info("Reconnected to database after error")
            except Exception as e:
                logger.error(f"Failed to reconnect: {str(e)}")
            
            # Return None to let Django handle the error normally
            return None
        
        return None
