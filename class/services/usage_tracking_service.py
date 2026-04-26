"""
UsageTrackingService for curriculum access analytics and reporting.
Tracks facilitator access patterns and provides impact analysis.
"""

import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.contrib.auth.models import User
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..models import CurriculumUsageLog, CurriculumSession, ClassSection, PlannedSession, CurriculumStatus

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Metrics for curriculum usage."""
    total_accesses: int
    unique_facilitators: int
    unique_classes: int
    average_session_duration: float
    most_accessed_day: int
    most_accessed_language: str
    peak_usage_hour: int


@dataclass
class ImpactAnalysis:
    """Analysis of curriculum changes impact."""
    affected_facilitators: List[Dict[str, Any]]
    affected_classes: List[Dict[str, Any]]
    total_sessions_impacted: int
    notification_recipients: List[User]


@dataclass
class ContentEffectiveness:
    """Effectiveness metrics for curriculum content."""
    day_number: int
    language: str
    access_count: int
    average_engagement_time: float
    facilitator_feedback_score: Optional[float]
    completion_rate: float


class UsageTrackingService:
    """
    Service for tracking curriculum usage and generating analytics.
    Provides insights into content effectiveness and facilitator engagement.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_curriculum_access(self, facilitator: User, curriculum_session: CurriculumSession, 
                            class_section: ClassSection, planned_session=None, 
                            content_source: str = 'admin_managed') -> CurriculumUsageLog:
        """
        Log curriculum access by a facilitator.
        
        Args:
            facilitator: User who accessed the content
            curriculum_session: CurriculumSession that was accessed
            class_section: ClassSection context for the access
            planned_session: Associated PlannedSession if applicable
            content_source: Source of the curriculum content
        
        Returns:
            CurriculumUsageLog: The created log entry
        """
        try:
            usage_log = CurriculumUsageLog.objects.create(
                facilitator=facilitator,
                curriculum_session=curriculum_session,
                class_section=class_section,
                planned_session=planned_session,
                content_source=content_source
            )
            
            self.logger.info(f"Logged curriculum access: {facilitator.email} accessed Day {curriculum_session.day_number} {curriculum_session.language}")
            return usage_log
            
        except Exception as e:
            self.logger.error(f"Error logging curriculum access: {str(e)}")
            raise
    
    def generate_usage_analytics(self, start_date: Optional[datetime] = None, 
                               end_date: Optional[datetime] = None) -> UsageMetrics:
        """
        Generate comprehensive usage analytics for curriculum content.
        
        Args:
            start_date: Start date for analytics period
            end_date: End date for analytics period
        
        Returns:
            UsageMetrics: Comprehensive usage metrics
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = timezone.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Base queryset for the period
            usage_logs = CurriculumUsageLog.objects.filter(
                access_timestamp__range=[start_date, end_date]
            )
            
            # Calculate metrics
            total_accesses = usage_logs.count()
            unique_facilitators = usage_logs.values('facilitator').distinct().count()
            unique_classes = usage_logs.values('class_section').distinct().count()
            
            # Average session duration (if we track end times)
            avg_duration = usage_logs.filter(
                session_duration__isnull=False
            ).aggregate(avg_duration=Avg('session_duration'))['avg_duration'] or 0.0
            
            # Most accessed day and language
            day_stats = usage_logs.values('curriculum_session__day_number').annotate(
                count=Count('id')
            ).order_by('-count').first()
            most_accessed_day = day_stats['curriculum_session__day_number'] if day_stats else 1
            
            language_stats = usage_logs.values('curriculum_session__language').annotate(
                count=Count('id')
            ).order_by('-count').first()
            most_accessed_language = language_stats['curriculum_session__language'] if language_stats else 'english'
            
            # Peak usage hour
            hour_stats = usage_logs.extra(
                select={'hour': 'EXTRACT(hour FROM access_timestamp)'}
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('-count').first()
            peak_usage_hour = int(hour_stats['hour']) if hour_stats else 10
            
            return UsageMetrics(
                total_accesses=total_accesses,
                unique_facilitators=unique_facilitators,
                unique_classes=unique_classes,
                average_session_duration=avg_duration,
                most_accessed_day=most_accessed_day,
                most_accessed_language=most_accessed_language,
                peak_usage_hour=peak_usage_hour
            )
            
        except Exception as e:
            self.logger.error(f"Error generating usage analytics: {str(e)}")
            raise
    
    def analyze_curriculum_impact(self, curriculum_session: CurriculumSession) -> ImpactAnalysis:
        """
        Analyze the impact of curriculum changes on facilitators and classes.
        
        Args:
            curriculum_session: CurriculumSession to analyze impact for
        
        Returns:
            ImpactAnalysis: Analysis of affected facilitators and classes
        """
        try:
            # Find all usage logs for this curriculum session
            usage_logs = CurriculumUsageLog.objects.filter(
                curriculum_session=curriculum_session
            ).select_related('facilitator', 'class_section', 'class_section__school')
            
            # Get affected facilitators with their usage patterns
            facilitator_data = {}
            for log in usage_logs:
                facilitator_id = log.facilitator.id
                if facilitator_id not in facilitator_data:
                    facilitator_data[facilitator_id] = {
                        'user': log.facilitator,
                        'email': log.facilitator.email,
                        'name': log.facilitator.full_name or log.facilitator.email,
                        'access_count': 0,
                        'last_access': None,
                        'classes_taught': set()
                    }
                
                facilitator_data[facilitator_id]['access_count'] += 1
                facilitator_data[facilitator_id]['classes_taught'].add(log.class_section.id)
                
                if (not facilitator_data[facilitator_id]['last_access'] or 
                    log.access_timestamp > facilitator_data[facilitator_id]['last_access']):
                    facilitator_data[facilitator_id]['last_access'] = log.access_timestamp
            
            # Convert sets to counts for serialization
            affected_facilitators = []
            for data in facilitator_data.values():
                data['classes_count'] = len(data['classes_taught'])
                data['classes_taught'] = list(data['classes_taught'])
                affected_facilitators.append(data)
            
            # Get affected classes with their usage patterns
            class_data = {}
            for log in usage_logs:
                class_id = log.class_section.id
                if class_id not in class_data:
                    class_data[class_id] = {
                        'class_section': log.class_section,
                        'school_name': log.class_section.school.name,
                        'class_level': log.class_section.class_level,
                        'section': log.class_section.section,
                        'access_count': 0,
                        'facilitators': set(),
                        'last_access': None
                    }
                
                class_data[class_id]['access_count'] += 1
                class_data[class_id]['facilitators'].add(log.facilitator.id)
                
                if (not class_data[class_id]['last_access'] or 
                    log.access_timestamp > class_data[class_id]['last_access']):
                    class_data[class_id]['last_access'] = log.access_timestamp
            
            # Convert sets to counts for serialization
            affected_classes = []
            for data in class_data.values():
                data['facilitators_count'] = len(data['facilitators'])
                data['facilitators'] = list(data['facilitators'])
                affected_classes.append(data)
            
            # Count total sessions that might be impacted
            total_sessions_impacted = PlannedSession.objects.filter(
                day_number=curriculum_session.day_number,
                class_section__in=[data['class_section'] for data in class_data.values()]
            ).count()
            
            # Get notification recipients (all affected facilitators)
            notification_recipients = [data['user'] for data in facilitator_data.values()]
            
            return ImpactAnalysis(
                affected_facilitators=affected_facilitators,
                affected_classes=affected_classes,
                total_sessions_impacted=total_sessions_impacted,
                notification_recipients=notification_recipients
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing curriculum impact: {str(e)}")
            raise
    
    def track_content_effectiveness(self, day_number: int, language: str) -> ContentEffectiveness:
        """
        Track effectiveness metrics for specific curriculum content.
        
        Args:
            day_number: Day number to analyze
            language: Language to analyze
        
        Returns:
            ContentEffectiveness: Effectiveness metrics for the content
        """
        try:
            # Get curriculum session
            try:
                curriculum_session = CurriculumSession.objects.get(
                    day_number=day_number,
                    language=language,
                    status=CurriculumStatus.PUBLISHED
                )
            except CurriculumSession.DoesNotExist:
                # Return default metrics if no admin-managed content exists
                return ContentEffectiveness(
                    day_number=day_number,
                    language=language,
                    access_count=0,
                    average_engagement_time=0.0,
                    facilitator_feedback_score=None,
                    completion_rate=0.0
                )
            
            # Get usage logs for this content
            usage_logs = CurriculumUsageLog.objects.filter(
                curriculum_session=curriculum_session
            )
            
            access_count = usage_logs.count()
            
            # Calculate average engagement time
            engagement_logs = usage_logs.filter(session_duration__isnull=False)
            avg_engagement = engagement_logs.aggregate(
                avg_time=Avg('session_duration')
            )['avg_time'] or 0.0
            
            # Calculate completion rate (sessions that were fully conducted)
            total_planned = PlannedSession.objects.filter(day_number=day_number).count()
            completed_sessions = PlannedSession.objects.filter(
                day_number=day_number
            ).count()  # All planned sessions are considered for completion rate
            completion_rate = (completed_sessions / total_planned * 100) if total_planned > 0 else 0.0
            
            # Get facilitator feedback score (if we have feedback data)
            # This would need to be implemented based on your feedback system
            facilitator_feedback_score = None
            
            return ContentEffectiveness(
                day_number=day_number,
                language=language,
                access_count=access_count,
                average_engagement_time=avg_engagement,
                facilitator_feedback_score=facilitator_feedback_score,
                completion_rate=completion_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error tracking content effectiveness for Day {day_number} {language}: {str(e)}")
            raise
    
    def get_facilitator_usage_summary(self, facilitator: User, 
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get usage summary for a specific facilitator.
        
        Args:
            facilitator: User to get summary for
            start_date: Start date for summary period
            end_date: End date for summary period
        
        Returns:
            Dict containing facilitator usage summary
        """
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = timezone.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            usage_logs = CurriculumUsageLog.objects.filter(
                facilitator=facilitator,
                access_timestamp__range=[start_date, end_date]
            ).select_related('curriculum_session', 'class_section')
            
            total_accesses = usage_logs.count()
            unique_days_accessed = usage_logs.values('curriculum_session__day_number').distinct().count()
            unique_classes = usage_logs.values('class_section').distinct().count()
            
            # Most accessed content
            day_stats = usage_logs.values('curriculum_session__day_number').annotate(
                count=Count('id')
            ).order_by('-count')
            
            language_stats = usage_logs.values('curriculum_session__language').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Recent activity
            recent_accesses = usage_logs.order_by('-access_timestamp')[:10]
            
            return {
                'facilitator': {
                    'id': facilitator.id,
                    'email': facilitator.email,
                    'name': facilitator.full_name or facilitator.email
                },
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_accesses': total_accesses,
                    'unique_days_accessed': unique_days_accessed,
                    'unique_classes': unique_classes,
                    'most_accessed_days': list(day_stats[:5]),
                    'language_preferences': list(language_stats),
                },
                'recent_activity': [
                    {
                        'day': log.curriculum_session.day_number,
                        'language': log.curriculum_session.language,
                        'class': f"{log.class_section.class_level}-{log.class_section.section}",
                        'school': log.class_section.school.name,
                        'timestamp': log.access_timestamp,
                        'access_type': log.access_type
                    }
                    for log in recent_accesses
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting facilitator usage summary: {str(e)}")
            raise
    
    def get_content_popularity_report(self) -> Dict[str, Any]:
        """
        Generate a report on content popularity across all facilitators.
        
        Returns:
            Dict containing content popularity metrics
        """
        try:
            # Get all usage logs from the last 90 days
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            usage_logs = CurriculumUsageLog.objects.filter(
                access_timestamp__range=[start_date, end_date]
            )
            
            # Day popularity
            day_popularity = usage_logs.values('curriculum_session__day_number').annotate(
                access_count=Count('id'),
                unique_facilitators=Count('facilitator', distinct=True),
                unique_classes=Count('class_section', distinct=True)
            ).order_by('-access_count')
            
            # Language popularity
            language_popularity = usage_logs.values('curriculum_session__language').annotate(
                access_count=Count('id'),
                unique_facilitators=Count('facilitator', distinct=True)
            ).order_by('-access_count')
            
            # School-wise usage
            school_usage = usage_logs.values('class_section__school__name').annotate(
                access_count=Count('id'),
                unique_facilitators=Count('facilitator', distinct=True),
                unique_days=Count('curriculum_session__day_number', distinct=True)
            ).order_by('-access_count')
            
            # Time-based patterns
            hourly_usage = usage_logs.extra(
                select={'hour': 'EXTRACT(hour FROM access_timestamp)'}
            ).values('hour').annotate(
                access_count=Count('id')
            ).order_by('hour')
            
            return {
                'report_period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_accesses': usage_logs.count()
                },
                'day_popularity': list(day_popularity[:20]),  # Top 20 days
                'language_popularity': list(language_popularity),
                'school_usage': list(school_usage[:10]),  # Top 10 schools
                'hourly_patterns': list(hourly_usage),
                'summary_stats': {
                    'most_popular_day': day_popularity.first()['curriculum_session__day_number'] if day_popularity else None,
                    'most_popular_language': language_popularity.first()['curriculum_session__language'] if language_popularity else None,
                    'peak_usage_hour': max(hourly_usage, key=lambda x: x['access_count'])['hour'] if hourly_usage else None
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating content popularity report: {str(e)}")
            raise