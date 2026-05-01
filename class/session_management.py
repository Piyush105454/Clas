"""
Session Sequence Management Logic
Implements the core business logic for 1-150 day session sequence management
"""

from django.db import models, transaction
from django.db.models import Q, Count, Max, Min
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, List, Dict, Any, Tuple, cast
from datetime import date
import logging

from django.core.cache import cache
from .models import (
    PlannedSession, ActualSession, ClassSection, User,
    SessionBulkTemplate, CANCELLATION_REASONS, SessionStatus,
    ClassSessionProgress, GroupedSession, CalendarDate, DateType
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result object for validation operations"""
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors: List[str] = errors or []
        self.warnings: List[str] = warnings or []
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)


class ProgressMetrics:
    """Progress metrics for a class section"""
    def __init__(self, class_section: ClassSection):
        self.class_section = class_section
        self.total_sessions = 150
        self.conducted_sessions = 0
        self.cancelled_sessions = 0
        self.holiday_sessions = 0
        self.pending_sessions = 0
        self.completion_percentage = 0.0
        self.next_day_number = 1
        self.current_session = None



def get_grouped_classes_for_session(planned_session: PlannedSession, target_date: Optional[date] = None) -> List[ClassSection]:
    """
    Helper function to get all classes in a grouped session
    Consolidates logic for checking both grouped_session_id and CalendarDate
    Uses caching to avoid redundant queries
    
    Returns list of ClassSection objects that are part of the same group
    """
    if target_date is None:
        target_date = timezone.localdate()
    
    grouped_classes = []
    
    # Priority 1: Check CalendarDate for specific date grouping
    calendar_entry = CalendarDate.objects.filter(
        date=target_date,
        class_sections=planned_session.class_section,
        date_type=DateType.SESSION
    ).prefetch_related('class_sections').first()
    
    if calendar_entry and calendar_entry.class_sections.count() > 1:
        grouped_classes = list(calendar_entry.class_sections.all())
        return grouped_classes

    # Priority 2: Persistent Groups (REMOVED)
    # To maintain the "Daily Clean Start" rule, we no longer automatically group 
    # based on permanent ID here. This ensures that if the dashboard shows 
    # 4A and 5A as single cards, the session page also treats them as single.
    # Grouping only happens if Priority 1 (Manual Today Grouping) is found.
    # -------------------------------------------------------------------------
    # if planned_session.grouped_session_id:
    #     today = timezone.localtime(timezone.now()).date()
    #     if target_date == today:
    #         grouped_sessions = PlannedSession.objects.filter(
    #             grouped_session_id=planned_session.grouped_session_id,
    #             day_number=planned_session.day_number
    #         ).select_related('class_section')
    #         
    #         grouped_classes = [gs.class_section for gs in grouped_sessions]
    #         return grouped_classes
            
    # Default: Single class
    grouped_classes = [planned_session.class_section]
    return grouped_classes


class SessionSequenceCalculator:
    """
    Determines the correct "today's session" for any class section
    Implements the core sequence calculation logic
    """
    # [PER-REQUEST CACHE]
    # Use threading.local() to ensure the cache is request-specific and thread-safe
    import threading
    _local = threading.local()

    @staticmethod
    def _get_cache():
        if not hasattr(SessionSequenceCalculator._local, 'cache'):
            SessionSequenceCalculator._local.cache = {}
        return SessionSequenceCalculator._local.cache

    @staticmethod
    def _get_group_leader(group_members: List[ClassSection]) -> ClassSection:
        """
        Picks the class in the group that has the MINIMUM progress 
        (the earliest curriculum gap). This ensures the group stays 
        together and no class misses any curriculum content.
        """
        # [CACHE] Check if we already calculated the leader for this exact group
        cache = SessionSequenceCalculator._get_cache()
        group_key = f"leader:{'-'.join(sorted([str(m.id) for m in group_members]))}"
        
        if group_key in cache:
            return cache[group_key]
            
        if not group_members:
            return None
        if len(group_members) == 1:
            return group_members[0]
            
        leader = group_members[0]
        min_gap_day = 151
        
        # We find the FIRST GAP for each class and pick the class with the smallest one
        for cls in group_members:
            # Get all curriculum days (1-150) that have been successfully CONDUCTED
            # We exclude CANCELLED sessions so they can be re-tried in a group
            completed_days = set(ActualSession.objects.filter(
                planned_session__class_section=cls,
                status=SessionStatus.CONDUCTED
            ).values_list('planned_session__day_number', flat=True))
            
            target_day = 1
            for day_num in range(1, 151):
                if day_num not in completed_days:
                    target_day = day_num
                    break
            
            if target_day < min_gap_day:
                min_gap_day = target_day
                leader = cls
            elif target_day == min_gap_day:
                # Tie-breaker: Use ID to be deterministic
                if str(cls.id) < str(leader.id):
                    leader = cls
                    
        SessionSequenceCalculator._get_cache()[group_key] = leader
        return leader

    @staticmethod
    def get_next_pending_session(class_section: ClassSection, facilitator: User = None, calendar_entry: Any = None) -> Optional[PlannedSession]:
        """
        Returns the next session that needs to be conducted.
        ENHANCED: Respects manual grouping for TODAY vs permanent grouping.
        """
        from django.utils import timezone
        from .services.facilitator_session_continuation import FacilitatorSessionContinuation
        
        today = timezone.localdate()
        
        try:
            # Step 1: Facilitator continuation logic (highest priority)
            if facilitator:
                continuation = FacilitatorSessionContinuation.get_next_session_for_facilitator(
                    class_section, facilitator
                )
                if continuation:
                    return continuation
            
            # Step 2: Detect Grouping for TODAY
            # Priority: Manual Grouping from CalendarDate
            lookup_class = class_section
            group_members = [class_section]
            
            if calendar_entry:
                if hasattr(calendar_entry, 'class_sections'):
                    current_group = list(calendar_entry.class_sections.all())
                    if class_section in current_group:
                        group_members = current_group
            else:
                # Fallback: Check for manual group for today in the DB
                from .models import CalendarDate
                todays_entry = CalendarDate.objects.filter(
                    date=today
                ).filter(
                    models.Q(class_sections=class_section) | models.Q(class_section=class_section)
                ).prefetch_related('class_sections').first()
                
                if todays_entry:
                    if todays_entry.class_section:
                        group_members = [todays_entry.class_section]
                    elif todays_entry.class_sections.exists():
                        group_members = list(todays_entry.class_sections.all())
            
            if len(group_members) > 1:
                # We are grouped TODAY. Use the class with MINIMUM progress as leader (no gap miss).
                lookup_class = SessionSequenceCalculator._get_group_leader(group_members)
                logger.info(f"Grouped progress for today: Using leader {lookup_class.display_name} (minimum progress sync) for {class_section.display_name}")
            else:
                # We are NOT grouped today. Use individual class progress history.
                # Note: We purposely ignore permanent GroupedSession records here to allow 
                # classes to diverge if they aren't taught together today.
                logger.info(f"Individual progress for today: Using individual history for {class_section.display_name}")
            
            # Step 2: ENSURE TODAY'S SESSION IS VALID
            # Check if there is an ActualSession for TODAY
            todays_actual_session = ActualSession.objects.filter(
                planned_session__class_section=lookup_class,
                date=today
            ).select_related('planned_session').order_by('planned_session__day_number').first()
            
            # [HEARTBEAT] GAP-AWARE SEQUENCING
            # We no longer look at the MAX Day Number. Instead, we find the FIRST MISSING Day.
            # 1. Get all curriculum days (1-150) that have been successfully CONDUCTED
            # We exclude CANCELLED to ensure they can be re-tried until CONDUCTED.
            completed_days = set(ActualSession.objects.filter(
                planned_session__class_section=lookup_class,
                planned_session__day_number__lte=150,
                status=SessionStatus.CONDUCTED
            ).exclude(date=today).values_list('planned_session__day_number', flat=True))
            
            # [SIMPLE LOGIC] 
            # Total conducted sessions (curriculum) + 1 = Next Day.
            # This is "Easy Logic": 2 conducted -> Suggest Day 3.
            standard_conducted_count = ActualSession.objects.filter(
                planned_session__class_section=lookup_class,
                status=SessionStatus.CONDUCTED,
                planned_session__day_number__lte=150
            ).count()
            
            target_day = standard_conducted_count + 1
            highest_completed_day = max(list(completed_days) + [0])
            logger.info(f"Gap-Aware Sync: {lookup_class.display_name} has highest {highest_completed_day}. Suggesting first gap: Day {target_day}")
            
            if todays_actual_session:
                # [FIX] CURRICULUM-FIRST: Ignore "Magic" days (997, 998, 999) on the main dashboard 
                # unless they are explicitly standard curriculum. This ensures that if 6 are done, 
                # Day 7 is shown even if Office Work was accidentally tagged.
                current_day_num = todays_actual_session.planned_session.day_number
                
                if current_day_num < 900:
                    # If today's session is CONDUCTED or CANCELLED, we must return it
                    if todays_actual_session.status in [SessionStatus.CONDUCTED, SessionStatus.CANCELLED]:
                        return todays_actual_session.planned_session
                    
                    # [STRICT GAP PROTECTION]
                    # If today's session is PENDING but it doesn't match our first gap (target_day),
                    # we must DELETE this incorrect record to allow the correct day to start.
                    if current_day_num != target_day:
                        logger.warning(f"CRITICAL: Today's session (Day {current_day_num}) does not match first gap (Day {target_day}) for {lookup_class}. Attempting to DELETING jumped record to restore sequence.")
                        try:
                            # Use transaction.atomic to ensure we don't leave half-deleted states 
                            # and catch specific DB errors if related tables are missing
                            with transaction.atomic():
                                todays_actual_session.delete()
                                # After deletion, null out local var so we proceed to Step 3
                                todays_actual_session = None
                        except Exception as delete_error:
                            logger.error(f"Failed to delete jumped record (possible missing DB table): {delete_error}")
                            # If we can't delete it, we MUST return it anyway or move to a fallback 
                            # to prevent a total UI crash. Better to show 'incorrect' session than no session.
                            return todays_actual_session.planned_session
                    else:
                        # Today's session is valid and pending, return it
                        return todays_actual_session.planned_session
                else:
                    # It's a magic day (997-999). We ignore it to let the curriculum day (target_day) 
                    # take precedence on this page.
                    logger.info(f"Ignoring existing today session for Magic Day {current_day_num} to prioritize curriculum.")
                    todays_actual_session = None
            
            # Step 3: USE ACTUAL SESSION HISTORY + PROGRESS TRACKER as source of truth
            # target_day from Gap-Aware Sync is our foundation.
            
            # Step 4: Reconcile with PROGRESS TRACKER
            latest_progress = ClassSessionProgress.objects.filter(
                class_section=lookup_class
            ).order_by('-date', '-id').first()
            
            if latest_progress:
                progress_day = latest_progress.day_number
                
                # [GAP SYNC] 
                # If progress tracker is out of sync with our first available gap,
                # we force the tracker to the gap to ensure UI consistency.
                if progress_day != target_day:
                    logger.warning(f"Gap Sync for {lookup_class}: Tracker says Day {progress_day} but physical gap is Day {target_day}. Correcting.")
                    # Self-heal the progress tracker
                    latest_progress.day_number = target_day
                    latest_progress.save(update_fields=['day_number'])
                    
                    # [CRITICAL] Invalidate progress cache so the UI updates Day badge immediately
                    SessionStatusManager._invalidate_progress_cache(lookup_class)
                    logger.info(f"Self-healed progress tracker and invalidated cache for {lookup_class}")
                
            logger.info(f"Final Target Calculation: Suggesting Day {target_day} for {lookup_class}")

            # Safety check: range 1-150
            if target_day > 150:
                 # Only stop if ALL 150 are done
                 if highest_completed_day >= 150:
                    return None
                 target_day = 150
            
            if target_day < 1:
                target_day = 1

            # Find the target planned session
            next_session = PlannedSession.objects.filter(
                class_section=lookup_class,
                day_number__gte=target_day,
                is_active=True
            ).order_by('day_number').first()

            # [AUTO-REPAIR] If we found a session but it's AFTER the target day,
            # or we found NOTHING but history says we aren't done, it's a curriculum gap.
            if (next_session and next_session.day_number > target_day) or (not next_session and highest_completed_day < 149):
                logger.warning(f"Curriculum gap detected for {lookup_class}: Expected Day {target_day}. Triggering aggressive repair.")
                SessionBulkManager.repair_sequence_gaps(lookup_class) # Fill the holes in 1-150
                # Re-fetch after repair
                next_session = PlannedSession.objects.filter(
                    class_section=lookup_class,
                    day_number__gte=target_day,
                    is_active=True
                ).order_by('day_number').first()
                logger.info(f"Curriculum repaired for {lookup_class}. New session identified: {next_session}")
            
            # If no session found, check if we have any sessions at all
            if not next_session:
                # [FIX] For grouped classes, we must check sessions for lookup_class
                total_sessions = PlannedSession.objects.filter(
                    class_section=lookup_class,
                    is_active=True
                ).count()
                
                if total_sessions == 0:
                    logger.warning(f"No planned sessions found for {lookup_class}")
                    return None
                
                # Check if all sessions are truly conducted
                completed_count = ActualSession.objects.filter(
                    planned_session__class_section=lookup_class,
                    status=SessionStatus.CONDUCTED
                ).count()
                
                if completed_count >= total_sessions:
                    logger.info(f"All sessions completed for {lookup_class}")
                    return None
                
                # There might be sessions without actual sessions, get the first one
                next_session = PlannedSession.objects.filter(
                    class_section=lookup_class,
                    is_active=True
                ).order_by('day_number').first()
            
            logger.info(f"Next pending session for {class_section}: Day {next_session.day_number if next_session else 'None'}")
            return next_session
            
        except Exception as e:
            logger.error(f"Error getting next pending session for {class_section}: {e}")
            return None
    
    @staticmethod
    def validate_sequence_integrity(class_section: ClassSection) -> ValidationResult:
        """
        Checks for gaps or issues in the session sequence
        Validates that all days 1-150 are present and properly ordered
        """
        result = ValidationResult(True)
        
        try:
            # Get all planned sessions for this class
            planned_sessions = PlannedSession.objects.filter(
                class_section=class_section,
                is_active=True
            ).order_by('day_number')
            
            if not planned_sessions.exists():
                result.add_error("No planned sessions found for this class")
                return result
            
            # Check for complete 1-150 sequence
            day_numbers = list(planned_sessions.values_list('day_number', flat=True))
            expected_days = set(range(1, 151))  # 1-150
            actual_days = set(day_numbers)
            
            # Check for missing days
            missing_days = expected_days - actual_days
            if missing_days:
                missing_list = sorted(list(missing_days))
                result.add_error(f"Missing session days: {missing_list}")
            
            # Check for duplicate days
            if len(day_numbers) != len(set(day_numbers)):
                duplicates = [day for day in set(day_numbers) if day_numbers.count(day) > 1]
                result.add_error(f"Duplicate session days: {duplicates}")
            
            # Check for days outside 1-150 range
            invalid_days = [day for day in day_numbers if day is not None and (day < 1 or day > 150)]
            if invalid_days:
                result.add_error(f"Invalid day numbers (must be 1-150): {invalid_days}")
            
            # Check sequence position consistency
            for session in planned_sessions:
                if session.sequence_position and session.sequence_position != session.day_number:
                    result.add_warning(f"Day {session.day_number} has inconsistent sequence_position: {session.sequence_position}")
            
            logger.info(f"Sequence integrity check for {class_section}: {result.is_valid}")
            
        except Exception as e:
            logger.error(f"Error validating sequence integrity for {class_section}: {e}")
            result.add_error(f"Validation error: {str(e)}")
        
        return result
    
    @staticmethod
    def calculate_progress(class_section: ClassSection) -> ProgressMetrics:
        """
        Computes completion percentage and metrics for a class section
        Uses Django cache to avoid redundant queries (1 hour timeout)
        """
        from django.core.cache import cache
        
        # Check cache first
        cache_key = f"progress_metrics:{class_section.id}"
        cached_metrics = cache.get(cache_key)
        if cached_metrics:
            logger.debug(f"Cache hit for progress metrics: {class_section}")
            return cached_metrics
        
        metrics = ProgressMetrics(class_section)
        
        try:
            # Step 1: Detect Grouping Context for Metrics
            # We use the same logic as the sequence calculator: 
            # If not grouped TODAY, use individual class metrics.
            from .models import CalendarDate
            from django.utils import timezone
            
            today = timezone.localdate()
            lookup_class = class_section
            
            todays_entry = CalendarDate.objects.filter(
                date=today
            ).filter(
                models.Q(class_sections=class_section) | models.Q(class_section=class_section)
            ).prefetch_related('class_sections').first()
            
            if todays_entry and todays_entry.class_sections.exists() and todays_entry.class_sections.count() > 1:
                group_members = list(todays_entry.class_sections.all())
                lookup_class = SessionSequenceCalculator._get_group_leader(group_members)
                logger.info(f"Metrics Sync: Using grouped context (Leader={lookup_class.display_name}) for {class_section.display_name}")
            else:
                logger.info(f"Metrics Sync: Using individual context for {class_section.display_name}")
            
            # Use lookup_class for metric calculation
            # Get all planned sessions
            planned_sessions = PlannedSession.objects.filter(
                class_section=lookup_class,
                is_active=True
            )
            
            # Step 1: Detect curriculum sessions (Days 1-150 only)
            curriculum_sessions = planned_sessions.filter(day_number__lte=150)
            metrics.total_sessions = curriculum_sessions.count()
            
            # Step 2: Calculate counts only for standard curriculum
            # (Exams / Day 999 are excluded from these badge metrics)
            metrics.conducted_sessions = ActualSession.objects.filter(
                planned_session__in=curriculum_sessions,
                status=SessionStatus.CONDUCTED
            ).count()
            
            metrics.cancelled_sessions = ActualSession.objects.filter(
                planned_session__in=curriculum_sessions,
                status=SessionStatus.CANCELLED
            ).count()
            
            metrics.holiday_sessions = ActualSession.objects.filter(
                planned_session__in=curriculum_sessions,
                status=SessionStatus.HOLIDAY
            ).count()
            
            # Step 3: Calculate pending sessions accurately (Days 1-150 minus CONDUCTED days)
            completed_days = ActualSession.objects.filter(
                planned_session__in=curriculum_sessions,
                status=SessionStatus.CONDUCTED
            ).values_list('planned_session__day_number', flat=True).distinct().count()
            
            metrics.pending_sessions = metrics.total_sessions - completed_days
            
            # Step 4: Calculate completion percentage
            completed_total = metrics.conducted_sessions + metrics.cancelled_sessions
            if metrics.total_sessions > 0:
                metrics.completion_percentage = (completed_total / metrics.total_sessions) * 100
            
            metrics.is_completed = completed_total >= metrics.total_sessions and metrics.total_sessions > 0
            
            # Get next session
            next_session = SessionSequenceCalculator.get_next_pending_session(class_section)
            metrics.current_session = next_session
            if next_session is not None:
                metrics.next_day_number = next_session.day_number
            else:
                # All sessions completed
                metrics.next_day_number = 151  # Beyond the sequence
            
            # Cache the metrics for 1 hour
            cache.set(cache_key, metrics, 3600)
            
        except Exception as e:
            logger.error(f"Error calculating progress for {class_section}: {e}")
        
        return metrics
    
    @staticmethod
    def get_facilitator_progress(class_section: ClassSection, facilitator: User) -> ProgressMetrics:
        """
        Computes progress metrics specific to a facilitator on a class section
        """
        metrics = ProgressMetrics(class_section)
        
        try:
            # Check if this class is part of a grouped session
            first_planned = PlannedSession.objects.filter(
                class_section=class_section,
                is_active=True
            ).order_by('day_number').first()
            
            # For grouped sessions, use the primary class's sessions
            if first_planned and first_planned.grouped_session_id:
                primary_session = PlannedSession.objects.filter(
                    grouped_session_id=first_planned.grouped_session_id,
                    day_number=1
                ).select_related('class_section').order_by('id').first()
                
                if primary_session:
                    class_section = primary_session.class_section
            
            # Get all planned sessions
            planned_sessions = PlannedSession.objects.filter(
                class_section=class_section,
                is_active=True
            )
            
            metrics.total_sessions = planned_sessions.count()
            
            # Count sessions by status for this facilitator
            # For grouped sessions, count unique planned_session_ids to avoid duplicates
            status_counts = ActualSession.objects.filter(
                planned_session__in=planned_sessions,
                facilitator=facilitator
            ).values('status').annotate(count=Count('planned_session_id', distinct=True))
            
            for status_count in status_counts:
                status = status_count['status']
                count = status_count['count']
                
                if status == SessionStatus.CONDUCTED:
                    metrics.conducted_sessions = count
                elif status == SessionStatus.CANCELLED:
                    metrics.cancelled_sessions = count
                elif status == SessionStatus.HOLIDAY:
                    metrics.holiday_sessions = count
            
            # Calculate pending sessions 
            # ACCURATE COUNT: Count days actually touched by THIS facilitator
            completed_days = ActualSession.objects.filter(
                planned_session__in=planned_sessions,
                facilitator=facilitator,
                status=SessionStatus.CONDUCTED
            ).values_list('planned_session__day_number', flat=True).distinct().count()
            
            metrics.pending_sessions = metrics.total_sessions - completed_days
            
            # Calculate completion percentage
            completed_sessions = metrics.conducted_sessions + metrics.cancelled_sessions
            if metrics.total_sessions > 0:
                metrics.completion_percentage = (completed_sessions / metrics.total_sessions) * 100
            
            # Get next session for this facilitator
            from .services.facilitator_session_continuation import FacilitatorSessionContinuation
            next_fac_session = FacilitatorSessionContinuation.get_next_session_for_facilitator(
                class_section, facilitator
            )
            metrics.current_session = next_fac_session
            if next_fac_session is not None:
                metrics.next_day_number = next_fac_session.day_number
            else:
                metrics.next_day_number = 151
            
            logger.info(f"Progress metrics for {facilitator} on {class_section}: {metrics.completion_percentage}% complete")
            
        except Exception as e:
            logger.error(f"Error calculating facilitator progress for {facilitator} on {class_section}: {e}")
        
        return metrics
    
    @staticmethod
    def get_session_history(class_section: ClassSection, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Returns session history with status information
        """
        try:
            # Get all actual sessions with their planned sessions
            actual_sessions = ActualSession.objects.filter(
                planned_session__class_section=class_section
            ).select_related('planned_session', 'facilitator').order_by('-date')[:limit]
            
            history = []
            for actual in actual_sessions:
                history.append({
                    'day_number': actual.planned_session.day_number,
                    'title': actual.planned_session.title,
                    'date': actual.date,
                    'status': actual.status,
                    'facilitator': actual.facilitator.full_name if actual.facilitator else 'Unknown',
                    'duration_minutes': actual.duration_minutes,
                    'attendance_marked': actual.attendance_marked,
                    'cancellation_reason': actual.get_cancellation_reason_display() if actual.cancellation_reason else None,
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting session history for {class_section}: {e}")
            return []


class SessionStatusManager:
    """
    Manages session status transitions and business rules
    Handles conduct, holiday, and cancellation logic
    """
    
    @staticmethod
    def _invalidate_progress_cache(class_section: ClassSection):
        """Invalidate cached progress metrics when session status changes"""
        from django.core.cache import cache
        cache_key = f"progress_metrics:{class_section.id}"
        cache.delete(cache_key)
        logger.info(f"Invalidated progress cache for {class_section}")
    
    @staticmethod
    def complete_session(actual_session: ActualSession, facilitator: User, 
                        remarks: str = "") -> ActualSession:
        """
        Marks session as CONDUCTED and optionally cleans up other grouped sessions.
        This is typically called when teacher feedback is submitted.
        """
        try:
            with transaction.atomic():
                # 1. Update the primary actual session
                actual_session.status = SessionStatus.CONDUCTED
                actual_session.status_changed_by = facilitator
                actual_session.status_change_reason = 'Teacher feedback submitted'
                if remarks:
                    actual_session.remarks = remarks
                actual_session.save()

                # 2. Handle Grouped Sessions (Sync status across the group)
                # CRITICAL: Only sync if they share a valid, non-None grouped_session_id
                planned_session = actual_session.planned_session
                today = actual_session.date
                group_members = get_grouped_classes_for_session(planned_session, today)
                
                if len(group_members) > 1 and planned_session.grouped_session_id:
                    other_actuals = ActualSession.objects.filter(
                        date=today,
                        planned_session__grouped_session_id=planned_session.grouped_session_id,
                        planned_session__day_number=planned_session.day_number,
                        planned_session__class_section__in=group_members
                    ).exclude(id=actual_session.id)
                    
                    updated_count = other_actuals.update(
                        status=SessionStatus.CONDUCTED,
                        status_changed_by=facilitator,
                        status_change_reason=f'Teacher feedback submitted (Group Sync - Day {planned_session.day_number})'
                    )
                    logger.info(f"Synced CONDUCTED status to {updated_count} other sessions in group")

                # 3. Update Progress Tracker & Invalidate Cache for ALL members
                for cls in group_members:
                    ClassSessionProgress.objects.filter(
                        date=today,
                        class_section=cls
                    ).update(status='completed')
                    
                    # Invalidate progress cache
                    SessionStatusManager._invalidate_progress_cache(cls)

                logger.info(f"Session completed (CONDUCTED): {planned_session} by {facilitator} (Group size: {len(group_members)})")
                return actual_session

        except Exception as e:
            logger.error(f"Error completing session {actual_session.id}: {e}")
            raise ValidationError(f"Failed to complete session: {str(e)}")

    @staticmethod
    def conduct_session(planned_session: PlannedSession, facilitator: User, 
                       remarks: str = "", duration_minutes: Optional[int] = None) -> ActualSession:
        """
        Starts session and creates it with PENDING status.
        Session will be marked as CONDUCTED only when feedback is saved.
        """
        try:
            with transaction.atomic():
                # Create or update actual session with PENDING status
                actual_session, created = ActualSession.objects.get_or_create(
                    planned_session=planned_session,
                    date=timezone.localdate(),
                    defaults={
                        'facilitator': facilitator,
                        'status': SessionStatus.PENDING,
                        'remarks': remarks,
                        'conducted_at': timezone.now(),
                        'duration_minutes': duration_minutes,
                        'status_changed_by': facilitator,
                        'status_change_reason': 'Session started - pending feedback'
                    }
                )
                
                if not created:
                    # Update existing session to PENDING if not already completed
                    if actual_session.status != SessionStatus.CONDUCTED:
                        actual_session.status = SessionStatus.PENDING
                        actual_session.facilitator = facilitator
                        actual_session.remarks = remarks
                        actual_session.conducted_at = timezone.now()
                        actual_session.duration_minutes = duration_minutes
                        actual_session.status_changed_by = facilitator
                        actual_session.status_change_reason = 'Session started - pending feedback'
                        actual_session.save()
                
                # [GROUP-AWARE] Identify all classes in the group
                today = timezone.localdate()
                group_members = get_grouped_classes_for_session(planned_session, today)
                
                # Update ClassSessionProgress for ALL classes in the group
                for cls in group_members:
                    progress, _ = ClassSessionProgress.objects.get_or_create(
                        date=today,
                        class_section=cls,
                        defaults={
                            'day_number': planned_session.day_number,
                            'status': 'pending',
                            'is_grouped': len(group_members) > 1,
                            'grouped_session_id': planned_session.grouped_session_id
                        }
                    )
                    
                    if progress.status != 'pending' or progress.day_number != planned_session.day_number:
                        progress.status = 'pending'
                        progress.day_number = planned_session.day_number
                        progress.save(update_fields=['status', 'day_number'])
                    
                    # Invalidate progress cache for each member
                    SessionStatusManager._invalidate_progress_cache(cls)
                
                logger.info(f"Session started (PENDING): {planned_session} by {facilitator} (Group size: {len(group_members)})")
                return actual_session
                
        except Exception as e:
            logger.error(f"Error starting session {planned_session}: {e}")
            raise ValidationError(f"Failed to start session: {str(e)}")
    
    @staticmethod
    def mark_holiday(planned_session: PlannedSession, facilitator: User, 
                    reason: str = "") -> ActualSession:
        """
        Marks session as holiday while preserving for future conduct
        """
        try:
            with transaction.atomic():
                actual_session, created = ActualSession.objects.get_or_create(
                    planned_session=planned_session,
                    date=timezone.localdate(),
                    defaults={
                        'facilitator': facilitator,
                        'status': SessionStatus.HOLIDAY,
                        'remarks': reason,
                        'can_be_rescheduled': True,
                        'status_changed_by': facilitator,
                        'status_change_reason': f'Marked as holiday: {reason}'
                    }
                )
                
                if not created:
                    # Update existing session
                    actual_session.status = SessionStatus.HOLIDAY
                    actual_session.facilitator = facilitator
                    actual_session.remarks = reason
                    actual_session.can_be_rescheduled = True
                    actual_session.status_changed_by = facilitator
                    actual_session.status_change_reason = f'Marked as holiday: {reason}'
                    actual_session.save()
                
                # [GROUP-AWARE] Identify all classes in the group
                today = timezone.localdate()
                group_members = get_grouped_classes_for_session(planned_session, today)
                
                # UPDATE PROGRESS TRACKER: Holiday does NOT move to next day for ANY member
                for cls in group_members:
                    ClassSessionProgress.objects.filter(
                        date=today,
                        class_section=cls
                    ).update(status='pending')
                    
                    # Invalidate progress cache
                    SessionStatusManager._invalidate_progress_cache(cls)
                
                logger.info(f"Session marked as holiday: {planned_session} by {facilitator} (Group size: {len(group_members)})")
                return actual_session
                
        except Exception as e:
            logger.error(f"Error marking session as holiday {planned_session}: {e}")
            raise ValidationError(f"Failed to mark session as holiday: {str(e)}")
    
    @staticmethod
    def cancel_session(planned_session: PlannedSession, facilitator: User, 
                      cancellation_reason: str, remarks: str = "") -> ActualSession:
        """
        Permanently cancels session and moves to next day
        """
        # Validate cancellation reason
        valid_reasons = [choice[0] for choice in CANCELLATION_REASONS]
        if cancellation_reason not in valid_reasons:
            raise ValidationError(f"Invalid cancellation reason. Must be one of: {valid_reasons}")
        
        try:
            with transaction.atomic():
                actual_session, created = ActualSession.objects.get_or_create(
                    planned_session=planned_session,
                    date=timezone.localdate(),
                    defaults={
                        'facilitator': facilitator,
                        'status': SessionStatus.CANCELLED,
                        'remarks': remarks,
                        'cancellation_reason': cancellation_reason,
                        'cancellation_category': cancellation_reason,
                        'is_permanent_cancellation': True,
                        'can_be_rescheduled': False,
                        'status_changed_by': facilitator,
                        'status_change_reason': f'Cancelled: {dict(CANCELLATION_REASONS)[cancellation_reason]}'
                    }
                )
                
                if not created:
                    # Update existing session
                    actual_session.status = SessionStatus.CANCELLED
                    actual_session.facilitator = facilitator
                    actual_session.remarks = remarks
                    actual_session.cancellation_reason = cancellation_reason
                    actual_session.cancellation_category = cancellation_reason
                    actual_session.is_permanent_cancellation = True
                    actual_session.can_be_rescheduled = False
                    actual_session.status_changed_by = facilitator
                    actual_session.status_change_reason = f'Cancelled: {dict(CANCELLATION_REASONS)[cancellation_reason]}'
                    actual_session.save()
                
                # [GROUP-AWARE] Identify all classes in the group
                today = timezone.localdate()
                group_members = get_grouped_classes_for_session(planned_session, today)
                
                # UPDATE PROGRESS TRACKER: Cancellation also moves to next day for ALL members
                for cls in group_members:
                    ClassSessionProgress.objects.filter(
                        date=today,
                        class_section=cls
                    ).update(status='completed')
                    
                    # Invalidate progress cache
                    SessionStatusManager._invalidate_progress_cache(cls)
                
                logger.info(f"Session cancelled: {planned_session} by {facilitator} (Group size: {len(group_members)}), reason: {cancellation_reason}")
                return actual_session
                
        except Exception as e:
            logger.error(f"Error cancelling session {planned_session}: {e}")
            raise ValidationError(f"Failed to cancel session: {str(e)}")
    
    @staticmethod
    def validate_status_change(current_status: str, new_status: str) -> bool:
        """
        Ensures status transitions are valid according to business rules
        """
        valid_transitions = {
            'pending': ['conducted', 'holiday', 'cancelled'],
            'holiday': ['conducted'],  # Holiday sessions can be conducted later
            'conducted': [],  # Conducted sessions cannot be changed
            'cancelled': []   # Cancelled sessions cannot be changed
        }
        
        if current_status not in valid_transitions:
            return False
        
        return new_status in valid_transitions[current_status]


class SessionBulkManager:
    """
    Handles bulk operations on sessions across multiple classes
    """
    
    @staticmethod
    def generate_sessions_for_class(class_section: ClassSection, 
                                  template: SessionBulkTemplate = None,
                                  created_by: User = None) -> Dict[str, Any]:
        """
        Auto-creates 1-150 sessions for new class
        """
        result: Dict[str, Any] = {
            'success': False,
            'created_count': 0,
            'skipped_count': 0,
            'errors': cast(List[str], []),
            'sessions_created': cast(List[Any], [])
        }
        
        try:
            with transaction.atomic():
                # Check if sessions already exist
                existing_sessions = PlannedSession.objects.filter(
                    class_section=class_section,
                    is_active=True
                ).count()
                
                if existing_sessions > 0:
                    result['errors'].append(f"Class already has {existing_sessions} sessions")
                    return result
                
                # Generate 150 sessions
                sessions_to_create = []
                for day_number in range(1, 151):
                    # Use template if provided
                    title = f"Day {day_number}"
                    description = ""
                    
                    if template and template.day_templates:
                        day_template = template.day_templates.get(str(day_number), {})
                        title = day_template.get('title', title)
                        description = day_template.get('description', description)
                    
                    session = PlannedSession(
                        class_section=class_section,
                        day_number=day_number,
                        title=title,
                        description=description,
                        sequence_position=day_number,
                        is_required=True,
                        is_active=True
                    )
                    sessions_to_create.append(session)
                
                # Bulk create sessions
                created_sessions = PlannedSession.objects.bulk_create(sessions_to_create)
                result['created_count'] = len(created_sessions)
                result['success'] = True
                
                # Update template usage count
                if template:
                    template.usage_count += 1
                    template.save()
                
                logger.info(f"Generated {result['created_count']} sessions for {class_section}")
                
        except Exception as e:
            logger.error(f"Error generating sessions for {class_section}: {e}")
            result['errors'].append(str(e))
        
        return result
    
    @staticmethod
    def repair_sequence_gaps(class_section: ClassSection, created_by: User = None) -> Dict[str, Any]:
        """
        Fixes missing sessions in the 1-150 sequence
        """
        result: Dict[str, Any] = {
            'success': False,
            'created_count': 0,
            'errors': cast(List[str], []),
            'gaps_filled': cast(List[int], [])
        }
        
        try:
            with transaction.atomic():
                # [FIX] For grouped sessions, secondary classes shouldn't have their own 150 sessions
                from .models import GroupedSession
                group = GroupedSession.objects.filter(class_sections=class_section).first()
                if group:
                    # Find primary class
                    primary_ps = PlannedSession.objects.filter(
                        grouped_session_id=group.grouped_session_id,
                        day_number=1
                    ).select_related('class_section').order_by('id').first()
                    
                    if primary_ps and primary_ps.class_section.id != class_section.id:
                        # This is a secondary class. It relies on the primary's sessions.
                        # We don't need to "repair" its local sequence if it's using the group's.
                        result['success'] = True
                        return result
                    elif not primary_ps:
                        # Group exists but no primary session? This is a broken state.
                        # We should probably allow repaired for the "first" class in the group.
                        pass
                
                # Get existing day numbers
                existing_days = set(
                    PlannedSession.objects.filter(
                        class_section=class_section,
                        is_active=True
                    ).values_list('day_number', flat=True)
                )
                
                # Find missing days
                all_days = set(range(1, 151))
                missing_days = all_days - existing_days
                
                if not missing_days:
                    result['success'] = True
                    return result
                
                # Check for existing but INACTIVE sessions for these days
                # This prevents unique constraint violations
                inactive_sessions = PlannedSession.objects.filter(
                    class_section=class_section,
                    day_number__in=missing_days,
                    is_active=False
                )
                
                activated_count = 0
                if inactive_sessions.exists():
                    activated_count = inactive_sessions.update(is_active=True)
                    # Update local tracking of what's still missing
                    missing_days = missing_days - set(inactive_sessions.values_list('day_number', flat=True))
                
                # Create remaining missing sessions
                sessions_to_create = []
                for day_number in sorted(missing_days):
                    session = PlannedSession(
                        class_section=class_section,
                        day_number=day_number,
                        title=f"Day {day_number}",
                        description="Auto-generated to fill sequence gap",
                        sequence_position=day_number,
                        is_required=True,
                        is_active=True
                    )
                    sessions_to_create.append(session)
                
                # Bulk create missing sessions
                created_sessions = []
                if sessions_to_create:
                    created_sessions = PlannedSession.objects.bulk_create(sessions_to_create)
                
                result['created_count'] = len(created_sessions) + activated_count
                result['gaps_filled'] = sorted(list(all_days - existing_days))
                result['success'] = True
                
                if result['created_count'] > 0:
                    logger.info(f"Repaired {result['created_count']} session gaps for {class_section} ({activated_count} reactivated, {len(created_sessions)} created)")
                result['success'] = True
                
                logger.info(f"Filled {result['created_count']} sequence gaps for {class_section}")
                
        except Exception as e:
            logger.error(f"Error repairing sequence gaps for {class_section}: {e}")
            result['errors'] = cast(List[str], result['errors'])
            result['errors'].append(str(e))
        
        return result
