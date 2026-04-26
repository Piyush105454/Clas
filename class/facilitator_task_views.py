from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import ActualSession, FacilitatorTask, CurriculumSession, CurriculumStatus, PlannedSession, SessionStatus
from .decorators import facilitator_required
import os
import logging

logger = logging.getLogger(__name__)


@facilitator_required
def facilitator_task_step(request, actual_session_id):
    """
    Facilitator task/preparation step
    Options: Take photo, Take video, Upload Facebook link
    Also displays lesson plan content for the session
    """
    from .models import CurriculumSession
    
    actual_session = get_object_or_404(ActualSession, id=actual_session_id)
    
    # Verify facilitator access
    if actual_session.planned_session.class_section.school.facilitators.filter(
        facilitator=request.user,
        is_active=True
    ).count() == 0:
        messages.error(request, "You don't have access to this session")
        return redirect('facilitator_today_session')
    
    # Get existing tasks
    existing_tasks = FacilitatorTask.objects.filter(
        actual_session=actual_session,
        facilitator=request.user
    )
    
    # Get lesson plan content from CurriculumSession
    planned_session = actual_session.planned_session
    curriculum_session = None
    
    try:
        # Try to find matching CurriculumSession by day_number
        # Assuming curriculum is language-specific, try to match by day
        curriculum_session = CurriculumSession.objects.filter(
            day_number=planned_session.day_number,
            status=CurriculumStatus.PUBLISHED
        ).first()
    except Exception as e:
        logger.warning(f"Error loading curriculum session: {str(e)}")
    
    # Check if this is a grouped session
    is_grouped_session = planned_session.grouped_session_id is not None
    grouped_classes = []
    
    if is_grouped_session:
        # Get all classes in the group
        grouped_sessions = PlannedSession.objects.filter(
            grouped_session_id=planned_session.grouped_session_id,
            day_number=planned_session.day_number
        ).select_related('class_section')
        grouped_classes = [gs.class_section for gs in grouped_sessions]
    
    context = {
        'actual_session': actual_session,
        'planned_session': planned_session,
        'existing_tasks': existing_tasks,
        'curriculum_session': curriculum_session,
        'is_grouped_session': is_grouped_session,
        'grouped_classes': grouped_classes,
        'task_count': existing_tasks.count(),
    }
    
    return render(request, 'facilitator/facilitator_task.html', context)


@facilitator_required
@require_http_methods(["POST"])
def facilitator_task_upload_photo(request, actual_session_id=None):
    """
    Upload photo for facilitator task
    actual_session_id is optional - if not provided, task is created without session link
    """
    try:
        actual_session = None
        if actual_session_id:
            actual_session = get_object_or_404(ActualSession, id=actual_session_id)
        
        if 'photo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No photo provided'}, status=400)
        
        photo = request.FILES['photo']
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = os.path.splitext(photo.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'success': False, 'error': 'Invalid file type. Use JPG, PNG, or GIF'}, status=400)
        
        # Create task
        task = FacilitatorTask.objects.create(
            actual_session=actual_session,
            facilitator=request.user,
            media_type='photo',
            media_file=photo,
            description=request.POST.get('description', '')
        )
        
        return JsonResponse({
            'success': True,
            'task_id': str(task.id),
            'message': 'Photo uploaded successfully'
        })
    except Exception as e:
        logger.error(f"Error uploading photo: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@facilitator_required
@require_http_methods(["POST"])
def facilitator_task_upload_video(request, actual_session_id=None):
    """
    Upload video for facilitator task
    actual_session_id is optional - if not provided, task is created without session link
    """
    try:
        actual_session = None
        if actual_session_id:
            actual_session = get_object_or_404(ActualSession, id=actual_session_id)
        
        if 'video' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No video provided'}, status=400)
        
        video = request.FILES['video']
        
        # Validate file type
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        ext = os.path.splitext(video.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'success': False, 'error': 'Invalid file type. Use MP4, AVI, MOV, MKV, or WebM'}, status=400)
        
        # Create task
        task = FacilitatorTask.objects.create(
            actual_session=actual_session,
            facilitator=request.user,
            media_type='video',
            media_file=video,
            description=request.POST.get('description', '')
        )
        
        return JsonResponse({
            'success': True,
            'task_id': str(task.id),
            'message': 'Video uploaded successfully'
        })
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@facilitator_required
@require_http_methods(["GET"])
def facilitator_task_facebook_links(request):
    """
    Get saved Facebook links for the current session only
    OPTIMIZED: Uses database query caching and filters by session
    """
    try:
        # Get the actual_session_id from query parameters
        actual_session_id = request.GET.get('actual_session_id')
        
        if not actual_session_id:
            return JsonResponse({
                'success': False,
                'error': 'actual_session_id is required',
                'links': []
            }, status=400)
        
        # Use select_related to avoid N+1 queries
        # Filter by both facilitator AND actual_session to get only current session links
        links = FacilitatorTask.objects.filter(
            facilitator=request.user,
            actual_session_id=actual_session_id,
            media_type='facebook_link'
        ).values('id', 'facebook_link', 'created_at').order_by('-created_at')[:10]
        
        links_list = []
        for link in links:
            links_list.append({
                'id': str(link['id']),
                'facebook_link': link['facebook_link'],
                'created_at': link['created_at'].strftime('%Y-%m-%d %H:%M:%S') if link['created_at'] else 'N/A'
            })
        
        return JsonResponse({
            'success': True,
            'links': links_list,
            'count': len(links_list)
        })
    except Exception as e:
        logger.error(f"Error fetching Facebook links: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@facilitator_required
@require_http_methods(["POST"])
def facilitator_task_facebook_link(request, actual_session_id=None):
    """
    Add Facebook link for facilitator task
    actual_session_id can be provided as URL parameter or POST data
    """
    try:
        # Get actual_session_id from URL parameter or POST data
        if not actual_session_id:
            actual_session_id = request.POST.get('actual_session_id')
        
        actual_session = None
        if actual_session_id:
            actual_session = get_object_or_404(ActualSession, id=actual_session_id)
        
        facebook_link = request.POST.get('facebook_link', '').strip()
        
        if not facebook_link:
            return JsonResponse({'success': False, 'error': 'Facebook link is required'}, status=400)
        
        # Validate Facebook URL
        if 'facebook.com' not in facebook_link and 'fb.watch' not in facebook_link:
            return JsonResponse({'success': False, 'error': 'Invalid Facebook link'}, status=400)
        
        # Create task with current timestamp
        task = FacilitatorTask.objects.create(
            actual_session=actual_session,
            facilitator=request.user,
            media_type='facebook_link',
            facebook_link=facebook_link,
            description=request.POST.get('description', ''),
            created_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'task_id': str(task.id),
            'message': 'Facebook link added successfully',
            'timestamp': task.created_at.isoformat()
        })
    except Exception as e:
        logger.error(f"Error adding Facebook link: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@facilitator_required
@require_http_methods(["POST"])
def facilitator_task_delete(request, task_id):
    """
    Delete facilitator task
    """
    task = get_object_or_404(FacilitatorTask, id=task_id, facilitator=request.user)
    actual_session_id = task.actual_session.id
    task.delete()
    
    return JsonResponse({'success': True, 'message': 'Task deleted successfully'})


@facilitator_required
def facilitator_task_complete(request, actual_session_id):
    """
    Mark facilitator task step as complete and move to next step
    Note: Session status remains PENDING until feedback is saved
    """
    actual_session = get_object_or_404(ActualSession, id=actual_session_id)
    
    # Check if at least one task exists
    task_count = FacilitatorTask.objects.filter(
        actual_session=actual_session,
        facilitator=request.user
    ).count()
    
    if task_count == 0:
        messages.warning(request, "Please add at least one task before proceeding")
        return redirect('facilitator_task_step', actual_session_id=actual_session_id)
    
    # Session status remains PENDING - it will be marked CONDUCTED when feedback is saved
    messages.success(request, "Facilitator task completed. Continue to feedback step.")
    # Redirect to feedback step instead of marking attendance
    return redirect('facilitator_class_today_session', class_section_id=actual_session.planned_session.class_section.id)
