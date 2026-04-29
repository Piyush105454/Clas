"""
Daily Profile Service
Aggregates all facilitator data for a specific date
"""

from datetime import datetime, date
from django.utils import timezone
from django.db.models import Q, Count, Sum
from typing import Dict, List, Any, Optional

from ..models import (
    User, ActualSession, LessonPlanUpload, FacilitatorTask,
    SessionFeedback, StudentFeedback, Enrollment, FacilitatorSchool
)


class DailyProfileService:
    """Service for aggregating facilitator daily profile data"""
    
    def __init__(self, facilitator: User, selected_date: date):
        """
        Initialize the service with a facilitator and date
        
        Args:
            facilitator: User object with role FACILITATOR
            selected_date: Date to fetch data for
        """
        self.facilitator = facilitator
        self.selected_date = selected_date
        
    def get_daily_profile(self) -> Dict[str, Any]:
        """
        Get complete daily profile data for the facilitator
        
        Returns:
            Dictionary containing all daily data
        """
        return {
            'facilitator': self._get_facilitator_info(),
            'selected_date': self.selected_date.isoformat(),
            'sessions': self._get_sessions(),
            'lesson_plans': self._get_lesson_plans(),
            'tasks': self._get_tasks(),
            'feedback': self._get_feedback(),
            'attendance_metrics': self._get_attendance_metrics(),
        }
    
    def _get_facilitator_info(self) -> Dict[str, Any]:
        """Get basic facilitator information"""
        return {
            'id': str(self.facilitator.id),
            'name': self.facilitator.full_name,
            'email': self.facilitator.email,
        }
    
    def _get_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions for the selected date - PURE ACTIVE GROUPING"""
        from ..session_management import get_grouped_classes_for_session
        
        # [FIX] STRICT SCHOOL FILTERING
        # Only show sessions for schools the facilitator is actually assigned to
        from ..models import FacilitatorSchool, SessionStatus, Attendance, SessionStepStatus
        from django.db.models import Exists, OuterRef
        
        assigned_school_ids = FacilitatorSchool.objects.filter(
            facilitator=self.facilitator,
            is_active=True
        ).values_list('school_id', flat=True)
        
        # Fast subqueries using Exists
        has_attendance = Attendance.objects.filter(actual_session_id=OuterRef('id'))
        has_steps = SessionStepStatus.objects.filter(
            planned_session_id=OuterRef('planned_session_id'),
            session_date=OuterRef('date')
        )
        
        sessions = ActualSession.objects.filter(
            facilitator=self.facilitator,
            date=self.selected_date,
            planned_session__class_section__school_id__in=assigned_school_ids
        ).filter(
            Q(status__in=[SessionStatus.CONDUCTED, SessionStatus.CANCELLED, SessionStatus.HOLIDAY]) |
            Exists(has_attendance) |
            Exists(has_steps)
        ).select_related(
            'planned_session',
            'planned_session__class_section',
            'planned_session__class_section__school'
        ).distinct()
        
        processed_session_ids = set()
        session_list = []
        
        # Sort sessions by day_number to find a consistent "representative" for a group
        sorted_sessions = list(sessions)
        
        for session in sorted_sessions:
            if session.id in processed_session_ids:
                continue
                
            pinned_planned = session.planned_session
            if not pinned_planned:
                continue
                
            # Determine if this session is part of an ACTIVE group today
            group_members = get_grouped_classes_for_session(pinned_planned, self.selected_date)
            is_actively_grouped = len(group_members) > 1
            
            if is_actively_grouped:
                # Group sessions by active members (ignore historical grouped_session_id)
                # We find all sessions today that belong to the active group members
                group_sessions = [s for s in sorted_sessions if 
                                 s.planned_session.class_section in group_members]
                
                # Combine classes for display
                classes = [f"{s.planned_session.class_section.class_level} - {s.planned_session.class_section.section}" for s in group_sessions]
                class_section_str = ", ".join(sorted(set(classes)))
                
                # Use the session with the highest day_number or specific title for the group name
                day_numbers = sorted(list(set([s.planned_session.day_number for s in group_sessions if s.planned_session])))
                if len(day_numbers) == 1:
                    group_name = pinned_planned.title or f"Day {day_numbers[0]}"
                else:
                    group_name = f"Mixed Session (Days {', '.join(map(str, day_numbers))})"
                
                # Get distinct student_ids across all sessions in this active group
                student_ids = set()
                for s in group_sessions:
                    # Try cached student_id first for performance, fallback to enrollment
                    s_ids = s.attendances.filter(status=1).values_list('student_id', flat=True)
                    if not s_ids:
                        s_ids = s.attendances.filter(status=1).values_list('enrollment__student_id', flat=True)
                    student_ids.update(s_ids)
                attendance_count = len(student_ids)
                
                # Enrolled count for active group members
                enrolled_count = Enrollment.objects.filter(
                    class_section__in=group_members,
                    is_active=True
                ).values('student_id').distinct().count()
                
                # Individual class breakdown
                class_breakdown = []
                for s in group_sessions:
                    s_class_name = f"{s.planned_session.class_section.class_level} - {s.planned_session.class_section.section}"
                    s_present = s.attendances.filter(status=1).values('student_id').distinct().count()
                    if s_present == 0:
                        s_present = s.attendances.filter(status=1).values('enrollment__student_id').distinct().count()
                    
                    s_enrolled = Enrollment.objects.filter(class_section=s.planned_session.class_section, is_active=True).count()
                    class_breakdown.append({
                        'class_name': s_class_name,
                        'present': s_present,
                        'enrolled': max(s_present, s_enrolled)
                    })
                
                session_list.append({
                    'id': str(session.id),
                    'name': group_name,
                    'class_section': class_section_str,
                    'status': session.status or 'completed',
                    'students_present': attendance_count,
                    'students_enrolled': max(attendance_count, enrolled_count),
                    'attendance_rate': round((attendance_count / max(1, enrolled_count)) * 100) if enrolled_count > 0 else 0,
                    'school': pinned_planned.class_section.school.name,
                    'class_breakdown': class_breakdown,
                })
                
                # Mark all group sessions as processed
                for gs in group_sessions:
                    processed_session_ids.add(gs.id)
            else:
                # Single session
                attendance_count = session.attendances.filter(status=1).values('student_id').distinct().count()
                if attendance_count == 0:
                     attendance_count = session.attendances.filter(status=1).values('enrollment__student_id').distinct().count()
                
                enrolled_count = Enrollment.objects.filter(
                    class_section=pinned_planned.class_section,
                    is_active=True
                ).count()
                
                session_list.append({
                    'id': str(session.id),
                    'name': pinned_planned.title or f"Day {pinned_planned.day_number}",
                    'class_section': f"{pinned_planned.class_section.class_level} - {pinned_planned.class_section.section}",
                    'status': session.status or 'completed',
                    'students_present': attendance_count,
                    'students_enrolled': max(attendance_count, enrolled_count),
                    'attendance_rate': round((attendance_count / max(1, enrolled_count)) * 100) if enrolled_count > 0 else 0,
                    'school': pinned_planned.class_section.school.name,
                })
                processed_session_ids.add(session.id)
            
        # Sort so it's consistent
        session_list.sort(key=lambda x: x['class_section'])
        
        return session_list
    
    def _get_lesson_plans(self) -> List[Dict[str, Any]]:
        """Get all lesson plans for the selected date"""
        lesson_plans = LessonPlanUpload.objects.filter(
            facilitator=self.facilitator,
            upload_date=self.selected_date
        ).select_related(
            'planned_session',
            'planned_session__class_section',
            'planned_session__class_section__school'
        ).order_by('-upload_date')
        
        lesson_plan_list = []
        for lesson in lesson_plans:
            lesson_plan_list.append({
                'id': str(lesson.id),
                'topic': lesson.planned_session.title if lesson.planned_session else 'Lesson Plan',
                'content_status': 'uploaded',
                'completion_status': 'approved' if lesson.is_approved else 'pending',
                'session_id': str(lesson.planned_session.id) if lesson.planned_session else None,
                'file_name': lesson.file_name,
                'upload_date': lesson.upload_date.isoformat(),
                'class_section': f"{lesson.planned_session.class_section.class_level} - {lesson.planned_session.class_section.section}",
                'school': lesson.planned_session.class_section.school.name,
            })
        
        return lesson_plan_list
    
    def _get_tasks(self) -> List[Dict[str, Any]]:
        """Get all preparation tasks for the selected date"""
        tasks = FacilitatorTask.objects.filter(
            facilitator=self.facilitator,
            created_at__date=self.selected_date
        ).select_related(
            'actual_session',
            'actual_session__planned_session',
            'actual_session__planned_session__class_section',
            'actual_session__planned_session__class_section__school'
        ).order_by('-created_at')
        
        # Get facilitator's assigned schools for fallback
        facilitator_schools = FacilitatorSchool.objects.filter(
            facilitator=self.facilitator,
            is_active=True
        ).select_related('school')
        
        # Get most recent session for this date to use as fallback class
        recent_session = ActualSession.objects.filter(
            facilitator=self.facilitator,
            date=self.selected_date
        ).select_related(
            'planned_session',
            'planned_session__class_section'
        ).order_by('-date').first()
        
        task_list = []
        for task in tasks:
            # Handle tasks with no actual_session
            class_section = 'General Task'
            school = 'No Session'
            
            if task.actual_session and task.actual_session.planned_session:
                # Task has a session - use it
                class_section = f"{task.actual_session.planned_session.class_section.class_level} - {task.actual_session.planned_session.class_section.section}"
                school = task.actual_session.planned_session.class_section.school.name
            elif recent_session and recent_session.planned_session:
                # No session on task, but facilitator has sessions today - use most recent
                class_section = f"{recent_session.planned_session.class_section.class_level} - {recent_session.planned_session.class_section.section}"
                school = recent_session.planned_session.class_section.school.name
            elif facilitator_schools.exists():
                # No sessions today, use assigned school
                school = facilitator_schools.first().school.name
                class_section = 'General Task'
            
            task_list.append({
                'id': str(task.id),
                'description': task.description or 'Preparation Task',
                'due_date': self.selected_date.isoformat(),
                'completion_status': 'completed',
                'media_type': task.media_type,
                'created_at': task.created_at.strftime('%Y-%m-%d'),  # Only date, no time
                'facebook_link': task.facebook_link or '',
                'class_section': class_section,
                'school': school,
            })
        
        return task_list
    
    def _get_feedback(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all feedback for the selected date (Facilitator, Student, Teacher)"""
        
        # Get all sessions for this facilitator on the selected date
        sessions = ActualSession.objects.filter(
            facilitator=self.facilitator,
            date=self.selected_date
        ).values_list('id', flat=True)
        
        all_feedback = []
        
        # 1. Facilitator Feedback (SessionFeedback)
        # Use timezone-aware date range for filtering to avoid warnings
        start_of_day = timezone.make_aware(datetime.combine(self.selected_date, datetime.min.time()))
        end_of_day = timezone.make_aware(datetime.combine(self.selected_date, datetime.max.time()))
        
        facilitator_feedback = SessionFeedback.objects.filter(
            actual_session__facilitator=self.facilitator,
            feedback_date__range=(start_of_day, end_of_day)
        ).select_related(
            'actual_session',
            'actual_session__planned_session',
            'actual_session__planned_session__class_section'
        ).order_by('-feedback_date')
        
        for feedback in facilitator_feedback:
            class_section = 'No Session'
            school = 'No Session'
            if feedback.actual_session and feedback.actual_session.planned_session:
                class_section = f"{feedback.actual_session.planned_session.class_section.class_level} - {feedback.actual_session.planned_session.class_section.section}"
                school = feedback.actual_session.planned_session.class_section.school.name
            
            all_feedback.append({
                'id': str(feedback.id),
                'content': feedback.day_reflection or '',
                'source': 'Facilitator',
                'timestamp': feedback.feedback_date.isoformat(),
                'type': 'facilitator',
                'rating': feedback.rating,
                'class_section': class_section,
                'school': school,
            })
        
        # 2. Student Feedback
        # Use timezone-aware date range for submitted_at
        student_feedback = StudentFeedback.objects.filter(
            actual_session_id__in=sessions,
            submitted_at__range=(start_of_day, end_of_day)
        ).select_related(
            'actual_session',
            'actual_session__planned_session',
            'actual_session__planned_session__class_section'
        ).order_by('-submitted_at')
        
        for feedback in student_feedback:
            class_section = 'No Session'
            school = 'No Session'
            if feedback.actual_session and feedback.actual_session.planned_session:
                class_section = f"{feedback.actual_session.planned_session.class_section.class_level} - {feedback.actual_session.planned_session.class_section.section}"
                school = feedback.actual_session.planned_session.class_section.school.name
            
            all_feedback.append({
                'id': str(feedback.id),
                'content': feedback.description or '',
                'source': 'Student',
                'timestamp': feedback.submitted_at.isoformat(),
                'type': 'student',
                'rating': 0, # Student feedback doesn't have a numerical rating in this model yet
                'class_section': class_section,
                'school': school,
            })
        
        # Sort all feedback by timestamp (newest first)
        all_feedback.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'provided': all_feedback,
            'received': [],
        }
    
    def _get_attendance_metrics(self) -> Dict[str, Any]:
        """Calculate attendance metrics for the selected date"""
        sessions = self._get_sessions()
        
        total_present = sum(s['students_present'] for s in sessions)
        total_enrolled = sum(s['students_enrolled'] for s in sessions)
        
        overall_rate = 0
        if total_enrolled > 0:
            overall_rate = round((total_present / total_enrolled) * 100)
        
        return {
            'overall_rate': overall_rate,
            'total_present': total_present,
            'total_enrolled': total_enrolled,
            'per_session_rates': [s['attendance_rate'] for s in sessions],
        }
    
    @staticmethod
    def validate_date(date_str: str) -> Optional[date]:
        """
        Validate and parse a date string
        
        Args:
            date_str: Date string in format YYYY-MM-DD
            
        Returns:
            date object or None if invalid
        """
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
