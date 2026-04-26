"""
Query Optimization Utilities for CLAS Platform
Provides optimized query patterns to prevent N+1 problems
"""

from django.db.models import Count, Q, Prefetch, Avg
from django.core.cache import cache
from .models import (
    Enrollment, Attendance, ActualSession, SessionFeedback,
    FacilitatorSchool, ClassSection, PlannedSession
)


class OptimizedQueries:
    """Collection of optimized query patterns"""
    
    @staticmethod
    def get_facilitator_stats(facilitator_ids):
        """
        Get all stats for facilitators in ONE query instead of N queries
        
        Returns: {
            'sessions': {facilitator_id: count},
            'students': {facilitator_id: count},
            'feedback': {facilitator_id: count},
            'avg_rating': {facilitator_id: rating}
        }
        """
        # Get session counts
        session_counts = ActualSession.objects.filter(
            facilitator_id__in=facilitator_ids,
            status=1
        ).values('facilitator_id').annotate(count=Count('id'))
        sessions_by_facilitator = {
            item['facilitator_id']: item['count'] 
            for item in session_counts
        }
        
        # Get unique student counts
        strength_counts = Attendance.objects.filter(
            actual_session__facilitator_id__in=facilitator_ids,
            actual_session__status=1
        ).values('actual_session__facilitator_id').annotate(
            unique_students=Count('enrollment__student', distinct=True)
        )
        strength_by_facilitator = {
            item['actual_session__facilitator_id']: item['unique_students'] 
            for item in strength_counts
        }
        
        # Get feedback counts
        feedback_counts = SessionFeedback.objects.filter(
            facilitator_id__in=facilitator_ids
        ).values('facilitator_id').annotate(
            count=Count('id')
        )
        feedback_by_facilitator = {
            item['facilitator_id']: {
                'count': item['count'],
                'avg_rating': 0 # Rating field removed from model
            }
            for item in feedback_counts
        }
        
        return {
            'sessions': sessions_by_facilitator,
            'students': strength_by_facilitator,
            'feedback': feedback_by_facilitator
        }
    
    @staticmethod
    def get_school_stats(school_ids):
        """
        Get all stats for schools in ONE query instead of N queries
        
        Returns: {
            'classes': {school_id: count},
            'students': {school_id: count},
            'facilitators': {school_id: count}
        }
        """
        # Get class counts
        class_counts = ClassSection.objects.filter(
            school_id__in=school_ids,
            is_active=True
        ).values('school_id').annotate(count=Count('id'))
        classes_by_school = {
            item['school_id']: item['count'] 
            for item in class_counts
        }
        
        # Get student counts
        student_counts = Enrollment.objects.filter(
            school_id__in=school_ids,
            is_active=True
        ).values('school_id').annotate(count=Count('id', distinct=True))
        students_by_school = {
            item['school_id']: item['count'] 
            for item in student_counts
        }
        
        # Get facilitator counts
        facilitator_counts = FacilitatorSchool.objects.filter(
            school_id__in=school_ids,
            is_active=True
        ).values('school_id').annotate(count=Count('facilitator', distinct=True))
        facilitators_by_school = {
            item['school_id']: item['count'] 
            for item in facilitator_counts
        }
        
        return {
            'classes': classes_by_school,
            'students': students_by_school,
            'facilitators': facilitators_by_school
        }
    
    @staticmethod
    def get_enrollment_with_attendance(school_ids, class_ids=None):
        """
        Get enrollments with attendance stats in optimized way
        
        Returns: QuerySet with prefetched attendance data
        """
        queryset = Enrollment.objects.filter(
            is_active=True,
            school_id__in=school_ids
        ).select_related(
            'student',
            'class_section',
            'school'
        )
        
        if class_ids:
            queryset = queryset.filter(class_section_id__in=class_ids)
        
        # Prefetch attendance with related session data
        queryset = queryset.prefetch_related(
            Prefetch(
                'attendances',
                queryset=Attendance.objects.select_related('actual_session')
            )
        )
        
        return queryset
    
    @staticmethod
    def get_attendance_stats(enrollment_ids):
        """
        Get attendance statistics for enrollments in ONE query
        
        Returns: {
            enrollment_id: {
                'present': count,
                'absent': count,
                'leave': count,
                'percentage': float
            }
        }
        """
        stats = Attendance.objects.filter(
            enrollment_id__in=enrollment_ids
        ).values('enrollment_id').annotate(
            present_count=Count('id', filter=Q(status=1)),
            absent_count=Count('id', filter=Q(status=2)),
            leave_count=Count('id', filter=Q(status=3)),
            total_count=Count('id')
        )
        
        result = {}
        for stat in stats:
            enrollment_id = stat['enrollment_id']
            total = stat['total_count']
            present = stat['present_count']
            
            result[enrollment_id] = {
                'present': present,
                'absent': stat['absent_count'],
                'leave': stat['leave_count'],
                'percentage': (present / total * 100) if total > 0 else 0
            }
        
        return result
    
    @staticmethod
    def get_session_stats(class_ids):
        """
        Get session statistics for classes in ONE query
        
        Returns: {
            class_id: {
                'total_sessions': count,
                'conducted_sessions': count,
                'cancelled_sessions': count
            }
        }
        """
        # Get planned sessions
        planned = PlannedSession.objects.filter(
            class_section_id__in=class_ids,
            is_active=True
        ).values('class_section_id').annotate(count=Count('id'))
        planned_by_class = {
            item['class_section_id']: item['count'] 
            for item in planned
        }
        
        # Get actual sessions by status
        actual = ActualSession.objects.filter(
            planned_session__class_section_id__in=class_ids
        ).values('planned_session__class_section_id', 'status').annotate(count=Count('id'))
        
        actual_by_class = {}
        for item in actual:
            class_id = item['planned_session__class_section_id']
            status = item['status']
            count = item['count']
            
            if class_id not in actual_by_class:
                actual_by_class[class_id] = {
                    'conducted': 0,
                    'cancelled': 0,
                    'holiday': 0
                }
            
            if status == 1:  # Conducted
                actual_by_class[class_id]['conducted'] = count
            elif status == 3:  # Cancelled
                actual_by_class[class_id]['cancelled'] = count
            elif status == 2:  # Holiday
                actual_by_class[class_id]['holiday'] = count
        
        result = {}
        for class_id in class_ids:
            result[class_id] = {
                'total_sessions': planned_by_class.get(class_id, 0),
                'conducted_sessions': actual_by_class.get(class_id, {}).get('conducted', 0),
                'cancelled_sessions': actual_by_class.get(class_id, {}).get('cancelled', 0),
                'holiday_sessions': actual_by_class.get(class_id, {}).get('holiday', 0)
            }
        
        return result


class CachedQueries:
    """Cached query patterns for frequently accessed data"""
    
    @staticmethod
    def get_schools_with_stats(user_id, cache_timeout=300):
        """
        Get all schools with stats, cached
        
        Args:
            user_id: User ID for cache key
            cache_timeout: Cache timeout in seconds (default 5 minutes)
        
        Returns: List of schools with stats
        """
        cache_key = f"schools_with_stats_{user_id}"
        result = cache.get(cache_key)
        
        if result is None:
            from .models import School, ClassSection, Enrollment, FacilitatorSchool
            from django.db.models import Count
            
            # Fetch base schools
            schools = list(School.objects.select_related('cluster').order_by('name'))
            school_ids = [s.id for s in schools]
            
            if school_ids:
                # Batch fetch statistics (much faster than nested subqueries or deep joins)
                class_counts = {
                    item['school_id']: item['count'] 
                    for item in ClassSection.objects.filter(school_id__in=school_ids, is_active=True)
                    .values('school_id').annotate(count=Count('id'))
                }
                
                student_counts = {
                    item['school_id']: item['count'] 
                    for item in Enrollment.objects.filter(school_id__in=school_ids, is_active=True)
                    .values('school_id').annotate(count=Count('student_id', distinct=True))
                }
                
                facilitator_counts = {
                    item['school_id']: item['count'] 
                    for item in FacilitatorSchool.objects.filter(school_id__in=school_ids, is_active=True)
                    .values('school_id').annotate(count=Count('facilitator_id', distinct=True))
                }
                
                # Map stats back to school objects
                for s in schools:
                    s.total_classes = class_counts.get(s.id, 0)
                    s.total_students = student_counts.get(s.id, 0)
                    s.active_facilitators = facilitator_counts.get(s.id, 0)
            
            result = schools
            cache.set(cache_key, result, cache_timeout)
        
        return result
    
    @staticmethod
    def invalidate_schools_cache(user_id):
        """Invalidate schools cache for a user"""
        cache_key = f"schools_with_stats_{user_id}"
        cache.delete(cache_key)
    
    @staticmethod
    def get_facilitators_with_stats(user_id, cache_timeout=300):
        """
        Get all facilitators with stats, cached
        
        Args:
            user_id: User ID for cache key
            cache_timeout: Cache timeout in seconds (default 5 minutes)
        
        Returns: List of facilitators with stats
        """
        cache_key = f"facilitators_with_stats_{user_id}"
        result = cache.get(cache_key)
        
        if result is None:
            from .models import User
            
            facilitators = User.objects.filter(
                role__name__iexact="FACILITATOR"
            ).select_related('role').prefetch_related(
                Prefetch(
                    'assigned_schools',
                    queryset=FacilitatorSchool.objects.select_related('school').filter(is_active=True)
                )
            ).annotate(
                school_count=Count('assigned_schools', filter=Q(assigned_schools__is_active=True), distinct=True)
            ).order_by("-created_at")
            
            result = list(facilitators)
            cache.set(cache_key, result, cache_timeout)
        
        return result
    
    @staticmethod
    def invalidate_facilitators_cache(user_id):
        """Invalidate facilitators cache for a user"""
        cache_key = f"facilitators_with_stats_{user_id}"
        cache.delete(cache_key)
