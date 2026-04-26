"""
Supervisor Facilitator Daily Profile Views
Provides comprehensive daily view of facilitator activities and performance
"""

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, F, Sum
from django.http import JsonResponse

from .models import (
    User, FacilitatorSchool, ClassSection, FacilitatorTask, 
    SessionFeedback, LessonPlanUpload, ActualSession, PlannedSession,
    Student, Enrollment, CurriculumSession
)
from .decorators import supervisor_required, admin_required
from .services.daily_profile_service import DailyProfileService


def _facilitator_daily_profile_logic(request, facilitator_id, base_template='supervisor/shared/base.html'):
    """Core logic for facilitator daily profile detail (undecorated)"""
    """
    Display comprehensive daily profile for a facilitator
    Shows all activities, tasks, feedback, and attendance for a selected date
    """
    
    facilitator = get_object_or_404(User, id=facilitator_id, role__name__iexact="FACILITATOR")
    
    # Get selected date from request, default to today
    date_str = request.GET.get('date', timezone.now().date().isoformat())
    selected_date = DailyProfileService.validate_date(date_str)
    if not selected_date:
        selected_date = timezone.now().date()
    
    # Get daily profile data using service
    service = DailyProfileService(facilitator, selected_date)
    daily_data = service.get_daily_profile()
    
    context = {
        'facilitator': facilitator,
        'selected_date': selected_date,
        'daily_data': daily_data,
        'sessions': daily_data['sessions'],
        'lesson_plans': daily_data['lesson_plans'],
        'tasks': daily_data['tasks'],
        'feedback_provided': daily_data['feedback']['provided'],
        'attendance_metrics': daily_data['attendance_metrics'],
        'base_template': base_template, # Support dynamic sidebar
    }
    
    return render(request, 'supervisor/facilitators/daily_profile.html', context)


@login_required
@supervisor_required
def supervisor_facilitator_daily_profile(request, facilitator_id, base_template='supervisor/shared/base.html'):
    """Supervisor entry point for daily profile"""
    return _facilitator_daily_profile_logic(request, facilitator_id, base_template=base_template)


@login_required
@admin_required
def admin_facilitator_daily_profile(request, facilitator_id):
    """Admin entry point for daily profile (uses admin layout)"""
    return _facilitator_daily_profile_logic(request, facilitator_id, base_template='admin/shared/base.html')


def _facilitator_daily_profile_api_logic(request, facilitator_id):
    """Core logic for facilitator daily profile API (undecorated)"""
    try:
        facilitator = get_object_or_404(User, id=facilitator_id, role__name__iexact="FACILITATOR")
    except Exception as e:
        return JsonResponse({
            'error': 'Facilitator not found',
            'status': 'error'
        }, status=404)
    
    # Get selected date from request
    date_str = request.GET.get('date', timezone.now().date().isoformat())
    selected_date = DailyProfileService.validate_date(date_str)
    if not selected_date:
        selected_date = timezone.now().date()
    
    try:
        # Get daily profile data using service
        service = DailyProfileService(facilitator, selected_date)
        daily_data = service.get_daily_profile()
        
        return JsonResponse({
            **daily_data,
            'status': 'success'
        })
    except Exception as e:
        return JsonResponse({
            'error': f'Error loading data: {str(e)}',
            'status': 'error'
        }, status=500)


# Admin-accessible wrappers
# =====================================================


@login_required
@admin_required
def admin_facilitator_daily_profile_api(request, facilitator_id):
    """Admin wrapper: daily profile API (permissions check only)"""
    return _facilitator_daily_profile_api_logic(request, facilitator_id)


@login_required
@supervisor_required
def supervisor_facilitator_daily_profile_api(request, facilitator_id):
    """Supervisor entry point for daily profile API"""
    return _facilitator_daily_profile_api_logic(request, facilitator_id)
