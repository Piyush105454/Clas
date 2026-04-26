"""
Facilitator Session Continuation Service
Handles facilitator rotation and ensures curriculum continuity when facilitators change
"""

from django.db import models, transaction
from django.db.models import Q, Max, F
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any, List, Tuple
import logging

from ..models import (
    PlannedSession, ActualSession, ClassSection, User, FacilitatorSchool
)

logger = logging.getLogger(__name__)


class FacilitatorAssignmentHistory:
    """Tracks facilitator assignments and session continuity"""
    
    def __init__(self, class_section: ClassSection):
        self.class_section = class_section
        self.assignments = []
        self.load_history()
    
    def load_history(self):
        """Load all facilitator assignments for this class"""
        try:
            # Get all actual sessions with facilitators, ordered by day number
            sessions = ActualSession.objects.filter(
                planned_session__class_section=self.class_section,
                facilitator__isnull=False
            ).select_related('facilitator', 'planned_session').order_by('planned_session__day_number')
            
            current_facilitator = None
            start_day = None
            
            for session in sessions:
                facilitator = session.facilitator
                day_number = session.planned_session.day_number
                
                # If facilitator changed, save previous assignment
                if facilitator != current_facilitator and current_facilitator is not None:
                    self.assignments.append({
                        'facilitator': current_facilitator,
                        'start_day': start_day,
                        'end_day': day_number - 1,
                        'total_days': (day_number - 1) - start_day + 1
                    })
                    start_day = day_number
                
                if facilitator != current_facilitator:
                    current_facilitator = facilitator
                    if start_day is None:
                        start_day = day_number
            
            # Add final assignment
            if current_facilitator is not None and start_day is not None:
                # Get the last conducted day
                last_day = sessions.values_list('planned_session__day_number', flat=True).last()
                self.assignments.append({
                    'facilitator': current_facilitator,
                    'start_day': start_day,
                    'end_day': last_day,
                    'total_days': last_day - start_day + 1
                })
        
        except Exception as e:
            logger.error(f"Error loading facilitator assignment history for {self.class_section}: {e}")
    
    def get_last_completed_day(self) -> int:
        """Get the highest day number completed by any facilitator"""
        try:
            from ..models import ClassSessionProgress
            
            # Step 1: Check Progress Tracker for the highest completed day
            last_progress = ClassSessionProgress.objects.filter(
                class_section=self.class_section,
                status='completed'
            ).order_by('-day_number').first()
            
            if last_progress:
                logger.info(f"Continuation: Progress Tracker found last completed day {last_progress.day_number} for {self.class_section}")
                return last_progress.day_number

            # Step 2: Fallback to ActualSession history if no tracker record exists
            from ..models import SessionStatus
            last_session = ActualSession.objects.filter(
                planned_session__class_section=self.class_section,
                status__in=[SessionStatus.CONDUCTED, SessionStatus.CANCELLED]
            ).select_related('planned_session').order_by('-planned_session__day_number').first()
            
            if last_session:
                logger.info(f"Continuation: No Tracker record. Fallback to ActualSession history: Day {last_session.planned_session.day_number}")
                return last_session.planned_session.day_number
            return 0
        
        except Exception as e:
            logger.error(f"Error getting last completed day for {self.class_section}: {e}")
            return 0
    
    def get_continuation_day(self) -> int:
        """Get the day where the next facilitator should start (last_day + 1)"""
        last_day = self.get_last_completed_day()
        return last_day + 1
    
    def get_current_facilitator(self) -> Optional[User]:
        """Get the facilitator currently assigned to this class"""
        try:
            # Get the most recent actual session with a facilitator
            latest_session = ActualSession.objects.filter(
                planned_session__class_section=self.class_section,
                facilitator__isnull=False
            ).select_related('facilitator').order_by('-date').first()
            
            if latest_session:
                return latest_session.facilitator
            return None
        
        except Exception as e:
            logger.error(f"Error getting current facilitator for {self.class_section}: {e}")
            return None
    
    def get_previous_facilitator(self) -> Optional[User]:
        """Get the facilitator who worked before the current one"""
        if len(self.assignments) >= 2:
            return self.assignments[-2]['facilitator']
        return None
    
    def get_assignment_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all facilitator assignments"""
        return self.assignments


class FacilitatorSessionContinuation:
    """
    Core logic for facilitator rotation and session continuation
    """
    
    @staticmethod
    def get_next_session_for_facilitator(class_section: ClassSection, 
                                        facilitator: User) -> Optional[PlannedSession]:
        """
        Get the next session a facilitator should conduct
        If new to class: returns continuation day (not day 1)
        If already working: returns next pending session
        """
        try:
            history = FacilitatorAssignmentHistory(class_section)
            
            # Check if this facilitator has worked on this class before
            has_worked_before = ActualSession.objects.filter(
                planned_session__class_section=class_section,
                facilitator=facilitator
            ).exists()
            
            if has_worked_before:
                # Facilitator already worked on this class, get next pending session
                next_session = PlannedSession.objects.filter(
                    class_section=class_section,
                    is_active=True
                ).exclude(
                    actual_sessions__status__in=[SessionStatus.CONDUCTED, SessionStatus.CANCELLED]
                ).order_by('day_number').first()
                
                logger.info(f"Facilitator {facilitator} has worked before on {class_section}, next session: {next_session}")
                return next_session
            
            else:
                # New facilitator to this class, get continuation day
                continuation_day = history.get_continuation_day()
                
                # Get the planned session for continuation day
                next_session = PlannedSession.objects.filter(
                    class_section=class_section,
                    day_number=continuation_day,
                    is_active=True
                ).first()
                
                if next_session:
                    logger.info(f"New facilitator {facilitator} assigned to {class_section}, starting from day {continuation_day}")
                else:
                    logger.warning(f"No planned session found for continuation day {continuation_day} in {class_section}")
                
                return next_session
        
        except Exception as e:
            logger.error(f"Error getting next session for facilitator {facilitator} on {class_section}: {e}")
            return None
    
    @staticmethod
    def assign_facilitator_to_class(class_section: ClassSection, 
                                   facilitator: User,
                                   previous_facilitator: Optional[User] = None) -> Dict[str, Any]:
        """
        Assign a new facilitator to a class, ensuring continuation from previous facilitator's work
        """
        result = {
            'success': False,
            'message': '',
            'continuation_day': 0,
            'previous_facilitator': None,
            'last_completed_day': 0,
            'next_session': None
        }
        
        try:
            with transaction.atomic():
                history = FacilitatorAssignmentHistory(class_section)
                
                # Get last completed day
                last_completed_day = history.get_last_completed_day()
                continuation_day = history.get_continuation_day()
                
                result['last_completed_day'] = last_completed_day
                result['continuation_day'] = continuation_day
                
                # Get current facilitator before assignment
                current_facilitator = history.get_current_facilitator()
                result['previous_facilitator'] = current_facilitator.full_name if current_facilitator else None
                
                # Get next session for new facilitator
                next_session = FacilitatorSessionContinuation.get_next_session_for_facilitator(
                    class_section, facilitator
                )
                result['next_session'] = {
                    'day_number': next_session.day_number,
                    'title': next_session.title
                } if next_session else None
                
                # Log the assignment
                logger.info(
                    f"Facilitator assignment: {facilitator.full_name} assigned to {class_section}, "
                    f"continuing from day {continuation_day} (previous: {current_facilitator.full_name if current_facilitator else 'None'})"
                )
                
                result['success'] = True
                result['message'] = (
                    f"Facilitator {facilitator.full_name} assigned to {class_section}. "
                    f"Previous facilitator completed up to day {last_completed_day}. "
                    f"New facilitator will continue from day {continuation_day}."
                )
        
        except Exception as e:
            logger.error(f"Error assigning facilitator {facilitator} to {class_section}: {e}")
            result['message'] = f"Error: {str(e)}"
        
        return result
    
    @staticmethod
    def validate_facilitator_transition(class_section: ClassSection,
                                       old_facilitator: User,
                                       new_facilitator: User) -> Dict[str, Any]:
        """
        Validate that a facilitator transition maintains curriculum continuity
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'transition_details': {}
        }
        
        try:
            history = FacilitatorAssignmentHistory(class_section)
            
            # Check if old facilitator actually worked on this class
            old_fac_sessions = ActualSession.objects.filter(
                planned_session__class_section=class_section,
                facilitator=old_facilitator
            ).count()
            
            if old_fac_sessions == 0:
                result['warnings'].append(f"{old_facilitator.full_name} has no sessions on {class_section}")
            
            # Check if new facilitator is already assigned
            new_fac_sessions = ActualSession.objects.filter(
                planned_session__class_section=class_section,
                facilitator=new_facilitator
            ).count()
            
            if new_fac_sessions > 0:
                result['warnings'].append(f"{new_facilitator.full_name} already has sessions on {class_section}")
            
            # Get continuation details
            last_day = history.get_last_completed_day()
            continuation_day = history.get_continuation_day()
            
            result['transition_details'] = {
                'old_facilitator': old_facilitator.full_name,
                'new_facilitator': new_facilitator.full_name,
                'last_completed_day': last_day,
                'continuation_day': continuation_day,
                'class_section': str(class_section)
            }
            
            logger.info(f"Facilitator transition validated: {old_facilitator.full_name} → {new_facilitator.full_name} on {class_section}")
        
        except Exception as e:
            logger.error(f"Error validating facilitator transition: {e}")
            result['is_valid'] = False
            result['errors'].append(str(e))
        
        return result
    
    @staticmethod
    def get_facilitator_workload(facilitator: User) -> Dict[str, Any]:
        """
        Get summary of facilitator's work across all classes
        """
        result = {
            'facilitator': facilitator.full_name,
            'total_classes': 0,
            'total_days_conducted': 0,
            'classes': []
        }
        
        try:
            # Get all classes this facilitator has worked on
            class_sections = ClassSection.objects.filter(
                planned_sessions__actual_sessions__facilitator=facilitator
            ).distinct()
            
            result['total_classes'] = class_sections.count()
            
            for class_section in class_sections:
                # Get days conducted by this facilitator
                days_conducted = ActualSession.objects.filter(
                    planned_session__class_section=class_section,
                    facilitator=facilitator,
                    status=SessionStatus.CONDUCTED
                ).count()
                
                # Get last day worked
                last_session = ActualSession.objects.filter(
                    planned_session__class_section=class_section,
                    facilitator=facilitator
                ).select_related('planned_session').order_by('-planned_session__day_number').first()
                
                last_day = last_session.planned_session.day_number if last_session else 0
                
                result['classes'].append({
                    'class_section': str(class_section),
                    'days_conducted': days_conducted,
                    'last_day_worked': last_day
                })
                
                result['total_days_conducted'] += days_conducted
        
        except Exception as e:
            logger.error(f"Error getting facilitator workload for {facilitator}: {e}")
        
        return result
    
    @staticmethod
    def get_class_facilitator_timeline(class_section: ClassSection) -> List[Dict[str, Any]]:
        """
        Get complete timeline of facilitator assignments for a class
        """
        timeline = []
        
        try:
            history = FacilitatorAssignmentHistory(class_section)
            
            for assignment in history.get_assignment_summary():
                timeline.append({
                    'facilitator': assignment['facilitator'].full_name,
                    'start_day': assignment['start_day'],
                    'end_day': assignment['end_day'],
                    'total_days': assignment['total_days'],
                    'percentage': round((assignment['total_days'] / 150) * 100, 2)
                })
            
            logger.info(f"Generated facilitator timeline for {class_section}: {len(timeline)} facilitators")
        
        except Exception as e:
            logger.error(f"Error generating facilitator timeline for {class_section}: {e}")
        
        return timeline
