from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Count, Q
from .models import (
    ClassSection, Student, Enrollment, Subject, StudentPerformance,
    StudentPerformanceSummary, PerformanceCutoff
)
from .decorators import facilitator_required


@facilitator_required
def student_performance_list(request, class_section_id):
    """List all students with their performance summary"""
    class_section = get_object_or_404(ClassSection, id=class_section_id)
    
    # Verify facilitator access
    if not class_section.school.facilitators.filter(
        facilitator=request.user,
        is_active=True
    ).exists():
        messages.error(request, "You don't have access to this class")
        return redirect('facilitator_students_list')
    
    # Get all students in class
    students = Student.objects.filter(
        enrollments__class_section=class_section,
        enrollments__is_active=True
    ).distinct().order_by('full_name')
    
    # Get performance summaries
    performance_data = []
    for student in students:
        try:
            summary = StudentPerformanceSummary.objects.get(
                student=student,
                class_section=class_section
            )
        except StudentPerformanceSummary.DoesNotExist:
            summary = None
        
        performance_data.append({
            'student': student,
            'summary': summary,
        })
    
    # Get cutoff settings
    try:
        cutoff = class_section.performance_cutoff
    except:
        cutoff = None
    
    context = {
        'class_section': class_section,
        'performance_data': performance_data,
        'cutoff': cutoff,
    }
    
    return render(request, 'facilitator/performance/list.html', context)


@facilitator_required
def student_performance_detail(request, class_section_id, student_id):
    """View and edit student performance by subject"""
    class_section = get_object_or_404(ClassSection, id=class_section_id)
    student = get_object_or_404(Student, id=student_id)
    
    # Verify facilitator access
    if not class_section.school.facilitators.filter(
        facilitator=request.user,
        is_active=True
    ).exists():
        messages.error(request, "You don't have access to this class")
        return redirect('facilitator_students_list')
    
    # Verify student is in class
    if not Enrollment.objects.filter(
        student=student,
        class_section=class_section,
        is_active=True
    ).exists():
        messages.error(request, "Student is not in this class")
        return redirect('student_performance_list', class_section_id=class_section_id)
    
    # Get all subjects
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    
    # Get student's performance records
    performances = StudentPerformance.objects.filter(
        student=student,
        class_section=class_section
    ).select_related('subject')
    
    performance_dict = {p.subject_id: p for p in performances}
    
    # Get cutoff
    try:
        cutoff = class_section.performance_cutoff
    except:
        cutoff = None
    
    context = {
        'class_section': class_section,
        'student': student,
        'subjects': subjects,
        'performance_dict': performance_dict,
        'cutoff': cutoff,
    }
    
    return render(request, 'facilitator/performance/detail.html', context)


@facilitator_required
@require_http_methods(["POST"])
def student_performance_save(request, class_section_id, student_id):
    """Save student performance score"""
    class_section = get_object_or_404(ClassSection, id=class_section_id)
    student = get_object_or_404(Student, id=student_id)
    
    # Verify facilitator access
    if not class_section.school.facilitators.filter(
        facilitator=request.user,
        is_active=True
    ).exists():
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    subject_id = request.POST.get('subject_id')
    score = request.POST.get('score')
    remarks = request.POST.get('remarks', '')
    
    if not subject_id or score is None:
        return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
    
    try:
        score = int(score)
        if score < 0 or score > 100:
            return JsonResponse({'success': False, 'error': 'Score must be between 0 and 100'}, status=400)
    except:
        return JsonResponse({'success': False, 'error': 'Invalid score'}, status=400)
    
    try:
        subject = Subject.objects.get(id=subject_id)
    except:
        return JsonResponse({'success': False, 'error': 'Invalid subject'}, status=400)
    
    # Create or update performance record
    performance, created = StudentPerformance.objects.update_or_create(
        student=student,
        class_section=class_section,
        subject=subject,
        defaults={
            'score': score,
            'remarks': remarks,
            'recorded_by': request.user,
        }
    )
    
    # Update summary
    update_performance_summary(student, class_section)
    
    return JsonResponse({
        'success': True,
        'message': 'Performance saved successfully',
        'grade': performance.grade,
    })


@facilitator_required
def performance_cutoff_settings(request, class_section_id):
    """View and edit performance cutoff settings"""
    class_section = get_object_or_404(ClassSection, id=class_section_id)
    
    # Verify facilitator access
    if not class_section.school.facilitators.filter(
        facilitator=request.user,
        is_active=True
    ).exists():
        messages.error(request, "You don't have access to this class")
        return redirect('facilitator_students_list')
    
    try:
        cutoff = class_section.performance_cutoff
    except:
        cutoff = None
    
    if request.method == "POST":
        passing_score = request.POST.get('passing_score', 40)
        good_score = request.POST.get('good_score', 60)
        excellent_score = request.POST.get('excellent_score', 80)
        
        try:
            passing_score = int(passing_score)
            good_score = int(good_score)
            excellent_score = int(excellent_score)
            
            if not (0 <= passing_score <= 100 and 0 <= good_score <= 100 and 0 <= excellent_score <= 100):
                messages.error(request, "All scores must be between 0 and 100")
                return redirect('performance_cutoff_settings', class_section_id=class_section_id)
            
            if not (passing_score < good_score < excellent_score):
                messages.error(request, "Passing < Good < Excellent")
                return redirect('performance_cutoff_settings', class_section_id=class_section_id)
            
            if cutoff:
                cutoff.passing_score = passing_score
                cutoff.good_score = good_score
                cutoff.excellent_score = excellent_score
                cutoff.save()
            else:
                cutoff = PerformanceCutoff.objects.create(
                    class_section=class_section,
                    passing_score=passing_score,
                    good_score=good_score,
                    excellent_score=excellent_score,
                )
            
            # Recalculate all grades
            performances = StudentPerformance.objects.filter(class_section=class_section)
            for perf in performances:
                perf.save()  # This will recalculate grade
            
            messages.success(request, "Cutoff settings updated successfully")
            return redirect('student_performance_list', class_section_id=class_section_id)
        
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('performance_cutoff_settings', class_section_id=class_section_id)
    
    context = {
        'class_section': class_section,
        'cutoff': cutoff,
    }
    
    return render(request, 'facilitator/performance/cutoff_settings.html', context)


def update_performance_summary(student, class_section):
    """Update student performance summary"""
    performances = StudentPerformance.objects.filter(
        student=student,
        class_section=class_section
    )
    
    if not performances.exists():
        return
    
    total_subjects = performances.count()
    passed_subjects = performances.filter(grade__in=['A', 'B', 'C']).count()
    failed_subjects = performances.filter(grade='F').count()
    average_score = performances.aggregate(Avg('score'))['score__avg'] or 0
    is_passed = failed_subjects == 0
    
    summary, created = StudentPerformanceSummary.objects.update_or_create(
        student=student,
        class_section=class_section,
        defaults={
            'average_score': average_score,
            'total_subjects': total_subjects,
            'passed_subjects': passed_subjects,
            'failed_subjects': failed_subjects,
            'is_passed': is_passed,
        }
    )
    
    # Update rank
    update_class_rankings(class_section)


def update_class_rankings(class_section):
    """Update rankings for all students in class"""
    summaries = StudentPerformanceSummary.objects.filter(
        class_section=class_section
    ).order_by('-average_score', '-passed_subjects')
    
    for rank, summary in enumerate(summaries, 1):
        summary.rank = rank
        summary.save()
