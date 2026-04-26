"""
Admin views for session sequence management
Handles bulk operations, template management, and sequence integrity
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Count
import json
import logging

from .models import (
    ClassSection, School, PlannedSession, ActualSession, 
    SessionBulkTemplate, User
)
from .session_management import (
    SessionBulkManager, SessionSequenceCalculator, ValidationResult
)

logger = logging.getLogger(__name__)


@login_required
def admin_session_templates_list(request):
    """
    Admin view to list and manage session templates
    """
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "Permission denied.")
        return redirect("no_permission")
    
    # Get all templates with usage statistics
    templates = SessionBulkTemplate.objects.all().order_by('-created_at')
    
    # Apply filters
    language_filter = request.GET.get('language', '')
    if language_filter:
        templates = templates.filter(language=language_filter)
    
    # Pagination
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'templates': page_obj,
        'language_filter': language_filter,
        'language_choices': SessionBulkTemplate._meta.get_field('language').choices,
    }
    
    return render(request, 'admin/sessions/templates_list.html', context)


@login_required
def admin_session_template_create(request):
    """
    Admin view to create a new session template
    """
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "Permission denied.")
        return redirect("no_permission")
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description')
            language = request.POST.get('language', 'english')
            total_days = int(request.POST.get('total_days', 150))
            
            # Create the template
            template = SessionBulkTemplate.objects.create(
                name=name,
                description=description,
                language=language,
                total_days=total_days,
                created_by=request.user,
                is_active=True
            )
            
            messages.success(request, f"Template '{name}' created successfully!")
            return redirect('admin_session_templates_list')
            
        except Exception as e:
            messages.error(request, f"Error creating template: {str(e)}")
    
    context = {
        'language_choices': SessionBulkTemplate._meta.get_field('language').choices,
    }
    
    return render(request, 'admin/sessions/template_form.html', context)


@login_required
def admin_bulk_generate_sessions(request):
    """
    Admin view for bulk session generation across multiple classes
    """
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "Permission denied.")
        return redirect("no_permission")
    
    if request.method == 'POST':
        try:
            class_ids = request.POST.getlist('class_ids')
            template_id = request.POST.get('template_id')
            
            if not class_ids:
                messages.error(request, "Please select at least one class.")
                return redirect(request.path)
            
            # Get template if specified
            template = None
            if template_id:
                template = get_object_or_404(SessionBulkTemplate, id=template_id)
            
            # Process each class
            results = {
                'success_count': 0,
                'error_count': 0,
                'total_sessions_created': 0,
                'errors': []
            }
            
            for class_id in class_ids:
                try:
                    class_section = get_object_or_404(ClassSection, id=class_id)
                    
                    result = SessionBulkManager.generate_sessions_for_class(
                        class_section=class_section,
                        template=template,
                        created_by=request.user
                    )
                    
                    if result['success']:
                        results['success_count'] += 1
                        results['total_sessions_created'] += result['created_count']
                    else:
                        results['error_count'] += 1
                        results['errors'].extend(result['errors'])
                        
                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append(f"Class {class_id}: {str(e)}")
            
            # Show results
            if results['success_count'] > 0:
                messages.success(request, 
                    f"Successfully generated sessions for {results['success_count']} classes "
                    f"({results['total_sessions_created']} total sessions)")
            
            if results['error_count'] > 0:
                messages.error(request, 
                    f"Failed to generate sessions for {results['error_count']} classes")
                for error in results['errors'][:5]:  # Show first 5 errors
                    messages.error(request, error)
            
            return redirect('admin_bulk_generate_sessions')
            
        except Exception as e:
            messages.error(request, f"Bulk generation error: {str(e)}")
    
    # Get classes without complete session sets
    classes_needing_sessions = []
    all_classes = ClassSection.objects.filter(is_active=True).select_related('school')
    
    for class_section in all_classes:
        session_count = PlannedSession.objects.filter(
            class_section=class_section,
            is_active=True
        ).count()
        
        if session_count < 150:
            classes_needing_sessions.append({
                'class_section': class_section,
                'current_sessions': session_count,
                'missing_sessions': 150 - session_count
            })
    
    # Get available templates
    templates = SessionBulkTemplate.objects.filter(is_active=True)
    
    context = {
        'classes_needing_sessions': classes_needing_sessions,
        'templates': templates,
    }
    
    return render(request, 'admin/sessions/bulk_generate.html', context)


@login_required
def admin_sequence_integrity_check(request):
    """
    Admin view to check and repair sequence integrity across all classes
    """
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "Permission denied.")
        return redirect("no_permission")
    
    if request.method == 'POST':
        action = request.POST.get('action')
        class_ids = request.POST.getlist('class_ids')
        
        if action == 'repair_gaps' and class_ids:
            repair_results = {
                'success_count': 0,
                'error_count': 0,
                'total_gaps_filled': 0,
                'errors': []
            }
            
            for class_id in class_ids:
                try:
                    class_section = get_object_or_404(ClassSection, id=class_id)
                    
                    result = SessionBulkManager.repair_sequence_gaps(
                        class_section=class_section,
                        created_by=request.user
                    )
                    
                    if result['success']:
                        repair_results['success_count'] += 1
                        repair_results['total_gaps_filled'] += result['created_count']
                    else:
                        repair_results['error_count'] += 1
                        repair_results['errors'].extend(result['errors'])
                        
                except Exception as e:
                    repair_results['error_count'] += 1
                    repair_results['errors'].append(f"Class {class_id}: {str(e)}")
            
            # Show results
            if repair_results['success_count'] > 0:
                messages.success(request, 
                    f"Repaired sequence gaps for {repair_results['success_count']} classes "
                    f"({repair_results['total_gaps_filled']} gaps filled)")
            
            if repair_results['error_count'] > 0:
                messages.error(request, 
                    f"Failed to repair {repair_results['error_count']} classes")
    
    # Check integrity for all classes
    integrity_results = []
    all_classes = ClassSection.objects.filter(is_active=True).select_related('school')
    
    for class_section in all_classes:
        validation_result = SessionSequenceCalculator.validate_sequence_integrity(class_section)
        progress_metrics = SessionSequenceCalculator.calculate_progress(class_section)
        
        integrity_results.append({
            'class_section': class_section,
            'validation_result': validation_result,
            'progress_metrics': progress_metrics,
            'has_issues': not validation_result.is_valid or len(validation_result.warnings) > 0
        })
    
    # Filter classes with issues
    classes_with_issues = [r for r in integrity_results if r['has_issues']]
    
    context = {
        'integrity_results': integrity_results,
        'classes_with_issues': classes_with_issues,
        'total_classes': len(integrity_results),
        'classes_with_issues_count': len(classes_with_issues),
    }
    
    return render(request, 'admin/sessions/integrity_check.html', context)


@login_required
def admin_session_analytics(request):
    """
    Admin view for session analytics and reporting
    """
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "Permission denied.")
        return redirect("no_permission")
    
    # Overall statistics
    total_classes = ClassSection.objects.filter(is_active=True).count()
    total_planned_sessions = PlannedSession.objects.filter(is_active=True).count()
    total_actual_sessions = ActualSession.objects.count()
    
    # Status breakdown
    status_breakdown = ActualSession.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Progress by school
    school_progress = []
    schools = School.objects.filter(status=1).prefetch_related('class_sections')
    
    for school in schools:
        school_classes = school.class_sections.filter(is_active=True)
        if school_classes.exists():
            total_sessions = 0
            conducted_sessions = 0
            
            for class_section in school_classes:
                metrics = SessionSequenceCalculator.calculate_progress(class_section)
                total_sessions += metrics.total_sessions
                conducted_sessions += metrics.conducted_sessions
            
            completion_rate = (conducted_sessions / total_sessions * 100) if total_sessions > 0 else 0
            
            school_progress.append({
                'school': school,
                'total_classes': school_classes.count(),
                'total_sessions': total_sessions,
                'conducted_sessions': conducted_sessions,
                'completion_rate': round(completion_rate, 1)
            })
    
    # Recent activity
    recent_sessions = ActualSession.objects.select_related(
        'planned_session__class_section__school', 'facilitator'
    ).order_by('-created_at')[:20]
    
    context = {
        'total_classes': total_classes,
        'total_planned_sessions': total_planned_sessions,
        'total_actual_sessions': total_actual_sessions,
        'status_breakdown': status_breakdown,
        'school_progress': school_progress,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'admin/sessions/analytics.html', context)


@login_required
def ajax_class_session_status(request):
    """
    AJAX endpoint to get session status for a specific class
    """
    if request.user.role.name.upper() != "ADMIN":
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'error': 'Class ID required'}, status=400)
    
    try:
        class_section = get_object_or_404(ClassSection, id=class_id)
        
        # Get validation result and progress metrics
        validation_result = SessionSequenceCalculator.validate_sequence_integrity(class_section)
        progress_metrics = SessionSequenceCalculator.calculate_progress(class_section)
        
        return JsonResponse({
            'success': True,
            'class_name': str(class_section),
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'progress': {
                'total_sessions': progress_metrics.total_sessions,
                'conducted_sessions': progress_metrics.conducted_sessions,
                'cancelled_sessions': progress_metrics.cancelled_sessions,
                'pending_sessions': progress_metrics.pending_sessions,
                'completion_percentage': progress_metrics.completion_percentage,
                'next_day_number': progress_metrics.next_day_number,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)