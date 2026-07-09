"""
API endpoints for managing session step status.
Handles saving and loading step completion status for grouped and non-grouped sessions.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
import json
import logging

from .models import PlannedSession, SessionStepStatus, ActualSession, ClassSection

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def save_step_status(request):
    """
    Save the completion status of a workflow step.
    
    POST data:
    {
        "planned_session_id": "uuid",
        "session_date": "YYYY-MM-DD",
        "step_number": 1-7,
        "is_completed": true/false,
        "step_content": {...},  # Optional JSON data
        "class_section_id": "uuid" # Optional but highly recommended under global master curriculum model
    }
    """
    try:
        data = json.loads(request.body)
        
        planned_session_id = data.get('planned_session_id')
        session_date = data.get('session_date')
        step_number = data.get('step_number')
        is_completed = data.get('is_completed', False)
        step_content = data.get('step_content', {})
        class_section_id = data.get('class_section_id')
        
        # Validate required fields
        if not all([planned_session_id, session_date, step_number]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: planned_session_id, session_date, step_number'
            }, status=400)
        
        # Validate step number
        if not (1 <= step_number <= 7):
            return JsonResponse({
                'success': False,
                'error': 'Invalid step number. Must be between 1 and 7.'
            }, status=400)
        
        # Get the planned session
        try:
            planned_session = PlannedSession.objects.get(id=planned_session_id)
        except PlannedSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Planned session {planned_session_id} not found'
            }, status=404)
            
        # Get class section
        class_section = None
        if class_section_id:
            try:
                class_section = ClassSection.objects.get(id=class_section_id)
            except ClassSection.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Class section {class_section_id} not found'
                }, status=404)
        else:
            # Fallback: get first active class assigned to facilitator
            class_section = ClassSection.objects.filter(
                school__facilitators__facilitator=request.user,
                school__facilitators__is_active=True
            ).first()
            
        if not class_section:
            return JsonResponse({
                'success': False,
                'error': 'No class section associated with this request'
            }, status=400)
        
        # Create or update the step status for the primary session
        with transaction.atomic():
            step_status, created = SessionStepStatus.objects.update_or_create(
                planned_session=planned_session,
                class_section=class_section,
                session_date=session_date,
                step_number=step_number,
                defaults={
                    'is_completed': is_completed,
                    'step_content': step_content,
                    'facilitator': request.user,
                    'completed_at': timezone.now() if is_completed else None,
                }
            )
            
            # [FIX] AUTO-START ACTUAL SESSION ON ACTION
            # If a step is completed today, ensure the ActualSession exists
            if is_completed and str(session_date) == str(timezone.now().date()):
                from .session_management import SessionStatusManager, get_grouped_classes_for_session
                
                # Check if session already exists
                actual_exists = ActualSession.objects.filter(
                    planned_session=planned_session,
                    class_section=class_section,
                    date=session_date
                ).exists()
                
                if not actual_exists:
                    # Start it!
                    actual_session = SessionStatusManager.conduct_session(
                        planned_session=planned_session,
                        class_section=class_section,
                        facilitator=request.user,
                        remarks=f"Session started by marking Step {step_number} complete"
                    )
                    
                    # Handle grouping - if this class is in an active group today, start them all
                    group_members = get_grouped_classes_for_session(class_section, timezone.localdate())
                    if len(group_members) > 1:
                        for other_cls in group_members:
                            if other_cls != class_section:
                                SessionStatusManager.conduct_session(
                                    planned_session=planned_session,
                                    class_section=other_cls,
                                    facilitator=request.user,
                                    remarks=f"Grouped session started by {class_section.display_name} action"
                                )
            
            # [GROUP SYNC] If this class is part of a group today, sync status to others
            from .session_management import get_grouped_classes_for_session
            
            group_members = get_grouped_classes_for_session(class_section, timezone.datetime.strptime(session_date, '%Y-%m-%d').date())
            
            if len(group_members) > 1:
                # Sync to other classes in the group
                for other_cls in group_members:
                    if other_cls != class_section:
                        SessionStepStatus.objects.update_or_create(
                            planned_session=planned_session,
                            class_section=other_cls,
                            session_date=session_date,
                            step_number=step_number,
                            defaults={
                                'is_completed': is_completed,
                                'step_content': step_content,
                                'facilitator': request.user,
                                'completed_at': step_status.completed_at,
                            }
                        )
                logger.info(f"Step {step_number} synced to {len(group_members) - 1} other sessions in group")
        
        # Find the actual session for this planned session today to return the ID for live UI updates
        actual_session = ActualSession.objects.filter(
            planned_session=planned_session,
            class_section=class_section,
            date=timezone.now().date()
        ).first()
        
        return JsonResponse({
            'success': True,
            'message': f'Step {step_number} status saved',
            'actual_session_id': str(actual_session.id) if actual_session else None,
            'step_status': {
                'id': str(step_status.id),
                'step_number': step_status.step_number,
                'is_completed': step_status.is_completed,
                'completed_at': step_status.completed_at.isoformat() if step_status.completed_at else None,
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving step status: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error saving step status: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_step_status(request):
    """
    Get the completion status of all steps for a session.
    
    Query parameters:
    - planned_session_id: UUID of the planned session
    - session_date: YYYY-MM-DD format
    - class_section_id: UUID of the class section
    
    Returns:
    {
        "success": true,
        "steps": {
            "1": {"is_completed": true, "completed_at": "..."},
            "2": {"is_completed": false, "completed_at": null},
            ...
        }
    }
    """
    try:
        planned_session_id = request.GET.get('planned_session_id')
        session_date = request.GET.get('session_date')
        class_section_id = request.GET.get('class_section_id')
        
        if not all([planned_session_id, session_date]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters: planned_session_id, session_date'
            }, status=400)
        
        # Get the planned session
        try:
            planned_session = PlannedSession.objects.get(id=planned_session_id)
        except PlannedSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Planned session {planned_session_id} not found'
            }, status=404)
        
        # Get all step statuses for this session, date and class section (or legacy null ones)
        q = Q(planned_session=planned_session, session_date=session_date)
        if class_section_id:
            q &= Q(Q(class_section_id=class_section_id) | Q(class_section__isnull=True))
        else:
            # Fallback: get first active class section for this facilitator
            class_section = ClassSection.objects.filter(
                school__facilitators__facilitator=request.user,
                school__facilitators__is_active=True
            ).first()
            if class_section:
                q &= Q(Q(class_section=class_section) | Q(class_section__isnull=True))
            
        step_statuses = SessionStepStatus.objects.filter(q).order_by('step_number')
        
        # Build response
        steps = {}
        for status in step_statuses:
            steps[str(status.step_number)] = {
                'is_completed': status.is_completed,
                'completed_at': status.completed_at.isoformat() if status.completed_at else None,
                'step_content': status.step_content,
            }
        
        # Add missing steps as incomplete
        for step_num in range(1, 8):
            if str(step_num) not in steps:
                steps[str(step_num)] = {
                    'is_completed': False,
                    'completed_at': None,
                    'step_content': {},
                }
        
        logger.info(
            f"Retrieved step statuses for session {planned_session_id} on {session_date} "
            f"by {request.user.email}"
        )
        
        return JsonResponse({
            'success': True,
            'planned_session_id': str(planned_session_id),
            'session_date': session_date,
            'steps': steps,
        })
    
    except Exception as e:
        logger.error(f"Error retrieving step status: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving step status: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def clear_step_status(request):
    """
    Clear (mark as incomplete) a specific step or all steps for a session.
    
    POST data:
    {
        "planned_session_id": "uuid",
        "session_date": "YYYY-MM-DD",
        "step_number": 1-7,  # Optional - if not provided, clears all steps
        "class_section_id": "uuid" # Optional
    }
    """
    try:
        data = json.loads(request.body)
        
        planned_session_id = data.get('planned_session_id')
        session_date = data.get('session_date')
        step_number = data.get('step_number')  # Optional
        class_section_id = data.get('class_section_id')
        
        if not all([planned_session_id, session_date]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: planned_session_id, session_date'
            }, status=400)
        
        # Get the planned session
        try:
            planned_session = PlannedSession.objects.get(id=planned_session_id)
        except PlannedSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Planned session {planned_session_id} not found'
            }, status=404)
            
        # Get class section
        class_section = None
        if class_section_id:
            try:
                class_section = ClassSection.objects.get(id=class_section_id)
            except ClassSection.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Class section {class_section_id} not found'
                }, status=404)
        else:
            class_section = ClassSection.objects.filter(
                school__facilitators__facilitator=request.user,
                school__facilitators__is_active=True
            ).first()
            
        if not class_section:
            return JsonResponse({
                'success': False,
                'error': 'No class section associated with this request'
            }, status=400)
        
        with transaction.atomic():
            if step_number:
                # Clear specific step
                if not (1 <= step_number <= 7):
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid step number. Must be between 1 and 7.'
                    }, status=400)
                
                step_status, _ = SessionStepStatus.objects.get_or_create(
                    planned_session=planned_session,
                    class_section=class_section,
                    session_date=session_date,
                    step_number=step_number,
                )
                step_status.mark_incomplete()
                
                # [GROUP SYNC] Clear for other group members
                from .session_management import get_grouped_classes_for_session
                group_members = get_grouped_classes_for_session(class_section, timezone.datetime.strptime(session_date, '%Y-%m-%d').date())
                
                if len(group_members) > 1:
                    other_classes = [c for c in group_members if c != class_section]
                    SessionStepStatus.objects.filter(
                        planned_session=planned_session,
                        class_section__in=other_classes,
                        session_date=session_date,
                        step_number=step_number
                    ).update(is_completed=False, completed_at=None)
                
                logger.info(
                    f"Cleared step {step_number} for session {planned_session_id} on {session_date} "
                    f"by {request.user.email} (Group synced)"
                )
            else:
                # Clear all steps
                SessionStepStatus.objects.filter(
                    planned_session=planned_session,
                    class_section=class_section,
                    session_date=session_date,
                ).update(is_completed=False, completed_at=None)
                
                # [GROUP SYNC] Clear all for other group members
                from .session_management import get_grouped_classes_for_session
                group_members = get_grouped_classes_for_session(class_section, timezone.datetime.strptime(session_date, '%Y-%m-%d').date())
                
                if len(group_members) > 1:
                    other_classes = [c for c in group_members if c != class_section]
                    SessionStepStatus.objects.filter(
                        planned_session=planned_session,
                        class_section__in=other_classes,
                        session_date=session_date
                    ).update(is_completed=False, completed_at=None)

                logger.info(
                    f"Cleared all steps for session {planned_session_id} on {session_date} "
                    f"by {request.user.email} (Group synced)"
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Step status cleared successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error clearing step status: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error clearing step status: {str(e)}'
        }, status=500)
