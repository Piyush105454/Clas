"""
URL patterns for facilitator student management
"""
from django.urls import path
from . import facilitator_views

urlpatterns = [
    # School management
    path('schools/', facilitator_views.FacilitatorSchoolListView.as_view(), name='facilitator_schools_list'),
    path('schools/<uuid:pk>/', facilitator_views.FacilitatorSchoolDetailView.as_view(), name='facilitator_school_detail'),
    
    # Student management
    path('students/', facilitator_views.FacilitatorStudentListView.as_view(), name='facilitator_students_list'),
    path('students/create/', facilitator_views.FacilitatorStudentCreateView.as_view(), name='facilitator_student_create'),
    path('students/<uuid:pk>/edit/', facilitator_views.FacilitatorStudentUpdateView.as_view(), name='facilitator_student_edit'),
    path('students/<uuid:student_id>/detail/', facilitator_views.facilitator_student_detail, name='facilitator_student_detail'),
    
    # AJAX endpoints
    path('ajax/school-classes/', facilitator_views.facilitator_ajax_school_classes, name='facilitator_ajax_school_classes'),
    path('ajax/student/<uuid:student_id>/growth-analysis/', facilitator_views.facilitator_student_growth_analysis_ajax, name='facilitator_student_growth_analysis_ajax'),
]