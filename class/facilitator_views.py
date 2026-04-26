"""
Facilitator Student Management Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from .models import (
    School, ClassSection, Student, Enrollment, FacilitatorSchool, User, 
    SessionStatus, AttendanceStatus, DateType, ActualSession, Attendance, 
    PlannedSession, CalendarDate
)
from .session_management import (
    SessionSequenceCalculator, 
    SessionStatusManager, 
    get_grouped_classes_for_session
)
from .mixins import FacilitatorAccessMixin
from .decorators import facilitator_required
from .forms import AddUserForm  # We'll need to create a student form
from .student_performance_views import (
    student_performance_list, student_performance_detail, 
    student_performance_save, performance_cutoff_settings
)
import logging
from datetime import date
import csv
import openpyxl
import re
logger = logging.getLogger(__name__)


class FacilitatorSchoolListView(FacilitatorAccessMixin, ListView):
    """
    View for facilitators to see their assigned schools
    """
    model = School
    template_name = 'facilitator/schools/list.html'
    context_object_name = 'schools'
    
    def get_queryset(self):
        """Return only schools assigned to the current facilitator, ordered alphabetically"""
        return self.get_facilitator_schools().order_by('name')
    
    def get_context_data(self, **kwargs):
        from django.db.models import Count
        
        context = super().get_context_data(**kwargs)
        
        school_ids = [s.id for s in context['schools']]
        
        # OPTIMIZATION: Single batch query for both counts
        enrollment_counts = Enrollment.objects.filter(
            school_id__in=school_ids,
            is_active=True
        ).values('school_id').annotate(count=Count('id'))
        enrollment_by_school = {item['school_id']: item['count'] for item in enrollment_counts}
        
        class_counts = ClassSection.objects.filter(
            school_id__in=school_ids,
            is_active=True
        ).values('school_id').annotate(count=Count('id'))
        class_by_school = {item['school_id']: item['count'] for item in class_counts}
        
        schools_with_counts = [
            {
                'school': school,
                'enrollment_count': enrollment_by_school.get(school.id, 0),
                'class_count': class_by_school.get(school.id, 0)
            }
            for school in context['schools']
        ]
        
        context['schools_with_counts'] = schools_with_counts
        return context


class FacilitatorSchoolDetailView(FacilitatorAccessMixin, DetailView):
    """
    View for facilitators to see classes within their assigned school
    """
    model = School
    template_name = 'facilitator/schools/detail.html'
    context_object_name = 'school'
    
    def get_object(self, queryset=None):
        """Get school and verify facilitator has access"""
        school = super().get_object(queryset)
        self.verify_school_access_or_403(school.id)
        return school
    
    def get_context_data(self, **kwargs):
        from django.db.models import Count
        
        context = super().get_context_data(**kwargs)
        school = self.object
        
        classes = ClassSection.objects.filter(
            school=school,
            is_active=True
        ).order_by('class_level', 'section')
        
        class_ids = [c.id for c in classes]
        
        # OPTIMIZATION: Single batch query for enrollment counts
        enrollment_counts = Enrollment.objects.filter(
            class_section_id__in=class_ids,
            is_active=True
        ).values('class_section_id').annotate(count=Count('id'))
        enrollment_by_class = {item['class_section_id']: item['count'] for item in enrollment_counts}
        
        classes_with_counts = [
            {
                'class_section': cls,
                'enrollment_count': enrollment_by_class.get(cls.id, 0)
            }
            for cls in classes
        ]
        
        context['classes_with_counts'] = classes_with_counts
        
        grade_levels = classes.values_list('class_level', flat=True).distinct()
        context['grade_levels'] = sorted(set(grade_levels))
        
        grade_filter = self.request.GET.get('grade')
        if grade_filter:
            classes_with_counts = [
                item for item in classes_with_counts 
                if item['class_section'].class_level == grade_filter
            ]
            context['selected_grade'] = grade_filter
        
        context['filtered_classes'] = classes_with_counts
        return context


class FacilitatorStudentListView(FacilitatorAccessMixin, ListView):
    """
    View for facilitators to see students from their assigned schools
    """
    model = Enrollment
    template_name = 'facilitator/students/list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        """Return students from facilitator's assigned schools"""
        queryset = Enrollment.objects.filter(
            is_active=True,
            school__in=self.get_facilitator_schools()
        ).select_related('student', 'class_section', 'school')
        
        # Apply filters
        school_filter = self.request.GET.get('school')
        class_filter = self.request.GET.get('class')
        grade_filter = self.request.GET.get('grade')
        search_query = self.request.GET.get('search')
        
        if school_filter:
            queryset = queryset.filter(school_id=school_filter)
        
        if class_filter:
            queryset = queryset.filter(class_section_id=class_filter)
        
        if grade_filter:
            queryset = queryset.filter(class_section__class_level=grade_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(student__full_name__icontains=search_query) |
                Q(student__enrollment_number__icontains=search_query)
            )
        
        # Default sort by name
        queryset = queryset.order_by('student__full_name')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        from django.db.models import Count, Q, Prefetch
        from .models import Attendance, ActualSession
        
        context = super().get_context_data(**kwargs)
        
        # Get sort option
        sort_option = self.request.GET.get('sort', '')
        
        # Apply sorting to the paginated enrollments
        enrollments = list(context['enrollments'])
        
        if sort_option == 'name_asc':
            enrollments.sort(key=lambda x: x.student.full_name.lower())
        elif sort_option == 'name_desc':
            enrollments.sort(key=lambda x: x.student.full_name.lower(), reverse=True)
        elif sort_option == 'enrollment_asc':
            enrollments.sort(key=lambda x: self._natural_sort_key(x.student.enrollment_number))
        elif sort_option == 'enrollment_desc':
            enrollments.sort(key=lambda x: self._natural_sort_key(x.student.enrollment_number), reverse=True)
        
        context['enrollments'] = enrollments
        
        context['schools'] = self.get_facilitator_schools()
        context['classes'] = self.get_assigned_class_sections()
        
        grade_levels = ClassSection.objects.filter(
            school__in=self.get_facilitator_schools()
        ).values_list('class_level', flat=True).distinct()
        context['grade_levels'] = sorted(set(grade_levels))
        
        context['filters'] = {
            'school': self.request.GET.get('school', ''),
            'class': self.request.GET.get('class', ''),
            'grade': self.request.GET.get('grade', ''),
            'search': self.request.GET.get('search', ''),
            'sort': sort_option,
        }
        
        # OPTIMIZATION: Get all data in batch queries
        enrollment_ids = [e.id for e in enrollments]
        class_ids = [c.id for c in context['classes']]
        
        # Single query for all class session counts
        # ✅ Group Mapping (For Single Set of 150 Architecture)
        # Map each class to its primary class if it's part of a group
        from .models import GroupedSession, PlannedSession
        class_to_primary = {c_id: c_id for c_id in class_ids}
        group_infos = GroupedSession.objects.filter(class_sections__id__in=class_ids).prefetch_related('class_sections')
        
        all_relevant_class_ids = set(class_ids)
        for g in group_infos:
            # Find the primary class for this group (the one with PlannedSessions)
            primary_ps = PlannedSession.objects.filter(grouped_session_id=g.grouped_session_id).first()
            if primary_ps:
                primary_id = primary_ps.class_section_id
                all_relevant_class_ids.add(primary_id)
                for c in g.class_sections.all():
                    if c.id in class_ids:
                        class_to_primary[c.id] = primary_id

        class_session_counts = ActualSession.objects.filter(
            planned_session__class_section_id__in=list(all_relevant_class_ids),
            status=SessionStatus.CONDUCTED
        ).values('planned_session__class_section_id').annotate(count=Count('id'))
        
        # Build the final dict, mapping secondary classes to primary counts
        primary_session_dict = {
            item['planned_session__class_section_id']: item['count'] 
            for item in class_session_counts
        }
        
        class_session_dict = {
            c_id: primary_session_dict.get(class_to_primary[c_id], 0)
            for c_id in class_ids
        }
        
        # Single query for all attendance stats
        attendance_stats_raw = Attendance.objects.filter(
            enrollment_id__in=enrollment_ids
        ).values('enrollment_id').annotate(
            present_count=Count('id', filter=Q(status=AttendanceStatus.PRESENT)),
            absent_count=Count('id', filter=Q(status=AttendanceStatus.ABSENT))
        )
        
        attendance_by_enrollment = {
            stat['enrollment_id']: {
                'present': stat['present_count'],
                'absent': stat['absent_count']
            }
            for stat in attendance_stats_raw
        }
        
        # Build stats from batch queries
        enrollment_stats = []
        for enrollment in enrollments:
            total_sessions = class_session_dict.get(enrollment.class_section_id, 0)
            attendance_data = attendance_by_enrollment.get(enrollment.id, {'present': 0, 'absent': 0})
            
            present_count = attendance_data['present']
            absent_count = attendance_data['absent']
            attendance_percentage = (present_count / total_sessions * 100) if total_sessions > 0 else 0
            
            enrollment_stats.append({
                'enrollment': enrollment,
                'total_sessions': total_sessions,
                'present_count': present_count,
                'absent_count': absent_count,
                'attendance_percentage': round(attendance_percentage, 1)
            })
        
        context['enrollment_stats'] = enrollment_stats
        return context
    
    def _natural_sort_key(self, text):
        """
        Convert a string into a list of mixed integers and strings for natural sorting.
        Example: "A123B45" -> ['a', 123, 'b', 45]
        This handles mixed alphanumeric enrollment numbers correctly.
        """
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        return [convert(c) for c in re.split('([0-9]+)', str(text))]


class FacilitatorStudentCreateView(FacilitatorAccessMixin, CreateView):
    """
    View for facilitators to create new students
    """
    model = Student
    template_name = 'facilitator/students/create.html'
    fields = ['enrollment_number', 'full_name', 'gender']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Only show classes from facilitator's assigned schools
        context['class_sections'] = self.get_assigned_class_sections()
        context['schools'] = self.get_facilitator_schools()
        
        return context
    
    def form_valid(self, form):
        """Create student and enrollment"""
        # Get the selected class section
        class_section_id = self.request.POST.get('class_section')
        if not class_section_id:
            messages.error(self.request, "Please select a class section.")
            return self.form_invalid(form)
        
        # Verify facilitator has access to this class
        self.verify_class_access_or_403(class_section_id)
        
        class_section = get_object_or_404(ClassSection, id=class_section_id)
        
        # Save the student
        student = form.save()
        
        # Create enrollment with start_date
        Enrollment.objects.create(
            student=student,
            school=class_section.school,
            class_section=class_section,
            start_date=date.today(),  # Add current date as start_date
            is_active=True
        )
        
        messages.success(self.request, f"Student {student.full_name} created successfully!")
        return redirect('facilitator_students_list')


class FacilitatorStudentUpdateView(FacilitatorAccessMixin, UpdateView):
    """
    View for facilitators to edit existing students
    """
    model = Student
    template_name = 'facilitator/students/edit.html'
    fields = ['enrollment_number', 'full_name', 'gender']
    
    def get_object(self, queryset=None):
        """Get student and verify facilitator has access"""
        student = super().get_object(queryset)
        
        # Check if student is enrolled in any of facilitator's schools
        enrollment = Enrollment.objects.filter(
            student=student,
            is_active=True,
            school__in=self.get_facilitator_schools()
        ).first()
        
        if not enrollment:
            raise PermissionDenied("You do not have access to this student.")
        
        return student
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current enrollment
        student = self.object
        current_enrollment = Enrollment.objects.filter(
            student=student,
            is_active=True,
            school__in=self.get_facilitator_schools()
        ).first()
        
        context['current_enrollment'] = current_enrollment
        context['class_sections'] = self.get_assigned_class_sections()
        context['schools'] = self.get_facilitator_schools()
        
        return context
    
    def form_valid(self, form):
        """Update student and enrollment if class changed"""
        student = form.save()
        
        # Check if class section was changed
        new_class_section_id = self.request.POST.get('class_section')
        if new_class_section_id:
            # Verify facilitator has access to new class
            self.verify_class_access_or_403(new_class_section_id)
            
            new_class_section = get_object_or_404(ClassSection, id=new_class_section_id)
            
            # Update enrollment
            current_enrollment = Enrollment.objects.filter(
                student=student,
                is_active=True,
                school__in=self.get_facilitator_schools()
            ).first()
            
            if current_enrollment:
                current_enrollment.class_section = new_class_section
                current_enrollment.school = new_class_section.school
                current_enrollment.save()
        
        messages.success(self.request, f"Student {student.full_name} updated successfully!")
        return redirect('facilitator_students_list')


# Function-based views for AJAX endpoints
@facilitator_required
def facilitator_ajax_school_classes(request):
    """AJAX endpoint to get classes for a specific school - Simplified version"""
    school_id = request.GET.get('school_id')
    
    if not school_id:
        return JsonResponse({'error': 'School ID required'}, status=400)
    
    try:
        # Check if facilitator has access to this school
        facilitator_schools = FacilitatorSchool.objects.filter(
            facilitator=request.user,
            school_id=school_id,
            is_active=True
        ).exists()
        
        if not facilitator_schools:
            return JsonResponse({'error': 'Access denied - School not assigned to facilitator'}, status=403)
        
        # Get classes for the school
        classes = ClassSection.objects.filter(
            school_id=school_id,
            is_active=True
        ).order_by('class_level', 'section')
        
        # Convert to simple list
        classes_data = []
        for cls in classes:
            classes_data.append({
                'id': str(cls.id),
                'class_level': cls.class_level,
                'section': cls.section or '',
                'display_name': cls.display_name or f"{cls.class_level}{cls.section or ''}"
            })
        
        return JsonResponse({
            'success': True,
            'classes': classes_data,
            'count': len(classes_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@facilitator_required
def facilitator_student_detail(request, student_id):
    """View student details and attendance - OPTIMIZED with lazy loading"""
    from .models import Attendance, ActualSession, StudentGrowthAnalysis, StudentQuiz
    
    student = get_object_or_404(Student, id=student_id)
    
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    
    enrollment = Enrollment.objects.filter(
        student=student,
        is_active=True,
        school__in=mixin.get_facilitator_schools()
    ).first()
    
    if not enrollment:
        messages.error(request, "You do not have access to this student.")
        return redirect('facilitator_students_list')
    
    # OPTIMIZATION: Single aggregation query for attendance stats
    attendance_stats = Attendance.objects.filter(
        enrollment=enrollment
    ).aggregate(
        total_sessions=Count('id', filter=Q(status__in=[AttendanceStatus.PRESENT, AttendanceStatus.ABSENT])),
        present_count=Count('id', filter=Q(status=AttendanceStatus.PRESENT)),
        absent_count=Count('id', filter=Q(status=AttendanceStatus.ABSENT))
    )
    
    total_sessions = attendance_stats['total_sessions']
    present_count = attendance_stats['present_count']
    absent_count = attendance_stats['absent_count']
    attendance_percentage = (present_count / total_sessions * 100) if total_sessions > 0 else 0
    
    # Get recent attendance records with select_related
    recent_attendance = Attendance.objects.filter(
        enrollment=enrollment
    ).select_related('actual_session__planned_session').order_by('-actual_session__date')[:10]
    
    # Get quiz history (last 6 months)
    quiz_history = StudentQuiz.objects.filter(
        enrollment=enrollment
    ).order_by('-quiz_date')[:12]
    
    # NOTE: Growth analysis is now loaded asynchronously via AJAX
    # This allows the page to render immediately without waiting for ML computations
    
    context = {
        'student': student,
        'enrollment': enrollment,
        'stats': {
            'total_sessions': total_sessions,
            'present_count': present_count,
            'absent_count': absent_count,
            'attendance_percentage': round(attendance_percentage, 1)
        },
        'attendance_records': recent_attendance,
        'growth_analysis': None,  # Will be loaded via AJAX
        'quiz_history': quiz_history,
    }
    
    return render(request, 'facilitator/students/detail.html', context)


@facilitator_required
def facilitator_student_growth_analysis_ajax(request, student_id):
    """
    AJAX endpoint for lazy-loading student growth analysis.
    This runs asynchronously so the page loads immediately.
    
    Returns JSON with growth analysis data.
    """
    from .models import StudentGrowthAnalysis
    from .services.student_growth_service import StudentGrowthAnalysisService
    import json
    
    try:
        student = get_object_or_404(Student, id=student_id)
        
        mixin = FacilitatorAccessMixin()
        mixin.request = request
        
        enrollment = Enrollment.objects.filter(
            student=student,
            is_active=True,
            school__in=mixin.get_facilitator_schools()
        ).first()
        
        if not enrollment:
            return JsonResponse({
                'success': False,
                'error': 'You do not have access to this student.'
            }, status=403)
        
        # Perform growth analysis (this is the heavy computation)
        analysis = StudentGrowthAnalysisService.update_growth_analysis(enrollment)
        
        if not analysis:
            return JsonResponse({
                'success': False,
                'error': 'Unable to generate growth analysis. Please try again later.'
            }, status=500)
        
        # Prepare response data
        growth_score = round(analysis.growth_score, 1)
        stroke_dasharray = round(growth_score * 3.39, 2)
        
        growth_data = {
            'success': True,
            'growth_score': growth_score,
            'growth_score_stroke': stroke_dasharray,
            'risk_level': analysis.get_risk_level_display(),
            'cluster': analysis.get_student_cluster_display(),
            'engagement_level': analysis.get_engagement_level_display(),
            'attendance_consistency': round(analysis.attendance_consistency, 1),
            'quiz_improvement_rate': round(analysis.quiz_improvement_rate, 2),
            'text_complexity_growth': round(analysis.text_complexity_growth, 1),
            'cluster_confidence': round(analysis.cluster_confidence * 100, 1),
            'insights': analysis.growth_insights,
            'recommendations': analysis.recommendations,
            'at_risk_flags': analysis.at_risk_flags,
            'is_sufficient_data': analysis.is_sufficient_data,
            'analysis_date': analysis.analysis_date.isoformat() if analysis.analysis_date else None,
        }
        
        return JsonResponse(growth_data)
    
    except Exception as e:
        logger.error(f"Error in facilitator_student_growth_analysis_ajax: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while generating growth analysis.'
        }, status=500)


@facilitator_required
def facilitator_debug_schools(request):
    """Debug view to check facilitator school access"""
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    
    schools = mixin.get_facilitator_schools()
    school_data = []
    
    for school in schools:
        classes = ClassSection.objects.filter(school=school, is_active=True)
        school_data.append({
            'school': school,
            'classes': classes,
            'class_count': classes.count()
        })
    
    return JsonResponse({
        'facilitator_id': str(request.user.id),
        'facilitator_name': request.user.full_name,
        'schools_count': schools.count(),
        'schools': [
            {
                'id': str(item['school'].id),
                'name': item['school'].name,
                'class_count': item['class_count'],
                'classes': [
                    {
                        'id': str(cls.id),
                        'display_name': cls.display_name,
                        'class_level': cls.class_level,
                        'section': cls.section
                    } for cls in item['classes']
                ]
            } for item in school_data
        ]
    })

@facilitator_required
def facilitator_test_access(request):
    """Test view to check facilitator access and data"""
    from django.http import HttpResponse
    
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    
    # Get facilitator schools
    schools = mixin.get_facilitator_schools()
    
    html = f"""
    <html>
    <head><title>Facilitator Access Test</title></head>
    <body>
        <h1>Facilitator Access Test</h1>
        <p><strong>User:</strong> {request.user.full_name} (ID: {request.user.id})</p>
        <p><strong>Role:</strong> {request.user.role.name}</p>
        <p><strong>Schools Assigned:</strong> {schools.count()}</p>
        
        <h2>Schools and Classes:</h2>
    """
    
    if schools.count() == 0:
        html += "<p style='color: red;'>No schools assigned to this facilitator!</p>"
        html += "<p>Please contact admin to assign schools to this facilitator.</p>"
    else:
        for school in schools:
            classes = ClassSection.objects.filter(school=school, is_active=True)
            html += f"""
            <div style='border: 1px solid #ccc; margin: 10px; padding: 10px;'>
                <h3>{school.name} (ID: {school.id})</h3>
                <p>Classes: {classes.count()}</p>
                <ul>
            """
            
            for cls in classes:
                html += f"<li>{cls.display_name} (ID: {cls.id})</li>"
            
            html += "</ul></div>"
    
    html += """
        <h2>Test AJAX Endpoint:</h2>
        <p>Select a school to test the AJAX endpoint:</p>
        <select id="schoolSelect" onchange="testAjax()">
            <option value="">Select School</option>
    """
    
    for school in schools:
        html += f'<option value="{school.id}">{school.name}</option>'
    
    html += """
        </select>
        <div id="result" style="margin-top: 20px; padding: 10px; border: 1px solid #ddd;"></div>
        
        <script>
        function testAjax() {
            const schoolId = document.getElementById('schoolSelect').value;
            const resultDiv = document.getElementById('result');
            
            if (!schoolId) {
                resultDiv.innerHTML = '';
                return;
            }
            
            resultDiv.innerHTML = 'Loading...';
            
            fetch('/facilitator/ajax/school-classes/?school_id=' + schoolId)
                .then(response => response.json())
                .then(data => {
                    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                })
                .catch(error => {
                    resultDiv.innerHTML = '<p style="color: red;">Error: ' + error + '</p>';
                });
        }
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html)

@facilitator_required
def facilitator_dashboard(request):
    """Enhanced facilitator dashboard with real data and analytics - OPTIMIZED with caching"""
    from django.db.models import Count, Q, F, Case, When, IntegerField
    from django.core.cache import cache
    from .models import Attendance, ActualSession, PlannedSession
    from datetime import datetime, timedelta
    
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    
    # OPTIMIZATION: Cache facilitator data for 5 minutes - MUST include user ID in cache key
    cache_key = f"facilitator_dashboard_{request.user.id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return render(request, 'facilitator/dashboard.html', cached_data)
    
    facilitator_schools = mixin.get_facilitator_schools()
    facilitator_classes = mixin.get_facilitator_classes()
    
    school_ids = list(facilitator_schools.values_list('id', flat=True))
    class_ids = list(facilitator_classes.values_list('id', flat=True))
    
    # OPTIMIZATION: Single aggregation query instead of multiple queries
    stats = PlannedSession.objects.filter(
        class_section_id__in=class_ids,
        is_active=True
    ).aggregate(
        total_planned=Count('id'),
        conducted=Count('id', filter=Q(actual_sessions__status=SessionStatus.CONDUCTED))
    )
    
    # OPTIMIZATION: Batch attendance stats in one query
    attendance_stats = Attendance.objects.filter(
        enrollment__school_id__in=school_ids
    ).aggregate(
        total_records=Count('id'),
        present_count=Count('id', filter=Q(status=AttendanceStatus.PRESENT))
    )
    
    total_planned_sessions = stats['total_planned']
    conducted_sessions = stats['conducted']
    total_attendance_records = attendance_stats['total_records']
    present_count = attendance_stats['present_count']
    
    session_completion_rate = (conducted_sessions / total_planned_sessions * 100) if total_planned_sessions > 0 else 0
    overall_attendance_rate = (present_count / total_attendance_records * 100) if total_attendance_records > 0 else 0
    
    # OPTIMIZATION: Get all class stats in one query with aggregation
    last_week = datetime.now().date() - timedelta(days=7)
    
    class_stats_raw = Attendance.objects.filter(
        enrollment__class_section_id__in=class_ids
    ).values('enrollment__class_section_id').annotate(
        total_attendance=Count('id'),
        present_attendance=Count('id', filter=Q(status=AttendanceStatus.PRESENT))
    )
    
    class_stats_dict = {
        stat['enrollment__class_section_id']: {
            'total': stat['total_attendance'],
            'present': stat['present_attendance']
        }
        for stat in class_stats_raw
    }
    
    # OPTIMIZATION: Get student counts per class in one query
    student_counts = Enrollment.objects.filter(
        class_section_id__in=class_ids,
        is_active=True
    ).values('class_section_id').annotate(count=Count('id'))
    
    student_counts_dict = {item['class_section_id']: item['count'] for item in student_counts}
    
    # OPTIMIZATION: Paginate classes (show only first 10)
    from django.core.paginator import Paginator
    paginator = Paginator(facilitator_classes, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Build class stats from aggregated data
    class_attendance_stats = []
    for class_section in page_obj.object_list:
        stats_data = class_stats_dict.get(class_section.id, {'total': 0, 'present': 0})
        attendance_rate = (stats_data['present'] / stats_data['total'] * 100) if stats_data['total'] > 0 else 0
        
        class_attendance_stats.append({
            'class_section': class_section,
            'attendance_rate': round(attendance_rate, 1),
            'total_students': student_counts_dict.get(class_section.id, 0)
        })
    
    # OPTIMIZATION: Prefetch related data to avoid N+1
    recent_students = Enrollment.objects.filter(
        school_id__in=school_ids,
        is_active=True
    ).select_related('student', 'class_section').order_by('-student__created_at')[:5]
    
    recent_sessions = ActualSession.objects.filter(
        planned_session__class_section__in=facilitator_classes,
        date__gte=last_week
    ).count()
    
    upcoming_sessions = PlannedSession.objects.filter(
        class_section__in=facilitator_classes,
        is_active=True
    ).exclude(
        actual_sessions__status=SessionStatus.CONDUCTED
    ).order_by('day_number')[:5]
    
    context = {
        'total_schools': len(school_ids),
        'total_classes': len(class_ids),
        'total_students': Enrollment.objects.filter(school_id__in=school_ids, is_active=True).count(),
        'total_planned_sessions': total_planned_sessions,
        'conducted_sessions': conducted_sessions,
        'session_completion_rate': round(session_completion_rate, 1),
        'overall_attendance_rate': round(overall_attendance_rate, 1),
        'recent_sessions': recent_sessions,
        'recent_students': recent_students,
        'upcoming_sessions': upcoming_sessions,
        'class_attendance_stats': class_attendance_stats,
        'facilitator_schools': facilitator_schools,
        'facilitator_name': request.user.full_name,
        'facilitator_email': request.user.email,
    }
    
    return render(request, 'facilitator/dashboard.html', context)



# =====================================================
# TODAY'S SESSION WITH CALENDAR INTEGRATION
# =====================================================

@facilitator_required
def facilitator_today_session(request):
    """
    Redirect to facilitator classes list
    """
    return redirect('facilitator_classes')


@login_required
def facilitator_mark_office_work_attendance(request):
    """
    Mark office work attendance (present/absent)
    """
    from .models import CalendarDate, OfficeWorkAttendance
    from datetime import date
    
    if request.method == "POST":
        calendar_date_id = request.POST.get('calendar_date_id')
        status = request.POST.get('status')  # 'present' or 'absent'
        remarks = request.POST.get('remarks', '').strip()
        
        try:
            calendar_date = CalendarDate.objects.get(id=calendar_date_id)
        except CalendarDate.DoesNotExist:
            messages.error(request, "Invalid calendar date")
            return redirect("facilitator_today_session")
        
        if status not in ['present', 'absent']:
            messages.error(request, "Invalid status")
            return redirect("facilitator_today_session")
        
        # Create or update attendance record
        attendance, created = OfficeWorkAttendance.objects.update_or_create(
            calendar_date=calendar_date,
            facilitator=request.user,
            defaults={
                'status': status,
                'remarks': remarks,
            }
        )
        
        status_text = "Present" if status == AttendanceStatus.PRESENT else "Absent"
        messages.success(request, f"Office work attendance marked as {status_text}")
        
        return redirect("facilitator_today_session")
    
    messages.error(request, "Invalid request")
    return redirect("facilitator_today_session")


@facilitator_required
def facilitator_today_session_calendar(request):
    """
    Show today's session dashboard - OPTIMIZED
    - Only loads TODAY's sessions (not all 700+)
    - Uses prefetch_related to avoid N+1 queries
    - Batch queries for attendance data
    """
    from datetime import date
    from django.db.models import Count, Q, Prefetch
    from .models import CalendarDate, OfficeWorkAttendance, PlannedSession, ActualSession, Attendance
    
    today = date.today()
    
    # Get facilitator's schools (single query)
    facilitator_schools_qs = School.objects.filter(
        facilitators__facilitator=request.user,
        facilitators__is_active=True
    ).order_by('name')
    facilitator_schools_ids = list(facilitator_schools_qs.values_list('id', flat=True))
    
    # OPTIMIZATION: Only query TODAY's calendar entries with prefetch
    calendar_sessions_today = CalendarDate.objects.filter(
        date=today,
        date_type=DateType.SESSION
    ).select_related('school', 'calendar__supervisor').prefetch_related('class_sections')
    
    classes_today = []
    processed_calendar_ids = set()
    
    # Track which first_class IDs we need actual sessions for
    class_to_calendar_map = {}
    
    # First pass: collect calendar entries and corresponding first classes
    for calendar_date in calendar_sessions_today:
        calendar_id = str(calendar_date.id)
        if calendar_id in processed_calendar_ids:
            continue
        processed_calendar_ids.add(calendar_id)
        
        grouped_classes = list(calendar_date.class_sections.all()) if calendar_date.class_sections.exists() else []
        facilitator_grouped_classes = [cls for cls in grouped_classes if cls.school_id in facilitator_schools_ids]
        
        if not facilitator_grouped_classes:
            continue
        
        first_class = facilitator_grouped_classes[0]
        class_to_calendar_map[first_class.id] = {
            'calendar_date': calendar_date,
            'grouped_classes': facilitator_grouped_classes,
            'first_class': first_class
        }

    # OPTIMIZATION: Bulk query all actual sessions for today
    actual_sessions_today = ActualSession.objects.filter(
        planned_session__class_section_id__in=class_to_calendar_map.keys(),
        date=today
    ).select_related('planned_session', 'planned_session__class_section')
    
    actual_session_ids = []
    for actual_session in actual_sessions_today:
        class_id = actual_session.planned_session.class_section.id
        if class_id in class_to_calendar_map:
            map_data = class_to_calendar_map[class_id]
            actual_session_ids.append(actual_session.id)
            classes_today.append({
                'class_sections': map_data['grouped_classes'],
                'class_section': map_data['first_class'],
                'planned_session': actual_session.planned_session,
                'actual_session': actual_session,
                'calendar_date': map_data['calendar_date'],
                'attendance_summary': None,  # Will fill in batch query
                'status': 'session',
            })
    
    # OPTIMIZATION: Batch query all attendance data for today's sessions
    if actual_session_ids:
        attendance_summaries = Attendance.objects.filter(
            actual_session_id__in=actual_session_ids
        ).values('actual_session_id', 'status').annotate(count=Count('id'))
        
        attendance_dict = {}
        for record in attendance_summaries:
            session_id = record['actual_session_id']
            if session_id not in attendance_dict:
                attendance_dict[session_id] = {'present': 0, 'absent': 0, 'leave': 0, 'total': 0}
            
            status = record['status']
            count = record['count']
            if status == AttendanceStatus.PRESENT:
                attendance_dict[session_id]['present'] = count
            elif status == AttendanceStatus.ABSENT:
                attendance_dict[session_id]['absent'] = count
            elif status == AttendanceStatus.LEAVE:
                attendance_dict[session_id]['leave'] = count
            attendance_dict[session_id]['total'] += count
        
        # Update classes_today with attendance summaries
        for item in classes_today:
            session_id = item['actual_session'].id
            if session_id in attendance_dict:
                item['attendance_summary'] = attendance_dict[session_id]
    
    # Get office work for today
    office_work_today = None
    office_work_calendar = CalendarDate.objects.filter(
        date=today,
        date_type=DateType.OFFICE_WORK
    ).select_related('calendar__supervisor').prefetch_related('assigned_facilitators').first()
    
    is_assigned_to_office_work = False
    if office_work_calendar:
        is_assigned_to_office_work = office_work_calendar.assigned_facilitators.filter(id=request.user.id).exists()
        
        if is_assigned_to_office_work:
            office_attendance = OfficeWorkAttendance.objects.filter(
                calendar_date=office_work_calendar,
                facilitator=request.user
            ).first()
            
            office_work_today = {
                'calendar_date': office_work_calendar,
                'is_assigned': True,
                'attendance': office_attendance,
            }
    
    # Get holiday for today
    holiday_today = None
    holiday_calendar = CalendarDate.objects.filter(
        date=today,
        date_type=DateType.HOLIDAY
    ).first()
    
    if holiday_calendar:
        holiday_today = {
            'holiday_name': holiday_calendar.holiday_name,
            'notes': holiday_calendar.notes
        }
    
    # OPTIMIZATION: Reuse facilitator_schools_qs for classes query
    facilitator_classes = ClassSection.objects.filter(
        school__in=facilitator_schools_qs
    ).select_related('school').order_by('school__name', 'class_level', 'section')
    
    context = {
        'today': today,
        'classes_today': classes_today,
        'office_work_today': office_work_today,
        'holiday_today': holiday_today,
        'facilitator_schools': facilitator_schools_qs,
        'facilitator_classes': facilitator_classes,
        'total_sessions_today': len(classes_today),
        'has_office_work': is_assigned_to_office_work,
        'has_holiday': holiday_today is not None,
    }
    
    return render(request, 'facilitator/Today_session.html', context)


@facilitator_required
def facilitator_performance_class_select(request):
    """
    Show all classes assigned to facilitator for performance management
    """
    from .models import StudentPerformanceSummary, Subject
    
    # Get all classes assigned to this facilitator
    facilitator_schools = FacilitatorSchool.objects.filter(
        facilitator=request.user,
        is_active=True
    ).values_list('school_id', flat=True)
    
    classes = ClassSection.objects.filter(
        school_id__in=facilitator_schools,
        is_active=True
    ).order_by('school__name', 'class_level', 'section')
    
    # Add stats for each class
    classes_with_stats = []
    for class_section in classes:
        student_count = Enrollment.objects.filter(
            class_section=class_section,
            is_active=True
        ).count()
        
        performance_count = StudentPerformanceSummary.objects.filter(
            class_section=class_section
        ).count()
        
        subject_count = Subject.objects.filter(is_active=True).count()
        
        classes_with_stats.append({
            'id': class_section.id,
            'display_name': class_section.display_name,
            'school_name': class_section.school.name,
            'student_count': student_count,
            'performance_count': performance_count,
            'subject_count': subject_count,
        })
    
    context = {
        'classes': classes_with_stats,
    }
    
    return render(request, 'facilitator/performance/class_select.html', context)



@facilitator_required
def facilitator_grouped_session(request):
    """
    Handle grouped session view - redirects to today_session with grouped class info
    Classes are passed as query parameter: ?classes=id1,id2,id3
    Stores grouped class info in session, then redirects to primary class today_session
    """
    from datetime import date
    import uuid
    
    # Get class IDs from query parameter
    class_ids_str = request.GET.get('classes', '')
    if not class_ids_str:
        messages.error(request, "No classes specified")
        return redirect('facilitator_classes')
    
    # Parse and validate UUIDs
    class_ids = []
    for cid in class_ids_str.split(','):
        cid = cid.strip()
        if cid:
            try:
                # Validate UUID format
                uuid.UUID(cid)
                class_ids.append(cid)
            except ValueError:
                messages.error(request, f"Invalid class ID format: {cid}")
                return redirect('facilitator_classes')
    
    if not class_ids:
        messages.error(request, "Invalid class IDs")
        return redirect('facilitator_classes')
    
    # Get all grouped classes
    grouped_classes = ClassSection.objects.filter(
        id__in=class_ids
    ).select_related('school').order_by('class_level', 'section')
    
    if not grouped_classes.exists():
        messages.error(request, "Classes not found")
        return redirect('facilitator_classes')
    
    # Verify facilitator has access to all classes
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    facilitator_schools = mixin.get_facilitator_schools()
    
    for cls in grouped_classes:
        if cls.school not in facilitator_schools:
            messages.error(request, "You do not have access to one or more classes")
            return redirect('facilitator_classes')
    
    # Get primary class (first in group)
    primary_class = grouped_classes.first()
    
    # Store grouped class info in session for display in today_session template
    # Store as list of UUID strings for consistency
    request.session['is_grouped_session'] = True
    request.session['grouped_class_ids'] = [str(cls.id) for cls in grouped_classes]
    request.session['grouped_classes_display'] = [
        {'id': str(cls.id), 'display_name': cls.display_name} 
        for cls in grouped_classes
    ]
    
    # Redirect to primary class today_session view
    # The today_session view will use the session data to show grouped class info
    return redirect('facilitator_class_today_session', class_section_id=primary_class.id)


# =====================================================
# Facilitator Settings
# =====================================================

@facilitator_required
def facilitator_settings(request):
    """Facilitator settings page"""
    return render(request, "facilitator/settings.html", {})


# =====================================================
# BULK STUDENT IMPORT FUNCTIONS
# =====================================================

@login_required
@facilitator_required
def facilitator_student_import(request, class_section_id):
    """Bulk import students via CSV/Excel for a specific class"""
    class_section = get_object_or_404(ClassSection, id=class_section_id)
    
    # Check access - facilitator must have access to this class
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    if not mixin.check_class_access(class_section_id):
        raise PermissionDenied("You don't have access to this class")
    
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            messages.error(request, "Please upload a file")
            return redirect(request.path)
        
        ext = file.name.split(".")[-1].lower()
        
        # Parse file
        if ext == "csv":
            rows = csv.DictReader(file.read().decode("utf-8").splitlines())
        elif ext in ["xlsx", "xls"]:
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            headers = [str(cell.value).strip() for cell in sheet[1]]
            rows = []
            for r in sheet.iter_rows(min_row=2, values_only=True):
                rows.append(dict(zip(headers, r)))
        else:
            messages.error(request, "Unsupported file format. Use CSV or Excel.")
            return redirect(request.path)
        
        created_count = 0
        skipped_count = 0
        
        # Process rows
        for row in rows:
            enrollment_no = str(row.get("enrollment_number", "")).strip()
            full_name = str(row.get("full_name", "")).strip()
            gender = str(row.get("gender", "")).strip()
            start_date = row.get("start_date") or date.today()
            
            # Validate
            if not all([enrollment_no, full_name, gender]):
                skipped_count += 1
                continue
            
            if gender.upper() not in ["M", "F"]:
                skipped_count += 1
                continue
            
            # Create student
            student, _ = Student.objects.get_or_create(
                enrollment_number=enrollment_no,
                defaults={
                    "full_name": full_name,
                    "gender": gender.upper()
                }
            )
            
            # Create enrollment
            enrollment, created = Enrollment.objects.get_or_create(
                student=student,
                school=class_section.school,
                class_section=class_section,
                defaults={
                    "start_date": start_date,
                    "is_active": True
                }
            )
            
            if created:
                created_count += 1
        
        # Feedback
        if created_count == 0:
            messages.warning(request, f"No students imported. Skipped: {skipped_count}")
        else:
            messages.success(request, f"{created_count} students imported (Skipped: {skipped_count})")
        
        return redirect("facilitator_class_students", class_section_id=class_section_id)
    
    return render(request, "facilitator/students/import.html", {
        "class_section": class_section
    })


@login_required
@facilitator_required
def facilitator_download_sample_csv(request):
    """Download sample CSV for student import"""
    sample_data = [
        ["enrollment_number", "full_name", "gender", "start_date"],
        ["E001", "John Doe", "M", "2026-01-12"],
        ["E002", "Jane Smith", "F", "2026-01-12"],
    ]
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students_sample.csv"'
    
    writer = csv.writer(response)
    for row in sample_data:
        writer.writerow(row)
    
    return response


@login_required
@facilitator_required
def facilitator_my_attendance(request):
    """
    Shows today's sessions for the facilitator and allows marking attendance.
    Proactively finds next pending session for each class.
    """
    today = timezone.localdate()
    
    try:
        # Get facilitator's assigned schools (Same logic as Dashboard)
        assigned_school_ids = FacilitatorSchool.objects.filter(
            facilitator=request.user,
            is_active=True
        ).values_list("school_id", flat=True)
        
        # Get all active classes in these schools
        class_sections = ClassSection.objects.filter(
            school_id__in=assigned_school_ids,
            is_active=True
        ).select_related('school').order_by('school__name', 'class_level', 'section')
        
        # Get schools for calendar lookup
        schools = list(assigned_school_ids)

        
        # 1. ENSURE SESSIONS EXIST FOR TODAY (Skip on Sundays as per user request)
        if today.weekday() != 6: # 6 is Sunday
            for cls in class_sections:
                # Check if there's already an ActualSession for today
                has_today_session = ActualSession.objects.filter(
                    planned_session__class_section=cls,
                    date=today
                ).exists()
                
                # Also check if today is a holiday/office work for this school/class
                is_off_day = CalendarDate.objects.filter(
                    date=today,
                    date_type__in=[DateType.HOLIDAY, DateType.OFFICE_WORK]
                ).filter(
                    Q(school=cls.school, class_section__isnull=True) |
                    Q(school__isnull=True) |
                    Q(class_section=cls) |
                    Q(class_sections=cls)
                ).exists()
                
                if not has_today_session and not is_off_day:
                    next_planned = SessionSequenceCalculator.get_next_pending_session(cls)
                    if next_planned:
                        try:
                            # This creates an ActualSession (PENDING) and updates progress
                            SessionStatusManager.conduct_session(
                                next_planned, 
                                request.user, 
                                remarks="Auto-started via My Attendance"
                            )
                        except Exception as ex:
                            logger.warning(f"Failed to auto-start session for {cls}: {ex}")

        # 2. FETCH TODAY'S SESSIONS (Including the ones we just created)
        actual_sessions_today = ActualSession.objects.filter(
            planned_session__class_section__in=class_sections,
            date=today
        ).select_related(
            'planned_session', 
            'planned_session__class_section', 
            'planned_session__class_section__school'
        ).order_by('date')
        
        # 3. IDENTIFY CALENDAR EVENTS (Holidays, Office Work, and Today's Groups)
        calendar_events = CalendarDate.objects.filter(
            date=today,
            date_type__in=[DateType.HOLIDAY, DateType.OFFICE_WORK, DateType.SESSION]
        ).filter(
            Q(school_id__in=schools) |
            Q(school__isnull=True) |
            Q(class_section__in=class_sections) |
            Q(class_sections__in=class_sections)
        ).distinct().prefetch_related('class_sections')
        
        # Build today's grouping map for the attendance UI
        calendar_grouping_map = {} # class_id -> list of member classes
        for cal in calendar_events:
            if cal.date_type == DateType.SESSION and cal.class_sections.exists():
                members = list(cal.class_sections.all())
                for m in members:
                    calendar_grouping_map[m.id] = members

        
        # 3a. IDENTIFY HOLIDAY CLASSES
        holiday_classes = set()
        off_day_events_by_class = {} # cls_id -> event
        
        for event in calendar_events:
            if event.date_type in [DateType.HOLIDAY, DateType.OFFICE_WORK]:
                event_classes = []
                if event.class_section:
                    event_classes.append(event.class_section)
                elif event.class_sections.exists():
                    event_classes.extend(list(event.class_sections.all()))
                elif not event.school or event.school_id in schools:
                    # School-wide or Global event
                    event_classes.extend(list(class_sections.filter(school=event.school) if event.school else class_sections))
                
                for cls in event_classes:
                    holiday_classes.add(cls.id)
                    off_day_events_by_class[cls.id] = event

        all_sessions = []
        ui_processed_classes = set()
        
        # Add holiday/office work placeholders FIRST to ensure they take priority
        for cls_id, event in off_day_events_by_class.items():
            cls = next((c for c in class_sections if c.id == cls_id), None)
            if not cls: continue
            
            display_type = "Holiday" if event.date_type == DateType.HOLIDAY else "Office Work"
            placeholder = type('SessionPlaceholder', (), {
                'id': None,
                'date': today,
                'planned_session': type('PlannedPlaceholder', (), {
                    'class_section': cls,
                    'school': cls.school,
                    'title': display_type
                })(),
                'facilitator_attendance': 'present' if event.date_type == DateType.OFFICE_WORK else None,
                'grouping_status': 'single',
                'grouped_class_names': '',
                'is_calendar_event': True,
                'event_type': event.date_type,
                'holiday_name': event.holiday_name if event.date == today else None,
                'holiday_notes': event.notes if event.date == today else None
            })()
            all_sessions.append(placeholder)
            ui_processed_classes.add(cls.id)

        for session in actual_sessions_today:
            cls_id = session.planned_session.class_section.id
            if cls_id in ui_processed_classes:
                continue
                
            # Check for manual grouping today
            group_members = calendar_grouping_map.get(cls_id)
            if group_members and len(group_members) > 1:
                # This is a grouped session
                session.grouping_status = 'grouped'
                session.grouped_class_names = " + ".join([m.display_name for m in group_members if m.id != cls_id])
                
                all_sessions.append(session)
                for m in group_members:
                    ui_processed_classes.add(m.id)
            else:

                session.grouping_status = 'single'
                session.grouped_class_names = ''
                all_sessions.append(session)
                ui_processed_classes.add(cls_id)

            
        # Add remaining calendar events (like SESSION groupings that didn't have ActualSession yet)
        for event in calendar_events:
            if event.date_type == DateType.SESSION:
                event_classes = []
                if event.class_section:
                    event_classes.append(event.class_section)
                elif event.class_sections.exists():
                    event_classes.extend(list(event.class_sections.all()))
                
                for cls in event_classes:
                    if cls.id not in ui_processed_classes:
                        # This handles session groupings that haven't been started
                        # The fallback logic below will handle these as well, 
                        # but we can preserve grouping info here if needed.
                        pass # Placeholder logic can be added if grouping info is critical for unstarted items

        # 4. FINAL FALLBACK: Add any assigned class that is still missing
        for cls in class_sections:
            if cls.id not in ui_processed_classes:
                placeholder = type('SessionPlaceholder', (), {
                    'id': None,
                    'date': today,
                    'planned_session': type('PlannedPlaceholder', (), {
                        'class_section': cls,
                        'school': cls.school,
                        'title': "No Session Scheduled"
                    })(),
                    'grouping_status': 'single',
                    'grouped_class_names': '',
                    'is_calendar_event': False
                })()
                all_sessions.append(placeholder)
                ui_processed_classes.add(cls.id)
        
        # Calculate statistics
        marked = sum(1 for s in all_sessions if hasattr(s, 'facilitator_attendance') and s.facilitator_attendance in ['present', 'absent', 'leave'])
        unmarked = len(all_sessions) - marked
        
        context = {
            'sessions': all_sessions,
            'today': today,
            'total_sessions': len(all_sessions),
            'marked_sessions': marked,
            'unmarked_sessions': unmarked,
            'is_sunday': today.weekday() == 6,
        }
        
        return render(request, 'facilitator/my_attendance.html', context)
        
    except Exception as e:
        logger.error(f"Error in facilitator_my_attendance: {str(e)}", exc_info=True)
        context = {
            'sessions': [],
            'today': today,
            'total_sessions': 0,
            'marked_sessions': 0,
            'unmarked_sessions': unmarked if 'unmarked' in locals() else 0,
            'error': str(e),
        }
        return render(request, 'facilitator/my_attendance.html', context)


@facilitator_required
def update_session_status(request):
    """
    AJAX endpoint to update session status for classes
    Options: curriculum, office_work, skip_next_day
    IMPORTANT: day_number stays the same when changing status
    """
    from .models import ActualSession, PlannedSession, ClassSection, CalendarDate, DateType
    from datetime import date, timedelta
    
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
        
        data = request.POST
        status = data.get('status')
        class_ids = data.getlist('class_ids')
        
        if not status or not class_ids:
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)
        
        # Verify facilitator has access to all classes
        mixin = FacilitatorAccessMixin()
        mixin.request = request
        facilitator_schools = mixin.get_facilitator_schools().values_list('id', flat=True)
        
        classes = ClassSection.objects.filter(id__in=class_ids)
        for cls in classes:
            if cls.school_id not in facilitator_schools:
                return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        today = date.today()
        
        if status == 'curriculum':
            # Keep as curriculum session (no changes needed)
            return JsonResponse({
                'success': True,
                'message': f'Marked {len(class_ids)} class(es) as curriculum session'
            })
        
        elif status == 'office_work':
            # Mark as office work - create CalendarDate entry
            for class_id in class_ids:
                cls = ClassSection.objects.get(id=class_id)
                
                # Delete existing ActualSession for today
                ActualSession.objects.filter(
                    planned_session__class_section=cls,
                    date=today
                ).delete()
                
                # Create or update CalendarDate for office work
                CalendarDate.objects.update_or_create(
                    school=cls.school,
                    date=today,
                    date_type=DateType.OFFICE_WORK,
                    defaults={'is_active': True}
                )
            
            # Clear cache
            from django.core.cache import cache
            cache.delete(f'facilitator_{request.user.id}_attendance')
            
            return JsonResponse({
                'success': True,
                'message': f'Marked {len(class_ids)} class(es) as office work'
            })
        
        elif status == 'skip_next_day':
            # Move session to next day - keep same day_number
            tomorrow = today + timedelta(days=1)
            
            for class_id in class_ids:
                cls = ClassSection.objects.get(id=class_id)
                
                # Get today's session to get day_number
                today_session = ActualSession.objects.filter(
                    planned_session__class_section=cls,
                    date=today
                ).first()
                
                if today_session:
                    day_number = today_session.planned_session.day_number
                    grouped_id = today_session.planned_session.grouped_session_id
                    
                    # Delete today's session
                    today_session.delete()
                    
                    # Create new session for tomorrow with SAME day_number and group ID
                    planned = PlannedSession.objects.create(
                        class_section=cls,
                        day_number=day_number,
                        grouped_session_id=grouped_id,
                        is_active=True
                    )
                    
                    ActualSession.objects.create(
                        planned_session=planned,
                        date=tomorrow,
                        status=0,  # PENDING
                        facilitator=request.user
                    )
            
            # Clear cache
            from django.core.cache import cache
            cache.delete(f'facilitator_{request.user.id}_attendance')
            
            return JsonResponse({
                'success': True,
                'message': f'Moved {len(class_ids)} class(es) to next day'
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status'
            }, status=400)
    
    except Exception as e:
        logger.error(f"Error in update_session_status: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@facilitator_required
def get_grouping_options(request, class_section_id):
    """
    AJAX endpoint to get grouping options for a class
    Returns list of other classes that can be grouped with this class
    """
    from .models import ClassSection
    
    try:
        class_section = get_object_or_404(ClassSection, id=class_section_id)
        
        # Verify facilitator has access
        mixin = FacilitatorAccessMixin()
        mixin.request = request
        
        if class_section.school_id not in mixin.get_facilitator_schools().values_list('id', flat=True):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Get all other classes in the same school
        other_classes = ClassSection.objects.filter(
            school=class_section.school,
            is_active=True
        ).exclude(id=class_section_id).order_by('class_level', 'section')
        
        options = []
        for cls in other_classes:
            options.append({
                'id': str(cls.id),
                'class_id': str(cls.id),
                'label': cls.display_name
            })
        
        return JsonResponse({
            'success': True,
            'current_class': {
                'id': str(class_section.id),
                'name': class_section.display_name
            },
            'options': options
        })
    
    except Exception as e:
        logger.error(f"Error in get_grouping_options: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@facilitator_required
def apply_grouping(request):
    """
    AJAX endpoint to apply grouping between classes
    Creates a grouped session for the specified classes
    """
    from .models import ClassSection, GroupedSession, PlannedSession, ActualSession
    from datetime import datetime
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        primary_class_id = data.get('primary_class_id')
        secondary_class_ids = data.get('secondary_class_ids', [])
        session_date = data.get('session_date')
        
        if not primary_class_id or not secondary_class_ids:
            return JsonResponse({
                'success': False,
                'error': 'Primary class and at least one secondary class required'
            }, status=400)
        
        # Verify facilitator has access to all classes
        mixin = FacilitatorAccessMixin()
        mixin.request = request
        facilitator_schools = mixin.get_facilitator_schools()
        
        primary_class = get_object_or_404(ClassSection, id=primary_class_id)
        if primary_class.school_id not in facilitator_schools.values_list('id', flat=True):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Verify all secondary classes are in the same school
        secondary_classes = ClassSection.objects.filter(
            id__in=secondary_class_ids,
            school=primary_class.school
        )
        
        if secondary_classes.count() != len(secondary_class_ids):
            return JsonResponse({
                'success': False,
                'error': 'All classes must be in the same school'
            }, status=400)
        
        # 1. Generate the shared Grouped Session UUID
        import uuid
        from django.utils import timezone
        today = timezone.now().date()
        group_uuid = uuid.uuid4()
        
        # 2. Get the target primary day number
        primary_session_query = ActualSession.objects.filter(
            planned_session__class_section=primary_class,
            date=today
        ).select_related('planned_session').first()
        
        if primary_session_query:
            target_day = primary_session_query.planned_session.day_number
        else:
            # Get next pending session
            from .session_management import SessionSequenceCalculator
            pending = SessionSequenceCalculator.get_next_pending_session(primary_class)
            target_day = pending.day_number if pending else 1
            
            # Fetch the planned session itself to update
            primary_planned = PlannedSession.objects.filter(
                class_section=primary_class,
                day_number=target_day,
                is_active=True
            ).first()
            
            if primary_planned:
                primary_planned.grouped_session_id = group_uuid
                primary_planned.save(update_fields=['grouped_session_id'])

        # 3. Create the GroupedSession master record
        grouped_session = GroupedSession.objects.create(
            grouped_session_id=group_uuid,
            name=f"Group: {primary_class.display_name} + {secondary_classes.count()} others"
        )
        grouped_session.class_sections.add(primary_class)
        grouped_session.class_sections.add(*secondary_classes)
        
        # 4. Create/Update CalendarDate for Unified Grouping Logic (Required for UI)
        from .models import CalendarDate, DateType
        
        # Remove any existing session groups for these classes today to avoid conflicts
        CalendarDate.objects.filter(
            date=today,
            date_type=DateType.SESSION,
            class_sections__in=[primary_class] + list(secondary_classes)
        ).distinct().delete()
        
        # Create new daily group record
        from .models import SupervisorCalendar
        calendar, _ = SupervisorCalendar.objects.get_or_create(supervisor=request.user)
        
        cal_date = CalendarDate.objects.create(
            calendar=calendar,
            date=today,
            school=primary_class.school,
            date_type=DateType.SESSION,
            notes=f"Group Session: {primary_class.display_name} & others"
        )
        # Add primary facilitator
        cal_date.assigned_facilitators.add(request.user)
        
        cal_date.class_sections.add(primary_class)
        cal_date.class_sections.add(*secondary_classes)
        
        # 5. Synchronize secondary classes to match day number and UUID
        for sec_cls in secondary_classes:
            # Check if there's an existing PlannedSession for this class on the target day
            sec_planned = PlannedSession.objects.filter(
                class_section=sec_cls,
                day_number=target_day
            ).first()

            if not sec_planned:
                # If no planned session exists for the target day, try to find the one they were supposed to do today
                # and move it, OR create a new one.
                sec_actual_today = ActualSession.objects.filter(
                    planned_session__class_section=sec_cls,
                    date=today
                ).select_related('planned_session').first()

                if sec_actual_today:
                    sec_planned = sec_actual_today.planned_session
                    sec_planned.day_number = target_day
                    sec_planned.grouped_session_id = group_uuid
                    sec_planned.save(update_fields=['day_number', 'grouped_session_id'])
                else:
                    # Create new planned session if none exists at all for this day
                    sec_planned = PlannedSession.objects.create(
                        class_section=sec_cls,
                        day_number=target_day,
                        grouped_session_id=group_uuid,
                        is_active=True,
                        title=f"Day {target_day}",
                        sequence_position=target_day
                    )
            else:
                # If it already exists, just update its grouped_session_id
                sec_planned.grouped_session_id = group_uuid
                sec_planned.save(update_fields=['grouped_session_id'])

            # Assign/Update ActualSession for today for this class
            sec_actual = ActualSession.objects.filter(
                planned_session__class_section=sec_cls,
                date=today
            ).first()
            if sec_actual:
                sec_actual.planned_session = sec_planned
                sec_actual.status = 0
                sec_actual.facilitator = request.user
                sec_actual.save(update_fields=['planned_session', 'status', 'facilitator'])
            else:
                ActualSession.objects.create(
                    planned_session=sec_planned,
                    date=today,
                    status=0,
                    facilitator=request.user
                )
                
        # Clear facilitator cache
        from django.core.cache import cache
        cache.delete(f'facilitator_{request.user.id}_attendance')
        
        # Clear specific caches for involved classes
        for cls in [primary_class] + list(secondary_classes):
            # Clear today_session grouping cache
            cache.delete(f"grouped_session_status_{cls.id}_{today}")
            # Clear dashboard/attendance status caches that might be affected
            cache.delete(f"facilitator_attendance_{request.user.id}_{cls.id}_{today}")
            cache.delete(f"facilitator_dashboard_{request.user.id}") # Clear dashboard cache as well
        
        return JsonResponse({
            'success': True,
            'grouped_session_id': str(grouped_session.id),
            'message': f'Group created. All {grouped_session.class_sections.count()} classes synced to Day {target_day}.'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in apply_grouping: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while creating grouped session'
        }, status=500)
@csrf_exempt
@login_required
def clear_grouping(request):
    """Clear grouping for a facilitator's classes for today"""
    if request.user.role.name.upper() != "FACILITATOR":
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
    try:
        from .models import PlannedSession, ActualSession, GroupedSession, CalendarDate, DateType
        from django.utils import timezone
        from django.core.cache import cache
        today = timezone.now().date()
        
        # 1. Find all planned sessions for this facilitator for today that are grouped
        facilitator_classes = ClassSection.objects.filter(
            school__facilitators__facilitator=request.user
        )
        
        # Get sessions that have a grouped_session_id
        grouped_planned_sessions_for_facilitator = PlannedSession.objects.filter(
            class_section__in=facilitator_classes,
            grouped_session_id__isnull=False,
            is_active=True
        )
        
        # Collect class IDs and group UUIDs before clearing
        class_ids_to_clear_cache = set()
        group_uuids_to_clear = set()
        for ps in grouped_planned_sessions_for_facilitator:
            class_ids_to_clear_cache.add(ps.class_section_id)
            if ps.grouped_session_id:
                group_uuids_to_clear.add(ps.grouped_session_id)

        # 2. Fast clear ALL grouped_session_id from PlannedSessions
        PlannedSession.objects.filter(
            class_section__in=facilitator_classes, 
            grouped_session_id__isnull=False
        ).update(grouped_session_id=None)
        
        if group_uuids_to_clear:
            # Also clear any stray sessions tied to these groups
            PlannedSession.objects.filter(grouped_session_id__in=group_uuids_to_clear).update(grouped_session_id=None)
            
            # 3. Delete the GroupedSession master records
            GroupedSession.objects.filter(grouped_session_id__in=group_uuids_to_clear).delete()
        
        # 4. Delete ALL CalendarDate records for these classes that represent groupings
        # We clear ALL past and future daily groupings for these classes to ensure a totally clean start
        CalendarDate.objects.filter(
            date_type=DateType.SESSION,
            class_sections__in=facilitator_classes
        ).distinct().delete()
        
        # 5. Clear ALL relevant caches
        for ps in PlannedSession.objects.filter(class_section__in=facilitator_classes, is_active=True):
            cache.delete(f"grouped_classes:{ps.id}:{today}")
            
        for cls_id in facilitator_classes.values_list('id', flat=True):
            # Clear today grouping status
            cache.delete(f"grouped_session_status_{cls_id}_{today}")
            # Clear general grouped classes cache
            # Since we don't know all dates, we clear a few primary ones or trust time-to-live
            cache.delete(f"facilitator_attendance_{request.user.id}_{cls_id}_{today}")
            
        cache.delete(f"facilitator_{request.user.id}_attendance")
        cache.delete(f"facilitator_dashboard_{request.user.id}")

        return JsonResponse({'success': True, 'message': 'All past and present grouping links cleared successfully.'})
        
    except Exception as e:
        logger.error(f"Error in clear_grouping: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@facilitator_required
def send_class_unavailable_notification(request):
    """
    Send notification to supervisor when class is not available
    Creates a notification that appears in supervisor dashboard
    """
    from django.core.cache import cache
    from datetime import date
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        data = json.loads(request.body)
        class_id = data.get('class_id')
        class_name = data.get('class_name', 'Unknown Class')
        facilitator_name = data.get('facilitator_name', request.user.full_name)
        
        if not class_id:
            return JsonResponse({'success': False, 'error': 'Class ID required'}, status=400)
        
        # Get the class to verify it exists and get school info
        try:
            class_section = ClassSection.objects.get(id=class_id)
        except ClassSection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Class not found'}, status=404)
        
        # Get all supervisors to broadcast the notification
        supervisors = User.objects.filter(role__name='Supervisor')
        
        if not supervisors.exists():
            return JsonResponse({'success': False, 'error': 'No supervisor found in database'}, status=404)
        
        # Create notification data
        today = date.today()
        notification = {
            'id': str(class_id),
            'type': 'class_unavailable',
            'facilitator_name': facilitator_name,
            'facilitator_id': str(request.user.id),
            'class_name': class_name,
            'class_id': str(class_id),
            'school_name': class_section.school.name,
            'school_id': str(class_section.school.id),
            'date': today.isoformat(),
            'timestamp': timezone.now().isoformat(),
            'message': f'{facilitator_name} reported that {class_name} is not available today'
        }
        
        # 1. DATABASE LOGGING (Reliable for production)
        # Find the group of classes for today
        from .session_management import SessionSequenceCalculator, get_grouped_classes_for_session
        next_planned = SessionSequenceCalculator.get_next_pending_session(class_section)
        classes_in_group = get_grouped_classes_for_session(next_planned, today) if next_planned else [class_section]
        
        # If part of a group, we mark ALL of them as cancelled
        total_affected_names = []
        for cls in classes_in_group:
            cls_planned = SessionSequenceCalculator.get_next_pending_session(cls)
            if cls_planned:
                ActualSession.objects.update_or_create(
                    planned_session=cls_planned,
                    date=today,
                    defaults={
                        'status': SessionStatus.CANCELLED,
                        'facilitator': request.user,
                        'remarks': f"NOTIFICATION: {facilitator_name} reported class unavailable. Message: {notification['message']}"
                    }
                )
                total_affected_names.append(cls.display_name)
        
        # If it was a group report, update the notification message slightly
        if len(classes_in_group) > 1:
            display_names = ", ".join(total_affected_names)
            notification['class_name'] = display_names
            notification['message'] = f"{facilitator_name} reported that group ({display_names}) is not available today"
            # Update the ID to represent the group (using first ID)
            notification['id'] = f"group_{classes_in_group[0].id}"
        
        if not total_affected_names:
            logger.warning(f"No pending session found for {class_name} (or its group) to mark as CANCELLED")

        # 2. CACHE BROADCAST (For immediate UI updates if on same worker)
        for supervisor in supervisors:
            cache_key = f"supervisor_notifications_{supervisor.id}"
            notifications = cache.get(cache_key, [])
            notifications.insert(0, notification)
            notifications = notifications[:50]
            cache.set(cache_key, notifications, 86400) # 24 hours
            
        logger.info(f"Class unavailable notification saved to DB and cache: {class_name} by {facilitator_name}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notification sent to supervisor',
            'notification': notification
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in send_class_unavailable_notification: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@facilitator_required
def facilitator_class_office_work(request, class_section_id):
    """
    Shows a form to log Office Work specifically replacing a class session.
    Saves the description in the ActualSession's remarks field.
    """
    from .models import ClassSection, PlannedSession, ActualSession, SessionStatus, GroupedSession
    from django.utils import timezone
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect, render
    from .mixins import FacilitatorAccessMixin
    
    class_section = get_object_or_404(ClassSection, id=class_section_id)
    today = timezone.localdate()
    day_number = 997  # Designated Day number for Class-Level Office Work
    
    # Verify facilitator has access
    mixin = FacilitatorAccessMixin()
    mixin.request = request
    if class_section.school_id not in mixin.get_facilitator_schools().values_list('id', flat=True):
        messages.error(request, "Permission denied.")
        return redirect("no_permission")
    
    # Check for grouping (using robust helper)
    from .session_management import SessionSequenceCalculator, get_grouped_classes_for_session
    next_planned = SessionSequenceCalculator.get_next_pending_session(class_section)
    classes_to_process = get_grouped_classes_for_session(next_planned, today) if next_planned else [class_section]
    
    # Get persistent grouped_session_id if any (for PlannedSession creation)
    grouped_session_id = next_planned.grouped_session_id if next_planned else None
        
    if request.method == 'POST':
        office_work_category = request.POST.get('office_work_category', '')
        office_work_description = request.POST.get('office_work_description', '').strip()
        
        if not office_work_category:
            messages.error(request, 'Please select an office work category')
            return redirect('facilitator_class_office_work', class_section_id=class_section.id)
            
        # Combine into remarks
        remarks_content = f"Office Work Type: {office_work_category}"
        if office_work_description:
            remarks_content += f"\nDescription: {office_work_description}"
            
        # 1. Get or Create static PlannedSession for all classes in group
        existing_day_classes = set(PlannedSession.objects.filter(
            class_section__in=classes_to_process,
            day_number=day_number
        ).values_list('class_section_id', flat=True))
        
        for cls in classes_to_process:
            if cls.id not in existing_day_classes:
                PlannedSession.objects.create(
                    class_section=cls,
                    day_number=day_number,
                    title="Office Work",
                    is_active=False, # Hide from normal sequences
                    grouped_session_id=grouped_session_id
                )
                
        # Ensure strictly PENDING (auto-grouped) sessions are cleared, without deleting actual conducted sessions
        ActualSession.objects.filter(
            planned_session__class_section__in=classes_to_process,
            date=today,
            status=SessionStatus.PENDING
        ).delete()
        
        # 2. Get or Create ActualSession for TODAY
        for cls in classes_to_process:
            cls_planned = PlannedSession.objects.get(class_section=cls, day_number=day_number)
            actual_session, created = ActualSession.objects.get_or_create(
                planned_session=cls_planned,
                date=today,
                defaults={
                    'facilitator': request.user,
                    'status': SessionStatus.CONDUCTED,
                    'remarks': remarks_content
                }
            )
            if not created:
                actual_session.status = SessionStatus.CONDUCTED
                actual_session.remarks = remarks_content
                actual_session.facilitator = request.user
                actual_session.save(update_fields=['status', 'remarks', 'facilitator'])
                
        messages.success(request, f"Office work logged successfully for {class_section.display_name}")
        return redirect('facilitator_classes')
        
    # GET request - render the form
    context = {
        'class_section': class_section,
        'today': today,
        'is_grouped': len(classes_to_process) > 1,
        'grouped_classes': classes_to_process
    }
    return render(request, 'facilitator/classes/office_work_form.html', context)


@facilitator_required
def facilitator_office_work(request):
    """
    Simple office work attendance marking page
    Shows only office work details and attendance marking form
    """
    from datetime import date
    from .models import CalendarDate, OfficeWorkAttendance, DateType
    
    today = date.today()
    
    # Get office work for today
    office_work_calendar = CalendarDate.objects.filter(
        date=today,
        date_type=DateType.OFFICE_WORK
    ).select_related('calendar__supervisor').prefetch_related('assigned_facilitators').first()
    
    office_work_today = None
    is_assigned_to_office_work = False
    
    if office_work_calendar:
        is_assigned_to_office_work = office_work_calendar.assigned_facilitators.filter(id=request.user.id).exists()
        
        if is_assigned_to_office_work:
            office_attendance = OfficeWorkAttendance.objects.filter(
                calendar_date=office_work_calendar,
                facilitator=request.user
            ).first()
            
            office_work_today = {
                'calendar_date': office_work_calendar,
                'is_assigned': True,
                'attendance': office_attendance,
            }
    
    context = {
        'today': today,
        'office_work_today': office_work_today,
        'is_assigned': is_assigned_to_office_work,
    }
    
    return render(request, 'facilitator/office_work.html', context)
