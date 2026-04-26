"""
Performance optimization mixins for CLAS views
"""
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q, Count
from django.db import models
import time
import logging

logger = logging.getLogger(__name__)


class PerformanceOptimizedMixin:
    """
    Mixin to add performance optimizations to views
    """
    cache_timeout = 300  # 5 minutes default
    paginate_by = 50  # Default pagination
    
    def dispatch(self, request, *args, **kwargs):
        """Add performance monitoring to all requests"""
        start_time = time.time()
        response = super().dispatch(request, *args, **kwargs)
        
        # Log slow queries
        if hasattr(connection, 'queries'):
            query_time = sum(float(q['time']) for q in connection.queries)
            total_time = time.time() - start_time
            
            if total_time > 1.0:  # Log requests taking more than 1 second
                logger.warning(
                    f"Slow request: {request.path} took {total_time:.2f}s "
                    f"with {len(connection.queries)} queries ({query_time:.2f}s)"
                )
        
        return response

    def get_cached_queryset(self, cache_key, queryset_func, timeout=None):
        """
        Generic method to cache querysets
        """
        if timeout is None:
            timeout = self.cache_timeout
            
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
            
        data = queryset_func()
        cache.set(cache_key, data, timeout)
        return data


class OptimizedListMixin(PerformanceOptimizedMixin):
    """
    Mixin for optimized list views with pagination and caching
    """
    
    def get_optimized_queryset(self):
        """
        Override this method to provide optimized queryset with select_related/prefetch_related
        """
        return self.get_queryset()
    
    def get_paginated_context(self, queryset, page_number=1):
        """
        Get paginated context with performance optimizations
        """
        paginator = Paginator(queryset, self.paginate_by)
        page_obj = paginator.get_page(page_number)
        
        return {
            'object_list': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
            'is_paginated': page_obj.has_other_pages(),
        }


class CachedViewMixin:
    """
    Mixin to add caching to views
    """
    cache_key_prefix = 'view'
    cache_timeout = 300
    
    def get_cache_key(self, *args, **kwargs):
        """Generate cache key for this view"""
        key_parts = [
            self.cache_key_prefix,
            self.__class__.__name__,
            str(self.request.user.id) if self.request.user.is_authenticated else 'anon',
        ]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}_{v}" for k, v in sorted(kwargs.items()))
        return '_'.join(key_parts)


class AjaxOptimizedMixin:
    """
    Mixin for optimized AJAX responses
    """
    
    def json_response(self, data, status=200):
        """Return optimized JSON response"""
        response = JsonResponse(data, status=status)
        response['Cache-Control'] = 'max-age=300'  # 5 minutes
        return response
    
    def error_response(self, message, status=400):
        """Return standardized error response"""
        return self.json_response({'error': message}, status=status)


class CachedTemplateViewMixin:
    """
    Mixin for template views that can be cached
    """
    
    @method_decorator(cache_page(300))  # Cache for 5 minutes
    @method_decorator(vary_on_headers('User-Agent'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class FacilitatorAccessMixin:
    """
    Mixin to ensure only facilitators can access views and they can only access their assigned schools
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login')
        
        if request.user.role.name.upper() != "FACILITATOR":
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "You do not have permission to access this page.")
            return redirect("no_permission")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_facilitator_schools(self):
        """Get schools assigned to the current facilitator"""
        from .models import FacilitatorSchool, School
        facilitator_school_ids = FacilitatorSchool.objects.filter(
            facilitator=self.request.user,
            is_active=True
        ).values_list('school_id', flat=True)
        
        return School.objects.filter(id__in=facilitator_school_ids)
    
    def get_facilitator_classes(self):
        """Get classes in schools assigned to the current facilitator"""
        from .models import ClassSection
        facilitator_schools = self.get_facilitator_schools()
        
        return ClassSection.objects.filter(
            school__in=facilitator_schools,
            is_active=True
        ).select_related('school').order_by('school__name', 'class_level', 'section')
    
    def get_assigned_class_sections(self):
        """Alias for get_facilitator_classes for backward compatibility"""
        return self.get_facilitator_classes()
    
    def check_school_access(self, school_id):
        """Check if facilitator has access to a specific school"""
        return self.get_facilitator_schools().filter(id=school_id).exists()
    
    def check_class_access(self, class_section_id):
        """Check if facilitator has access to a specific class section"""
        from .models import ClassSection
        try:
            class_section = ClassSection.objects.get(id=class_section_id)
            return self.check_school_access(class_section.school.id)
        except ClassSection.DoesNotExist:
            return False
    
    def verify_school_access_or_403(self, school_id):
        """Verify school access or raise 403"""
        if not self.check_school_access(school_id):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You do not have access to this school.")
    
    def verify_class_access_or_403(self, class_section_id):
        """Verify class access or raise 403"""
        from .models import ClassSection
        try:
            class_section = ClassSection.objects.get(id=class_section_id)
            if not self.check_school_access(class_section.school.id):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You do not have access to this class.")
        except ClassSection.DoesNotExist:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Class section not found.")
    
    def filter_by_assigned_schools(self, queryset):
        """Filter a queryset to only include items from schools assigned to the facilitator"""
        facilitator_schools = self.get_facilitator_schools()
        return queryset.filter(school__in=facilitator_schools)


class DatabaseOptimizedMixin:
    """
    Mixin with common database optimization patterns
    """
    
    def get_schools_with_stats(self):
        """Get schools with related statistics in a single query"""
        from .models import School, ClassSection, Enrollment
        
        return School.objects.select_related().prefetch_related(
            Prefetch(
                'classsection_set',
                queryset=ClassSection.objects.select_related().prefetch_related(
                    Prefetch(
                        'enrollment_set',
                        queryset=Enrollment.objects.filter(is_active=True).select_related('student')
                    )
                )
            )
        ).annotate(
            total_classes=models.Count('classsection', distinct=True),
            total_students=models.Count('classsection__enrollments', 
                                      filter=Q(classsection__enrollments__is_active=True),
                                      distinct=True)
        )
    
    def get_sessions_with_status(self, class_section):
        """Get sessions with their status in optimized way"""
        from .models import PlannedSession, ActualSession
        
        return PlannedSession.objects.filter(
            class_section=class_section
        ).select_related('class_section', 'class_section__school').prefetch_related(
            Prefetch(
                'actual_sessions',
                queryset=ActualSession.objects.select_related('facilitator').order_by('-date')
            )
        ).order_by('day_number')
    
    def get_curriculum_sessions_optimized(self, filters=None):
        """Get curriculum sessions with optimizations"""
        from .models import CurriculumSession
        
        queryset = CurriculumSession.objects.select_related('created_by', 'template')
        
        if filters:
            if filters.get('language'):
                queryset = queryset.filter(language=filters['language'])
            if filters.get('day_from'):
                queryset = queryset.filter(day_number__gte=filters['day_from'])
            if filters.get('day_to'):
                queryset = queryset.filter(day_number__lte=filters['day_to'])
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
        
        return queryset.order_by('language', 'day_number')


class LazyLoadingMixin:
    """
    Mixin to support lazy loading of data
    """
    
    def get_lazy_load_context(self, initial_count=20):
        """
        Get context for lazy loading with initial items
        """
        queryset = self.get_queryset()
        total_count = queryset.count()
        initial_items = queryset[:initial_count]
        
        return {
            'initial_items': initial_items,
            'total_count': total_count,
            'initial_count': initial_count,
            'has_more': total_count > initial_count,
            'load_more_url': self.get_load_more_url(),
        }
    
    def get_load_more_url(self):
        """Override this to provide load more URL"""
        return '#'


# Decorator for caching expensive operations
def cache_expensive_operation(cache_key_func, timeout=300):
    """
    Decorator to cache expensive operations
    
    Usage:
    @cache_expensive_operation(lambda user_id: f'user_stats_{user_id}', timeout=600)
    def get_user_statistics(user_id):
        # expensive operation
        return stats
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            result = cache.get(cache_key)
            
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


# Performance monitoring decorator
def monitor_performance(func):
    """
    Decorator to monitor function performance
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        if execution_time > 0.5:  # Log functions taking more than 500ms
            logger.warning(f"Slow function: {func.__name__} took {execution_time:.2f}s")
        
        return result
    return wrapper