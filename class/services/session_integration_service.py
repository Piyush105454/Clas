"""
SessionIntegrationService for managing connections between PlannedSessions and CurriculumSessions.
Handles automatic linking, data integration, and alignment validation.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from django.utils import timezone
from django.db import transaction

from ..models import (
    PlannedSession, CurriculumSession, SessionContentMapping, 
    ClassSection, CurriculumUsageLog, CurriculumStatus
)

logger = logging.getLogger(__name__)


@dataclass
class IntegratedSessionData:
    """Combined data from PlannedSession and CurriculumSession."""
    planned_session: PlannedSession
    curriculum_session: Optional[CurriculumSession] = None
    content_source: str = 'static_fallback'
    last_sync: Optional[timezone.datetime] = None
    sync_status: str = 'synced'
    curriculum_content: str = ''
    has_admin_content: bool = False


@dataclass
class AlignmentReport:
    """Report on alignment between class progress and curriculum content."""
    class_section: ClassSection
    total_planned_sessions: int
    sessions_with_curriculum: int
    sessions_without_curriculum: int
    alignment_percentage: float
    misaligned_sessions: List[Dict[str, Any]]
    recommendations: List[str]


class SessionIntegrationService:
    """
    Service for managing the integration between PlannedSessions and CurriculumSessions.
    Provides automatic linking, data combination, and alignment validation.
    """
    
    def __init__(self):
        self.logger = logger
    
    def link_planned_to_curriculum(self, planned_session: PlannedSession) -> Optional[CurriculumSession]:
        """
        Create or update the link between a PlannedSession and its corresponding CurriculumSession.
        Returns the linked CurriculumSession if found, None otherwise.
        """
        try:
            # Determine language from class section
            language = self._get_class_language(planned_session.class_section)
            
            # Find matching CurriculumSession
            curriculum_session = self._find_curriculum_session(
                planned_session.day_number, 
                language
            )
            
            # Create or update the mapping
            mapping, created = SessionContentMapping.objects.get_or_create(
                planned_session=planned_session,
                defaults={
                    'curriculum_session': curriculum_session,
                    'content_source': 'admin_managed' if curriculum_session else 'static_fallback',
                    'sync_status': 'synced'
                }
            )
            
            if not created and mapping.curriculum_session != curriculum_session:
                # Update existing mapping if curriculum session changed
                mapping.curriculum_session = curriculum_session
                mapping.content_source = 'admin_managed' if curriculum_session else 'static_fallback'
                mapping.sync_status = 'synced'
                mapping.save()
                
                self.logger.info(
                    f"Updated mapping for {planned_session} to curriculum session {curriculum_session}"
                )
            elif created:
                self.logger.info(
                    f"Created new mapping for {planned_session} to curriculum session {curriculum_session}"
                )
            
            return curriculum_session
            
        except Exception as e:
            self.logger.error(f"Error linking planned session {planned_session.id} to curriculum: {str(e)}")
            return None
    
    def get_integrated_session_data(self, planned_session: PlannedSession) -> IntegratedSessionData:
        """
        Get combined data from PlannedSession and its linked CurriculumSession.
        ENHANCED: Handles grouped sessions and provides comprehensive error handling.
        """
        try:
            # Get or create the mapping
            mapping = self._get_or_create_mapping(planned_session)
            
            # Load curriculum content if available
            curriculum_content = ''
            has_admin_content = False
            
            if mapping.curriculum_session and mapping.content_source == 'admin_managed':
                curriculum_content = self._load_curriculum_content(mapping.curriculum_session)
                has_admin_content = True
                
                self.logger.info(
                    f"[OK] Loaded admin-managed curriculum content for day {planned_session.day_number}, "
                    f"class {planned_session.class_section.id}, "
                    f"grouped_session_id={planned_session.grouped_session_id or 'None'}"
                )
            else:
                # Log fallback
                self.logger.info(
                    f"[INFO] Using static fallback for day {planned_session.day_number}, "
                    f"class {planned_session.class_section.id}, "
                    f"grouped_session_id={planned_session.grouped_session_id or 'None'}, "
                    f"reason={'No curriculum session found' if not mapping.curriculum_session else 'Content source is not admin_managed'}"
                )
            
            return IntegratedSessionData(
                planned_session=planned_session,
                curriculum_session=mapping.curriculum_session,
                content_source=mapping.content_source,
                last_sync=mapping.last_sync,
                sync_status=mapping.sync_status,
                curriculum_content=curriculum_content,
                has_admin_content=has_admin_content
            )
            
        except Exception as e:
            self.logger.error(
                f"[ERROR] Error getting integrated data for planned_session {planned_session.id}, "
                f"day {planned_session.day_number}, class {planned_session.class_section.id}: {str(e)}", 
                exc_info=True
            )
            return IntegratedSessionData(
                planned_session=planned_session,
                content_source='error',
                sync_status='failed'
            )
    
    def update_session_relationships(self, curriculum_session: CurriculumSession) -> List[PlannedSession]:
        """
        Update all PlannedSession mappings when a CurriculumSession is modified.
        Returns list of affected PlannedSessions.
        """
        try:
            affected_sessions = []
            
            # Find all PlannedSessions that should link to this curriculum session
            planned_sessions = PlannedSession.objects.filter(
                day_number=curriculum_session.day_number,
                is_active=True
            )
            
            # Filter by language using our helper method
            matching_sessions = []
            for planned_session in planned_sessions:
                if self._get_class_language(planned_session.class_section) == curriculum_session.language:
                    matching_sessions.append(planned_session)
            
            # Filter by language using our helper method
            matching_sessions = []
            for planned_session in planned_sessions:
                if self._get_class_language(planned_session.class_section) == curriculum_session.language:
                    matching_sessions.append(planned_session)
            
            for planned_session in matching_sessions:
                # Update or create mapping
                mapping, created = SessionContentMapping.objects.get_or_create(
                    planned_session=planned_session,
                    defaults={
                        'curriculum_session': curriculum_session,
                        'content_source': 'admin_managed',
                        'sync_status': 'synced'
                    }
                )
                
                if not created:
                    # Update existing mapping
                    mapping.curriculum_session = curriculum_session
                    mapping.content_source = 'admin_managed'
                    mapping.sync_status = 'synced'
                    mapping.save()
                
                affected_sessions.append(planned_session)
            
            self.logger.info(
                f"Updated {len(affected_sessions)} session relationships for curriculum session {curriculum_session.id}"
            )
            
            return affected_sessions
            
        except Exception as e:
            self.logger.error(f"Error updating session relationships for curriculum {curriculum_session.id}: {str(e)}")
            return []
    
    def validate_session_alignment(self, class_section: ClassSection) -> AlignmentReport:
        """
        Check alignment between class progress and available curriculum content.
        """
        try:
            planned_sessions = PlannedSession.objects.filter(
                class_section=class_section,
                is_active=True
            ).order_by('day_number')
            
            total_sessions = planned_sessions.count()
            sessions_with_curriculum = 0
            sessions_without_curriculum = 0
            misaligned_sessions = []
            
            language = self._get_class_language(class_section)
            
            for planned_session in planned_sessions:
                # Check if curriculum content exists
                curriculum_session = self._find_curriculum_session(
                    planned_session.day_number, 
                    language
                )
                
                if curriculum_session and curriculum_session.is_active_for_facilitators:
                    sessions_with_curriculum += 1
                else:
                    sessions_without_curriculum += 1
                    misaligned_sessions.append({
                        'day_number': planned_session.day_number,
                        'title': planned_session.title,
                        'issue': 'No admin-managed curriculum content available',
                        'recommendation': 'Create curriculum session or use static content'
                    })
            
            alignment_percentage = (sessions_with_curriculum / total_sessions * 100) if total_sessions > 0 else 0
            
            # Generate recommendations
            recommendations = self._generate_alignment_recommendations(
                alignment_percentage, 
                sessions_without_curriculum,
                language
            )
            
            return AlignmentReport(
                class_section=class_section,
                total_planned_sessions=total_sessions,
                sessions_with_curriculum=sessions_with_curriculum,
                sessions_without_curriculum=sessions_without_curriculum,
                alignment_percentage=alignment_percentage,
                misaligned_sessions=misaligned_sessions,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error validating alignment for class {class_section.id}: {str(e)}")
            return AlignmentReport(
                class_section=class_section,
                total_planned_sessions=0,
                sessions_with_curriculum=0,
                sessions_without_curriculum=0,
                alignment_percentage=0,
                misaligned_sessions=[],
                recommendations=['Error occurred during alignment validation']
            )
    
    def bulk_link_sessions(self, class_section: ClassSection) -> Dict[str, int]:
        """
        Bulk link all PlannedSessions in a class to their corresponding CurriculumSessions.
        Returns statistics about the linking operation.
        """
        try:
            with transaction.atomic():
                planned_sessions = PlannedSession.objects.filter(
                    class_section=class_section,
                    is_active=True
                )
                
                stats = {
                    'total_sessions': planned_sessions.count(),
                    'linked_to_admin': 0,
                    'linked_to_static': 0,
                    'errors': 0
                }
                
                for planned_session in planned_sessions:
                    try:
                        curriculum_session = self.link_planned_to_curriculum(planned_session)
                        if curriculum_session:
                            stats['linked_to_admin'] += 1
                        else:
                            stats['linked_to_static'] += 1
                    except Exception as e:
                        stats['errors'] += 1
                        self.logger.error(f"Error linking session {planned_session.id}: {str(e)}")
                
                self.logger.info(f"Bulk linked sessions for class {class_section}: {stats}")
                return stats
                
        except Exception as e:
            self.logger.error(f"Error in bulk linking for class {class_section.id}: {str(e)}")
            return {'total_sessions': 0, 'linked_to_admin': 0, 'linked_to_static': 0, 'errors': 1}
    
    def log_curriculum_access(self, planned_session: PlannedSession, facilitator, request=None):
        """
        Log when a facilitator accesses curriculum content through a planned session.
        """
        try:
            mapping = self._get_or_create_mapping(planned_session)
            
            if mapping.curriculum_session:
                # Create usage log
                usage_log = CurriculumUsageLog.objects.create(
                    curriculum_session=mapping.curriculum_session,
                    facilitator=facilitator,
                    class_section=planned_session.class_section,
                    planned_session=planned_session,
                    content_source=mapping.content_source,
                    user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
                    ip_address=self._get_client_ip(request) if request else None
                )
                
                self.logger.info(f"Logged curriculum access: {usage_log}")
                return usage_log
                
        except Exception as e:
            self.logger.error(f"Error logging curriculum access for session {planned_session.id}: {str(e)}")
            return None
    
    def _get_class_language(self, class_section: ClassSection) -> str:
        """
        Determine the language for a class section.
        Since ClassSection doesn't have a language field, we'll default to English.
        In a real implementation, this might be determined by school location or other factors.
        """
        # Check if class section has a language field
        if hasattr(class_section, 'language') and class_section.language:
            return class_section.language.lower()
        
        # Check if school has language preference (if such field exists)
        if hasattr(class_section.school, 'language') and class_section.school.language:
            return class_section.school.language.lower()
        
        # Default to English if no language specified
        return 'english'
    
    def _find_curriculum_session(self, day_number: int, language: str) -> Optional[CurriculumSession]:
        """
        Find a CurriculumSession for the given day and language.
        ENHANCED: Better error handling and logging.
        """
        try:
            curriculum_session = CurriculumSession.objects.get(
                day_number=day_number,
                language=language,
                status=CurriculumStatus.PUBLISHED
            )
            
            self.logger.debug(
                f"[OK] Found curriculum session: day {day_number}, language {language}, "
                f"curriculum_id={curriculum_session.id}"
            )
            
            return curriculum_session
            
        except CurriculumSession.DoesNotExist:
            self.logger.debug(
                f"[INFO] Curriculum session not found: day {day_number}, language {language}"
            )
            return None
            
        except Exception as e:
            self.logger.error(
                f"[ERROR] Error finding curriculum session for day {day_number}, language {language}: {str(e)}", 
                exc_info=True
            )
            return None
    
    def _get_or_create_mapping(self, planned_session: PlannedSession) -> SessionContentMapping:
        """
        Get or create a SessionContentMapping for a PlannedSession.
        """
        mapping, created = SessionContentMapping.objects.get_or_create(
            planned_session=planned_session,
            defaults={
                'content_source': 'static_fallback',
                'sync_status': 'synced'
            }
        )
        
        if created:
            # Try to link to curriculum session
            self.link_planned_to_curriculum(planned_session)
            mapping.refresh_from_db()
        
        return mapping
    
    def _load_curriculum_content(self, curriculum_session: CurriculumSession) -> str:
        """
        Load formatted content from a CurriculumSession.
        """
        try:
            content_parts = []
            
            if curriculum_session.title:
                content_parts.append(f"<h1>{curriculum_session.title}</h1>")
            
            if curriculum_session.learning_objectives:
                content_parts.append(f"<h2>Learning Objectives</h2>")
                content_parts.append(f"<div class='learning-objectives'>{curriculum_session.learning_objectives}</div>")
            
            if curriculum_session.content:
                content_parts.append(f"<h2>Session Content</h2>")
                content_parts.append(f"<div class='session-content'>{curriculum_session.content}</div>")
            
            return "\n".join(content_parts) if content_parts else "<p>No content available.</p>"
            
        except Exception as e:
            self.logger.error(f"Error loading curriculum content for session {curriculum_session.id}: {str(e)}")
            return "<p>Error loading curriculum content.</p>"
    
    def _generate_alignment_recommendations(self, alignment_percentage: float, missing_count: int, language: str) -> List[str]:
        """
        Generate recommendations based on alignment analysis.
        """
        recommendations = []
        
        if alignment_percentage < 50:
            recommendations.append(
                f"Low alignment ({alignment_percentage:.1f}%). Consider creating curriculum sessions for missing days."
            )
        elif alignment_percentage < 80:
            recommendations.append(
                f"Moderate alignment ({alignment_percentage:.1f}%). Review and create curriculum sessions for key missing days."
            )
        else:
            recommendations.append(
                f"Good alignment ({alignment_percentage:.1f}%). Continue maintaining curriculum content."
            )
        
        if missing_count > 0:
            recommendations.append(
                f"Create {missing_count} curriculum sessions in {language} to achieve full alignment."
            )
        
        recommendations.append(
            "Regularly review and update curriculum content to maintain alignment with class progress."
        )
        
        return recommendations
    
    def _get_client_ip(self, request) -> Optional[str]:
        """
        Get client IP address from request.
        """
        if not request:
            return None
            
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip