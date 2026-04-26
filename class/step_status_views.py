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
import json
import logging

from .models import PlannedSession, SessionStepStatus, ActualSession

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
        "step_content": {...}  # Optional JSON data
    }
    """
    try:
        data = json.loads(request.body)
        
        planned_session_id = data.get('planned_session_id')
        session_date = data.get('session_date')
        step_number = data.get('step_number')
        is_completed = data.get('is_completed', False)
        step_content = data.get('step_content', {})
        
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
        
        # Create or update the step status
        with transaction.atomic():
            step_status, created = SessionStepStatus.objects.update_or_create(
                planned_session=planned_session,
                session_date=session_date,
                step_number=step_number,
                defaults={
                    'is_completed': is_completed,
                    'step_content': step_content,
                    'facilitator': request.user,
                    'completed_at': timezone.now() if is_completed else None,
                }
            )
        
        logger.info(
            f"Step {step_number} status saved for session {planned_session_id} on {session_date} "
            f"(completed={is_completed}) by {request.user.email}"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Step {step_number} status saved',
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
        
        # Get all step statuses for this session and date
        step_statuses = SessionStepStatus.objects.filter(
            planned_session=planned_session,
            session_date=session_date
        ).order_by('step_number')
        
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
    }
    """
    try:
        data = json.loads(request.body)
        
        planned_session_id = data.get('planned_session_id')
        session_date = data.get('session_date')
        step_number = data.get('step_number')  # Optional
        
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
                    session_date=session_date,
                    step_number=step_number,
                )
                step_status.mark_incomplete()
                logger.info(
                    f"Cleared step {step_number} for session {planned_session_id} on {session_date} "
                    f"by {request.user.email}"
                )
            else:
                # Clear all steps
                SessionStepStatus.objects.filter(
                    planned_session=planned_session,
                    session_date=session_date,
                ).update(is_completed=False, completed_at=None)
                logger.info(
                    f"Cleared all steps for session {planned_session_id} on {session_date} "
                    f"by {request.user.email}"
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
