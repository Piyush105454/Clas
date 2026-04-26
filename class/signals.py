"""
Django signals for automatic session generation and growth analysis
Handles automatic creation of 1-150 sessions when new classes are created
Handles automatic growth analysis when attendance or quiz data is added
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging
from datetime import datetime, timedelta

from .models import (
    ClassSection, PlannedSession, SessionBulkTemplate, 
    Attendance, StudentQuiz, StudentAttendanceSummary, AttendanceStatus,
    FacilitatorAttendanceSummary, FacilitatorSchool, ActualSession, SessionStatus,
    FeedbackAnalytics
)
from .session_management import SessionBulkManager

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=ClassSection)
def auto_generate_sessions_for_new_class(sender, instance, created, **kwargs):
    """
    Automatically generate 1-150 sessions when a new class is created
    """
    if created:  # Only for newly created classes
        try:
            logger.info(f"Auto-generating sessions for new class: {instance}")
            
            # Check if sessions already exist (safety check)
            existing_sessions = PlannedSession.objects.filter(
                class_section=instance,
                is_active=True
            ).count()
            
            if existing_sessions > 0:
                logger.warning(f"Class {instance} already has {existing_sessions} sessions, skipping auto-generation")
                return
            
            # Try to get a default template
            default_template = SessionBulkTemplate.objects.filter(
                is_active=True,
                language='english'  # Default to English
            ).first()
            
            # Generate sessions using SessionBulkManager
            result = SessionBulkManager.generate_sessions_for_class(
                class_section=instance,
                template=default_template,
                created_by=None  # System generated
            )
            
            if result['success']:
                logger.info(f"Successfully auto-generated {result['created_count']} sessions for {instance}")
            else:
                logger.error(f"Failed to auto-generate sessions for {instance}: {result['errors']}")
                
        except Exception as e:
            logger.error(f"Error in auto-generating sessions for {instance}: {e}")


@receiver(post_save, sender=SessionBulkTemplate)
def update_template_usage_stats(sender, instance, created, **kwargs):
    """
    Update template statistics when templates are used
    """
    if not created:  # Only for updates, not new creations
        logger.info(f"Template {instance.name} usage updated")


@receiver(post_save, sender=Attendance)
def trigger_growth_analysis_on_attendance(sender, instance, created, **kwargs):
    """
    Trigger growth analysis when attendance is recorded
    """
    if created:
        try:
            from .services.student_growth_service import StudentGrowthAnalysisService
            
            enrollment = instance.enrollment
            logger.info(f"Triggering growth analysis for {enrollment.student.full_name}")
            StudentGrowthAnalysisService.update_growth_analysis(enrollment)
        except Exception as e:
            logger.error(f"Error triggering growth analysis on attendance: {e}")


@receiver(post_save, sender=StudentQuiz)
def trigger_growth_analysis_on_quiz(sender, instance, created, **kwargs):
    """
    Trigger growth analysis when quiz score is recorded
    """
    if created:
        try:
            from .services.student_growth_service import StudentGrowthAnalysisService
            
            enrollment = instance.enrollment
            logger.info(f"Triggering growth analysis for {enrollment.student.full_name}")
            StudentGrowthAnalysisService.update_growth_analysis(enrollment)
        except Exception as e:
            logger.error(f"Error triggering growth analysis on quiz: {e}")


# =========================
# ATTENDANCE SUMMARY SIGNALS (PHASE 2 SCALABILITY)
# =========================

def recount_student_attendance(enrollment):
    """Recalculate complete summary for a student (Safe but slower)"""
    # Safety check: If enrollment is being deleted, don't recount
    if not enrollment or not Enrollment.objects.filter(id=enrollment.id).exists():
        return

    try:
        from django.db.models import Count
        
        # We only update if the summary already exists OR if we are not in a deletion
        summary = StudentAttendanceSummary.objects.filter(enrollment=enrollment).first()
        
        if not summary:
            # If it doesn't exist, only create it if the enrollment still exists
            if not Enrollment.objects.filter(id=enrollment.id).exists():
                return
            summary = StudentAttendanceSummary(enrollment=enrollment)
        
        stats = Attendance.objects.filter(enrollment=enrollment).values('status').annotate(
            count=Count('id')
        )
        
        # Reset
        summary.present_count = 0
        summary.absent_count = 0
        summary.leave_count = 0
        
        for s in stats:
            if s['status'] == AttendanceStatus.PRESENT:
                summary.present_count = s['count']
            elif s['status'] == AttendanceStatus.ABSENT:
                summary.absent_count = s['count']
            elif s['status'] == AttendanceStatus.LEAVE:
                summary.leave_count = s['count']
        
        summary.save()
    except Exception as e:
        logger.error(f"Error recounting student attendance: {e}")


@receiver(post_save, sender=Attendance)
def update_attendance_summary_on_save(sender, instance, created, **kwargs):
    """
    Automatically update StudentAttendanceSummary when Attendance is saved.
    This ensures the summary table stays in sync for real-time reporting.
    """
    try:
        from django.db.models import F
        from django.utils import timezone
        
        enrollment = instance.enrollment
        
        # For new records, we can do an efficient incremental update
        if created:
            summary, _ = StudentAttendanceSummary.objects.get_or_create(enrollment=enrollment)
            if instance.status == AttendanceStatus.PRESENT:
                summary.present_count = F('present_count') + 1
            elif instance.status == AttendanceStatus.ABSENT:
                summary.absent_count = F('absent_count') + 1
            elif instance.status == AttendanceStatus.LEAVE:
                summary.leave_count = F('leave_count') + 1
            
            summary.last_marked_at = timezone.now()
            summary.save()
        else:
            # For updates, a full recount is safest to avoid complex delta logic
            recount_student_attendance(enrollment)
            
    except Exception as e:
        logger.error(f"Error updating attendance summary on save: {e}")


@receiver(post_delete, sender=Attendance)
def update_attendance_summary_on_delete(sender, instance, **kwargs):
    """Recount attendance stats when a record is deleted"""
    try:
        recount_student_attendance(instance.enrollment)
    except Exception as e:
        logger.error(f"Error updating attendance summary on delete: {e}")


# =========================
# FACILITATOR SUMMARY SIGNALS (PHASE 2 SCALABILITY)
# =========================

def recount_facilitator_stats(facilitator):
    """Recalculate complete summary for a facilitator (Safe but slower)"""
    # Safety check: If facilitator is being deleted, don't recount
    if not facilitator or not User.objects.filter(id=facilitator.id).exists():
        return

    try:
        from django.db.models import Avg
        
        # IMPORTANT: Use filter().first() instead of get_or_create() 
        # to avoid creating "Zombie" child records during a parent's deletion transaction.
        summary = FacilitatorAttendanceSummary.objects.filter(facilitator=facilitator).first()
        
        if not summary:
            # If it doesn't exist, only create it if the user still exists in the DB
            if not User.objects.filter(id=facilitator.id).exists():
                return
            summary = FacilitatorAttendanceSummary(facilitator=facilitator)
        
        # 1. Sessions Conducted
        summary.sessions_conducted = ActualSession.objects.filter(
            facilitator=facilitator,
            status=SessionStatus.CONDUCTED
        ).count()
        
        # 2. Last Active Date
        last_session = ActualSession.objects.filter(
            facilitator=facilitator,
            status=SessionStatus.CONDUCTED
        ).order_by('-date').first()
        if last_session:
            summary.last_active_date = last_session.date
            
        # 3. Schools Count
        summary.schools_count = FacilitatorSchool.objects.filter(
            facilitator=facilitator,
            is_active=True
        ).count()
        
        # 4. Average Rating (From FeedbackAnalytics)
        avg_score = FeedbackAnalytics.objects.filter(
            actual_session__facilitator=facilitator
        ).aggregate(avg_val=Avg('session_quality_score'))['avg_val']
        
        summary.average_rating = avg_score or 0.0
        
        summary.save()
    except Exception as e:
        logger.error(f"Error recounting facilitator stats: {e}")


@receiver(post_save, sender=ActualSession)
def update_facilitator_summary_on_session_save(sender, instance, **kwargs):
    """Update facilitator stats when a session status changes to CONDUCTED"""
    if instance.facilitator:
        recount_facilitator_stats(instance.facilitator)


@receiver(post_delete, sender=ActualSession)
def update_facilitator_summary_on_session_delete(sender, instance, **kwargs):
    """Update facilitator stats when a session is deleted"""
    if instance.facilitator:
        recount_facilitator_stats(instance.facilitator)


@receiver(post_save, sender=FacilitatorSchool)
def update_facilitator_summary_on_school_save(sender, instance, **kwargs):
    """Update facilitator school count assignments"""
    recount_facilitator_stats(instance.facilitator)


@receiver(post_delete, sender=FacilitatorSchool)
def update_facilitator_summary_on_school_delete(sender, instance, **kwargs):
    """Update facilitator school count assignments on removal"""
    recount_facilitator_stats(instance.facilitator)


@receiver(post_save, sender=FeedbackAnalytics)
def update_facilitator_summary_on_feedback(sender, instance, **kwargs):
    """Update facilitator average rating when new analytics are generated"""
    facilitator = instance.actual_session.facilitator
    if facilitator:
        recount_facilitator_stats(facilitator)