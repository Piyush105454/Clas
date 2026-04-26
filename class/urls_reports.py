"""
URL patterns for reports functionality
"""

from django.urls import path
from . import reports_views

urlpatterns = [
    # Main reports dashboard
    path('admin/reports/', reports_views.reports_dashboard, name='reports_dashboard'),
    
    # AJAX endpoints for data
    path('admin/reports/data/<str:report_type>/', reports_views.get_report_data, name='get_report_data'),
    path('admin/reports/classes/<uuid:school_id>/', reports_views.get_classes_for_school, name='get_classes_for_school'),
    
    # PDF download endpoints
    path('admin/reports/download/pdf/<str:report_type>/', reports_views.download_pdf_report, name='download_pdf_report'),
    path('admin/reports/download/excel/<str:report_type>/', reports_views.download_excel_report, name='download_excel_report'),
    path('admin/reports/download/excel_all/', reports_views.download_all_excel_report, name='download_all_excel_report'),
]