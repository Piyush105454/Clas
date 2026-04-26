from django.urls import path, include
from .views_auth import (
    # Auth views
    login_view, logout_view, session_check_view, clear_session_view,
)
from .pwa_views import (
    # PWA views
    offline, service_worker, manifest, offline_sync, resource_prioritization,
)
from .supervisor_views import (
    # Admin-accessible wrappers for supervisor views
    admin_view_facilitators, admin_view_calendar, admin_get_notifications,
    admin_facilitator_detail, admin_calendar_add_date, admin_calendar_edit_date,
    admin_calendar_delete_date, admin_session_detail, admin_sessions_list,
    admin_class_sessions, admin_reports_dashboard
)
from .views import (
    # Auth
    dashboard, no_permission, admin_settings, heartbeat,
    
    # Optimized views (performance)
    admin_dashboard_optimized, admin_dashboard_stats_ajax, admin_system_snapshot_ajax, facilitator_dashboard_optimized, supervisor_dashboard_optimized,

    # Admin – users & setup
    users_view, add_user, edit_user, delete_user, create_user_ajax,
    schools, add_school, edit_school, delete_school, school_detail,
    class_sections_list, class_section_add, edit_class_section, class_section_delete, admin_bulk_add_classes, admin_bulk_create_classes,
    assign_facilitator, admin_sessions_filter,
)
from .reports_views import (
    # Admin - Reports
    reports_dashboard,
    get_report_data,
    get_classes_for_school,
)
from .supervisor_views import (
    # Supervisor - Dashboard
    supervisor_dashboard,
    
    # Supervisor - Users
    supervisor_users_list,
    supervisor_user_create,
    supervisor_user_edit,
    supervisor_user_delete,
    supervisor_create_user_ajax,
    
    # Supervisor - Schools
    supervisor_schools_list,
    supervisor_school_create,
    supervisor_school_edit,
    supervisor_school_detail,
    supervisor_school_delete,
    get_blocks_by_district,
    get_schools_by_block,
    get_all_schools,
    
    # Supervisor - Clusters
    clusters_list,
    cluster_create,
    cluster_edit,
    cluster_detail,
    cluster_delete,
    
    # Supervisor - Classes
    supervisor_classes_list,
    supervisor_class_create,
    supervisor_class_bulk_create,
    supervisor_class_edit,
    supervisor_class_delete,
    supervisor_bulk_add_classes,
    
    # Supervisor - Facilitators
    supervisor_facilitators_list,
    supervisor_facilitator_detail,
    supervisor_assign_facilitator_school,
    supervisor_assign_facilitator_class,
    
    # Supervisor - Reports
    supervisor_reports_dashboard,
    supervisor_feedback_analytics,
    supervisor_attendance_report_excel,
    
    # Supervisor - Settings
    supervisor_settings,
    
    # Supervisor - Calendar
    supervisor_calendar,
    supervisor_calendar_add_date,
    supervisor_calendar_edit_date,
    supervisor_calendar_delete_date,
    
    # Supervisor - Student Import
    supervisor_student_import,
    supervisor_download_sample_csv,
    
    # Supervisor - Sessions
    supervisor_sessions_list,
    supervisor_session_detail,
    supervisor_class_sessions,
    supervisor_school_sessions_analytics,
    get_classes_by_school,
)
from .supervisor_daily_profile_views import (
    supervisor_facilitator_daily_profile,
    supervisor_facilitator_daily_profile_api,
    admin_facilitator_daily_profile,
    admin_facilitator_daily_profile_api,
)
from .step_status_views import (
    # Step Status API
    save_step_status,
    get_step_status,
    clear_step_status,
)
from .views import (

    # Admin – students
    students_list, student_add, student_edit, student_delete, student_import,
    
    # Admin - Feedback & Analytics
    admin_feedback_dashboard, admin_student_feedback_list, admin_teacher_feedback_list, admin_feedback_analytics,

    # Sessions & attendance
    sessions_view,          # admin class sessions
    class_attendance,       # admin class attendance
    today_session,          # facilitator today session
    facilitator_class_attendance_only, # separate view for non-curriculum attendance
    start_session,          # facilitator start session
    mark_attendance,        # facilitator mark attendance
    mark_attendance_redirect, # robust redirect for attendance
    facilitator_fill_past_attendance, # new view for back-filling
    mark_facilitator_attendance,  # facilitator mark own attendance
    get_previous_day_attendance,  # API to fetch previous day attendance
    facilitator_classes,    # facilitator classes list
    facilitator_attendance, # facilitator attendance filtering
    admin_attendance_filter,
    planned_session_create,
    planned_session_edit,
    planned_session_delete,
    planned_session_import,
    initialize_class_sessions,
    delete_all_class_sessions,
    bulk_delete_sessions,
    bulk_initialize_school_sessions,
    bulk_delete_school_sessions,
    api_class_sessions_lazy,
    download_sample_csv,
    toggle_facilitator_assignment,
    delete_facilitator_assignment,


    
    # Guardian Management
    add_guardian,
    edit_guardian,
    delete_guardian,
    get_guardians,
 
    # Curriculum Navigator
    curriculum_navigator,
    hindi_curriculum_navigator,
    facilitator_curriculum_session,
    curriculum_content_api,
    facilitator_session_quick_nav,
    
    # Facilitator Management
    facilitator_schools,
    facilitator_school_detail,
    facilitator_students_list,
    facilitator_student_detail,
    facilitator_student_edit,
    
    # Admin Curriculum Session Management
    admin_curriculum_sessions_list,
    admin_curriculum_session_create,
    admin_curriculum_session_edit,
    admin_curriculum_session_delete,
    admin_curriculum_session_preview,
    admin_sessions_overview,
    ajax_school_classes_admin,
    
    # Performance API endpoints
    api_lazy_load_sessions,
    api_lazy_load_schools,
    api_dashboard_stats,
    api_dashboard_recent_sessions,
    api_dashboard_curriculum_updates,
    api_curriculum_sessions_filter,
    
    # Session Workflow (NEW)
    upload_lesson_plan,
    get_lesson_plan_uploads,
    delete_lesson_plan,
    view_lesson_plan,
    save_preparation_checklist,
    save_session_reward,
    save_session_tracking,
    save_session_feedback,
    api_session_state,
    api_session_complete,
    api_mark_conduct_complete,
    api_detect_grouped_session,
    save_student_feedback,
    save_teacher_feedback,
    get_feedback_status,
    
    # Create Grouping API Endpoints
    api_get_available_classes,
    api_get_grouped_sessions,
    api_create_grouping,
    api_get_group_details,
    api_apply_group_to_today,
    
    # AJAX endpoints
    ajax_facilitator_schools,
    ajax_school_classes,
    ajax_class_students,
    debug_sessions,
)
from . import facilitator_views
from . import supervisor_views
from . import facilitator_task_views
from .admin_session_views import (
    admin_session_templates_list,
    admin_session_template_create,
    admin_bulk_generate_sessions,
    admin_sequence_integrity_check,
    admin_session_analytics,
    ajax_class_session_status,
)

urlpatterns = [

    # ======================
    # PWA (Progressive Web App) - MUST BE FIRST
    # ======================
    # Manifest is now served as static file (static/manifest.json) via Nginx
    path("service-worker.js", service_worker, name="service_worker"),
    path("manifest.json", manifest, name="manifest"),
    path("offline-sync.js", offline_sync, name="offline_sync"),
    path("resource-prioritization.js", resource_prioritization, name="resource_prioritization"),
    path("offline/", offline, name="offline"),

    # ======================
    # Heartbeat (Keep-Alive)
    # ======================
    path("heartbeat/", heartbeat, name="heartbeat"),

    # ======================
    # Authentication
    # ======================
    path("", login_view, name="login"),
    path("login/", login_view, name="login_page"),
    path("logout/", logout_view, name="logout"),
    path("api/session/check/", session_check_view, name="session_check"),
    path("api/session/clear/", clear_session_view, name="session_clear"),

    # ======================
    # Dashboards (role based) - OPTIMIZED FOR PERFORMANCE
    # ======================
    path("admin/dashboard/", admin_dashboard_optimized, name="admin_dashboard"),
    path("admin/dashboard/stats/ajax/", admin_dashboard_stats_ajax, name="admin_dashboard_stats_ajax"),
    path("admin/dashboard/system-snapshot/ajax/", admin_system_snapshot_ajax, name="admin_system_snapshot_ajax"),

    path("supervisor/dashboard/", supervisor_dashboard_optimized, name="supervisor_dashboard"),
    path("facilitator/dashboard/", facilitator_dashboard_optimized, name="facilitator_dashboard"),
    
    # ======================
    # Supervisor URLs
    # ======================
    # Users
    path("supervisor/users/", supervisor_users_list, name="supervisor_users_list"),
    path("supervisor/users/create/", supervisor_user_create, name="supervisor_user_create"),
    path("supervisor/users/<uuid:user_id>/edit/", supervisor_user_edit, name="supervisor_user_edit"),
    path("supervisor/users/<uuid:user_id>/delete/", supervisor_user_delete, name="supervisor_user_delete"),
    path("supervisor/users/create-ajax/", supervisor_create_user_ajax, name="supervisor_create_user_ajax"),
    
    # Schools
    path("supervisor/schools/", supervisor_schools_list, name="supervisor_schools_list"),
    path("supervisor/schools/create/", supervisor_school_create, name="supervisor_school_create"),
    path("supervisor/schools/<uuid:school_id>/edit/", supervisor_school_edit, name="supervisor_school_edit"),
    path("supervisor/schools/<uuid:school_id>/", supervisor_school_detail, name="supervisor_school_detail"),
    path("supervisor/schools/<uuid:school_id>/delete/", supervisor_school_delete, name="supervisor_school_delete"),
    path("supervisor/schools/api/blocks/", get_blocks_by_district, name="get_blocks_by_district"),
    path("supervisor/schools/api/schools/", get_schools_by_block, name="get_schools_by_block"),
    
    # Clusters
    path("supervisor/clusters/", clusters_list, name="clusters_list"),
    path("supervisor/clusters/create/", cluster_create, name="cluster_create"),
    path("supervisor/clusters/<uuid:cluster_id>/edit/", cluster_edit, name="cluster_edit"),
    path("supervisor/clusters/<uuid:cluster_id>/", cluster_detail, name="cluster_detail"),
    path("supervisor/clusters/<uuid:cluster_id>/delete/", cluster_delete, name="cluster_delete"),
    
    # Classes
    path("supervisor/classes/", supervisor_classes_list, name="supervisor_classes_list"),
    path("supervisor/classes/bulk-add/", supervisor_bulk_add_classes, name="supervisor_bulk_add_classes"),
    path("supervisor/classes/bulk-create/", supervisor_class_bulk_create, name="supervisor_class_bulk_create"),
    path("supervisor/classes/create/", supervisor_class_create, name="supervisor_class_create"),
    path("supervisor/classes/<uuid:class_id>/edit/", supervisor_class_edit, name="supervisor_class_edit"),
    path("supervisor/classes/<uuid:class_id>/delete/", supervisor_class_delete, name="supervisor_class_delete"),
    
    # Facilitators
    path("supervisor/facilitators/", supervisor_facilitators_list, name="supervisor_facilitators_list"),
    path("supervisor/facilitators/<uuid:facilitator_id>/", supervisor_facilitator_detail, name="supervisor_facilitator_detail"),
    path("supervisor/facilitators/<uuid:facilitator_id>/daily-profile/", supervisor_facilitator_daily_profile, name="supervisor_facilitator_daily_profile"),
    path("supervisor/facilitators/<uuid:facilitator_id>/assign-schools/", supervisor_assign_facilitator_school, name="supervisor_assign_facilitator_school"),
    path("supervisor/facilitators/<uuid:facilitator_id>/assign-classes/", supervisor_assign_facilitator_class, name="supervisor_assign_facilitator_class"),
    
    # Reports
    path("supervisor/reports/", supervisor_reports_dashboard, name="supervisor_reports_dashboard"),
    path("supervisor/reports/feedback/", supervisor_feedback_analytics, name="supervisor_feedback_analytics"),
    path("supervisor/reports/attendance-excel/", supervisor_attendance_report_excel, name="supervisor_attendance_report_excel"),
    
    # Settings
    path("supervisor/settings/", supervisor_settings, name="supervisor_settings"),
    
    # Calendar Management (NEW)
    path("supervisor/calendar/", supervisor_calendar, name="supervisor_calendar"),
    path("supervisor/calendar/add-date/", supervisor_calendar_add_date, name="supervisor_calendar_add_date"),
    path("supervisor/calendar/edit-date/<uuid:date_id>/", supervisor_calendar_edit_date, name="supervisor_calendar_edit_date"),
    path("supervisor/calendar/delete-date/<uuid:date_id>/", supervisor_calendar_delete_date, name="supervisor_calendar_delete_date"),
    
    # Sessions Management (NEW)
    path("supervisor/sessions/", supervisor_sessions_list, name="supervisor_sessions_list"),
    path("supervisor/sessions/<uuid:session_id>/", supervisor_session_detail, name="supervisor_session_detail"),
    path("supervisor/class/<uuid:class_id>/sessions/", supervisor_class_sessions, name="supervisor_class_sessions"),
    path("supervisor/school/<uuid:school_id>/sessions-analytics/", supervisor_school_sessions_analytics, name="supervisor_school_sessions_analytics"),
    path("supervisor/get-classes-by-school/", get_classes_by_school, name="get_classes_by_school"),
    
    # Feedback & Analytics
    # ======================
    path("admin/feedback/", admin_feedback_dashboard, name="admin_feedback_dashboard"),
    path("admin/feedback/student/", admin_student_feedback_list, name="admin_student_feedback_list"),
    path("admin/feedback/teacher/", admin_teacher_feedback_list, name="admin_teacher_feedback_list"),
    path("admin/feedback/analytics/", admin_feedback_analytics, name="admin_feedback_analytics"),

    # ======================
    # Reports (ADMIN)
    # ======================

    # ======================
    # Users (ADMIN)
    # ======================
    path("admin/users/", users_view, name="users_view"),
    path("admin/users/add/", add_user, name="add_user"),
    path("admin/users/edit/<uuid:user_id>/", edit_user, name="edit_user"),
    path("admin/users/delete/<uuid:user_id>/", delete_user, name="delete_user"),
    path("admin/users/create-ajax/", create_user_ajax, name="create_user_ajax"),

    # ======================
    # Schools (ADMIN)
    # ======================
    path("admin/schools/", schools, name="schools"),
    path("admin/schools/add/", add_school, name="add_school"),
    path("admin/schools/edit/<uuid:school_id>/", edit_school, name="edit_school"),
    path("admin/schools/<uuid:school_id>/", school_detail, name="school_detail"),

    # ======================
    # Classes (ADMIN)
    # ======================
    path("admin/classes/", class_sections_list, name="class_sections_list"),
    path("admin/classes/bulk-add/", admin_bulk_add_classes, name="admin_bulk_add_classes"),
    path("admin/classes/bulk-create/", admin_bulk_create_classes, name="admin_bulk_create_classes"),
    path(
        "admin/schools/<uuid:school_id>/classes/",
        class_sections_list,
        name="class_sections_list_by_school"
    ),
    path(
        "admin/schools/<uuid:school_id>/classes/add/",
        class_section_add,
        name="class_section_add"
    ),
    path(
        "admin/classes/edit/<uuid:pk>/",
        edit_class_section,
        name="edit_class_section"
    ),
    path(
        "admin/classes/delete/<uuid:pk>/",
        class_section_delete,
        name="class_section_delete"
    ),

    # ======================
    # Students (ADMIN)
    # ======================
    path(
        "admin/schools/<uuid:school_id>/students/",
        students_list,
        name="students_list"
    ),
    path(
        "admin/schools/<uuid:school_id>/students/add/",
        student_add,
        name="student_add"
    ),
    
     path("admin/schools/<uuid:school_id>/delete/", delete_school, name="delete_school"),

    
    path(
        "admin/schools/<uuid:school_id>/students/<uuid:student_id>/edit/",
        student_edit,
        name="student_edit"
    ),
    path(
        "admin/schools/<uuid:school_id>/students/<uuid:student_id>/delete/",
        student_delete,
        name="student_delete"
    ),
    path(
        "admin/schools/<uuid:school_id>/students/import/",
        student_import,
        name="student_import"
    ),
    
    # ======================
    # Facilitator Assignment (ADMIN)
    # ======================
    path(
        "admin/classes/<uuid:class_section_id>/assign-facilitator/",
        assign_facilitator,
        name="assign_facilitator"
    ),
    path(
        "admin/schools/assign-facilitator/",
        assign_facilitator,
        name="assign_school_facilitator"
    ),
    path(
    "admin/attendance/",
    admin_attendance_filter,
    name="admin_attendance_filter"
),


    # ======================
    # Sessions & Attendance (ADMIN – READ ONLY)
    # ======================
    path(
        "admin/classes/<uuid:class_section_id>/sessions/",
        sessions_view,
        name="admin_class_sessions_list"
    ),
    path(
        "admin/classes/<uuid:class_section_id>/attendance/",
        class_attendance,
        name="class_attendance"
    ),
    path(
    "facilitator/classes/",
    facilitator_classes,
    name="facilitator_classes"
),
    path(
        "admin/sessions/",
        admin_sessions_filter,
        name="admin_sessions_filter"
    ),
path(
    "admin/sessions/classes/",
    admin_sessions_filter,
    name="admin_class_sessions_filter"
),





    # ======================
    # Facilitator Flow
    # ======================
    path(
        "facilitator/class/<uuid:class_section_id>/today/",
        today_session,
        name="facilitator_class_today_session"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/attendance-only/",
        facilitator_class_attendance_only,
        name="facilitator_class_attendance_only"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/office-work/",
        facilitator_views.facilitator_class_office_work,
        name="facilitator_class_office_work"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/debug/",
        debug_sessions,
        name="debug_sessions"
    ),
    path(
        "facilitator/session/start/<uuid:planned_session_id>/",
        start_session,
        name="start_session"
    ),
    path(
        "facilitator/session/<uuid:actual_session_id>/attendance/",
        mark_attendance,
        name="mark_attendance"
    ),
    path(
        "api/facilitator/session/<uuid:actual_session_id>/previous-attendance/",
        get_previous_day_attendance,
        name="get_previous_day_attendance"
    ),
    path(
        "facilitator/planned-session/<uuid:planned_session_id>/attendance/",
        mark_attendance_redirect,
        name="mark_attendance_redirect"
    ),
    path(
        "facilitator/session/<uuid:actual_session_id>/facilitator-attendance/",
        mark_facilitator_attendance,
        name="mark_facilitator_attendance"
    ),
    path(
        "facilitator/attendance/",
        facilitator_attendance,
        name="facilitator_attendance"
    ),
    path(
        "facilitator/fill-attendance/<uuid:class_section_id>/<str:date_str>/",
        facilitator_fill_past_attendance,
        name="facilitator_fill_past_attendance"
    ),
    
    # AJAX endpoints for attendance filtering
    path(
        "api/facilitator/schools/",
        ajax_facilitator_schools,
        name="ajax_facilitator_schools"
    ),
    path(
        "api/facilitator/classes/",
        ajax_school_classes,
        name="ajax_school_classes"
    ),
    path(
        "api/facilitator/students/",
        ajax_class_students,
        name="ajax_class_students"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/planned-session/create/",
        planned_session_create,
        name="planned_session_create"
    ),
   path(
    "admin/planned-session/<uuid:session_id>/edit/",
    planned_session_edit,
    name="planned_session_edit"
),
path(
    "admin/planned-session/<uuid:session_id>/delete/",
    planned_session_delete,
    name="planned_session_delete"
),
path(
    "admin/classes/<uuid:class_section_id>/planned-sessions/import/",
    planned_session_import,
    name="planned_session_import"
),
    path(
        "admin/schools/<uuid:school_id>/bulk-delete-sessions/",
        bulk_delete_school_sessions,
        name="bulk_delete_school_sessions"
    ),
    path(
        "admin/class/<uuid:class_section_id>/sessions/initialize/",
        initialize_class_sessions,
        name="initialize_class_sessions"
    ),
path(
    "admin/classes/<uuid:class_section_id>/sessions/delete-all/",
    delete_all_class_sessions,
    name="delete_all_class_sessions"
),
path(
    "admin/schools/<uuid:school_id>/bulk-initialize-sessions/",
    bulk_initialize_school_sessions,
    name="bulk_initialize_school_sessions"
),
path(
    "api/classes/<uuid:class_section_id>/sessions/",
    api_class_sessions_lazy,
    name="api_class_sessions_lazy"
),
path(
    "admin/classes/<uuid:class_section_id>/planned-sessions/bulk-delete/",
    bulk_delete_sessions,
    name="bulk_delete_sessions"
),
    path(
        "admin/download-sample-csv/",
        download_sample_csv,
        name="download_sample_csv"
    ),
path(
    "admin/facilitator-assignment/<uuid:assignment_id>/toggle/",
    toggle_facilitator_assignment,
    name="toggle_facilitator_assignment"
),
path(
    "admin/facilitator-assignment/<uuid:assignment_id>/delete/",
    delete_facilitator_assignment,
    name="delete_facilitator_assignment"
),


    # ======================
    # No Permission
    # ======================
    path("no_permission/", no_permission, name="no_permission"),
    
    # ======================
    # Admin Settings
    # ======================
    path("admin/settings/", admin_settings, name="admin_settings"),
    
    # Admin-accessible Supervisor views (admin wrappers)
    path("admin/facilitators/", admin_view_facilitators, name="admin_view_facilitators"),
    path("admin/facilitators/<uuid:facilitator_id>/", admin_facilitator_detail, name="admin_facilitator_detail"),
    path("admin/facilitators/<uuid:facilitator_id>/daily-profile/", admin_facilitator_daily_profile, name="admin_facilitator_daily_profile"),
    path("admin/reports/dashboard/", admin_reports_dashboard, name="admin_reports_dashboard"),
    path("admin/sessions/all/", admin_sessions_list, name="admin_sessions_list"),
    path("admin/sessions/<uuid:session_id>/", admin_session_detail, name="admin_session_detail"),
    path("admin/class/<uuid:class_id>/sessions/", admin_class_sessions, name="admin_class_sessions"),
    path("admin/calendar/", admin_view_calendar, name="admin_view_calendar"),
    path("admin/calendar/add-date/", admin_calendar_add_date, name="admin_calendar_add_date"),
    path("admin/calendar/edit-date/<uuid:date_id>/", admin_calendar_edit_date, name="admin_calendar_edit_date"),
    path("admin/calendar/delete-date/<uuid:date_id>/", admin_calendar_delete_date, name="admin_calendar_delete_date"),
    path("api/admin/notifications/", admin_get_notifications, name="admin_get_notifications"),
    path("api/admin/daily-profile/<uuid:facilitator_id>/", admin_facilitator_daily_profile_api, name="admin_facilitator_daily_profile_api"),
    
    # ======================
    # Curriculum Navigator
    # ======================
    path("curriculum/", curriculum_navigator, name="curriculum_navigator"),
    path("curriculum/hindi/", hindi_curriculum_navigator, name="hindi_curriculum_navigator"),
    path(
        "facilitator/class/<uuid:class_section_id>/curriculum/",
        facilitator_curriculum_session,
        name="facilitator_curriculum_session"
    ),
    path("api/curriculum/content/", curriculum_content_api, name="curriculum_content_api"),
    path(
        "api/facilitator/class/<uuid:class_section_id>/sessions/",
        facilitator_session_quick_nav,
        name="facilitator_session_quick_nav"
    ),
    
    # ======================
    # Facilitator Management
    # ======================
    path("facilitator/schools/", facilitator_schools, name="facilitator_schools"),
    path(
        "facilitator/school/<uuid:school_id>/",
        facilitator_school_detail,
        name="facilitator_school_detail_fbv"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/students/",
        facilitator_students_list,
        name="facilitator_class_students_list"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/student/<uuid:student_id>/",
        facilitator_student_detail,
        name="facilitator_student_detail_fbv"
    ),
    path(
        "facilitator/class/<uuid:class_section_id>/student/<uuid:student_id>/edit/",
        facilitator_student_edit,
        name="facilitator_student_edit_fbv"
    ),
    
    # Guardian Management Routes
    path(
        "api/facilitator/student/<uuid:student_id>/guardian/add/",
        add_guardian,
        name="add_guardian"
    ),
    path(
        "api/facilitator/guardian/<uuid:guardian_id>/edit/",
        edit_guardian,
        name="edit_guardian"
    ),
    path(
        "api/facilitator/guardian/<uuid:guardian_id>/delete/",
        delete_guardian,
        name="delete_guardian"
    ),
    path(
        "api/facilitator/student/<uuid:student_id>/guardians/",
        get_guardians,
        name="get_guardians"
    ),
    
    # ======================
    # AJAX endpoints
    # ======================
    path("api/school-classes/", ajax_school_classes_admin, name="ajax_school_classes_admin"),
    path("api/all-schools/", get_all_schools, name="get_all_schools"),
    
    # ======================
    # Admin Sessions Overview
    # ======================
    path("admin/sessions/overview/", admin_sessions_overview, name="admin_sessions_overview"),
    
    # ======================
    # Admin Curriculum Session Management
    # ======================
    path("admin/curriculum-sessions/", admin_curriculum_sessions_list, name="admin_curriculum_sessions_list"),
    path("admin/curriculum-sessions/create/", admin_curriculum_session_create, name="admin_curriculum_session_create"),
    path("admin/curriculum-sessions/<uuid:session_id>/edit/", admin_curriculum_session_edit, name="admin_curriculum_session_edit"),
    path("admin/curriculum-sessions/<uuid:session_id>/delete/", admin_curriculum_session_delete, name="admin_curriculum_session_delete"),
    path("admin/curriculum-sessions/<uuid:session_id>/preview/", admin_curriculum_session_preview, name="admin_curriculum_session_preview"),
    
    # ======================
    # Class Session Initialization
    # ======================
    path("admin/initialize-class-sessions-global/", initialize_class_sessions, name="initialize_class_sessions_global"),
    
    # ======================
    # Facilitator Student Management (New)
    # ======================
    path("facilitator/my-schools/", facilitator_views.FacilitatorSchoolListView.as_view(), name="facilitator_schools_list"),
    path("facilitator/my-schools/<uuid:pk>/", facilitator_views.FacilitatorSchoolDetailView.as_view(), name="facilitator_school_detail"),
    path("facilitator/students/", facilitator_views.FacilitatorStudentListView.as_view(), name="facilitator_students_list"),
    path("facilitator/students/create/", facilitator_views.FacilitatorStudentCreateView.as_view(), name="facilitator_student_create"),
    path("facilitator/students/<uuid:pk>/edit/", facilitator_views.FacilitatorStudentUpdateView.as_view(), name="facilitator_student_edit"),
    path("facilitator/students/<uuid:student_id>/detail/", facilitator_views.facilitator_student_detail, name="facilitator_student_detail"),
    path("facilitator/ajax/school-classes/", facilitator_views.facilitator_ajax_school_classes, name="facilitator_ajax_school_classes"),
    path("facilitator/ajax/student/<uuid:student_id>/growth-analysis/", facilitator_views.facilitator_student_growth_analysis_ajax, name="facilitator_student_growth_analysis_ajax"),
    path("facilitator/debug/schools/", facilitator_views.facilitator_debug_schools, name="facilitator_debug_schools"),
    path("facilitator/test/access/", facilitator_views.facilitator_test_access, name="facilitator_test_access"),
    
    # ======================
    # Facilitator Calendar & Today Session (NEW)
    # ======================
    path("facilitator/today-session/", facilitator_views.facilitator_today_session, name="facilitator_today_session"),
    path("facilitator/today-session-calendar/", facilitator_views.facilitator_today_session_calendar, name="facilitator_today_session_calendar"),
    path("facilitator/office-work/", facilitator_views.facilitator_office_work, name="facilitator_office_work"),
    path("facilitator/grouped-session/", facilitator_views.facilitator_grouped_session, name="facilitator_grouped_session"),
    path("facilitator/mark-office-work/", facilitator_views.facilitator_mark_office_work_attendance, name="facilitator_mark_office_work"),
    path("facilitator/my-attendance/", facilitator_views.facilitator_my_attendance, name="facilitator_my_attendance"),
    path("facilitator/grouping-options/<uuid:class_section_id>/", facilitator_views.get_grouping_options, name="get_grouping_options"),
    path("facilitator/apply-grouping/", facilitator_views.apply_grouping, name="apply_grouping"),
    path("facilitator/clear-grouping/", facilitator_views.clear_grouping, name="clear_grouping"),
    path("facilitator/update-session-status/", facilitator_views.update_session_status, name="update_session_status"),
    path("facilitator/settings/", facilitator_views.facilitator_settings, name="facilitator_settings"),
    path("facilitator/send-class-unavailable-notification/", facilitator_views.send_class_unavailable_notification, name="send_class_unavailable_notification"),
    
    # ======================
    # Facilitator Task (NEW)
    # ======================
    path("facilitator/task/<uuid:actual_session_id>/", facilitator_task_views.facilitator_task_step, name="facilitator_task_step"),
    path("facilitator/task/<uuid:actual_session_id>/upload-photo/", facilitator_task_views.facilitator_task_upload_photo, name="facilitator_task_upload_photo"),
    path("facilitator/task/<uuid:actual_session_id>/upload-video/", facilitator_task_views.facilitator_task_upload_video, name="facilitator_task_upload_video"),
    path("facilitator/task/<uuid:actual_session_id>/facebook-link/", facilitator_task_views.facilitator_task_facebook_link, name="facilitator_task_facebook_link"),
    # Upload without session ID (for pre-session uploads)
    path("facilitator/task/upload-photo/", facilitator_task_views.facilitator_task_upload_photo, name="facilitator_task_upload_photo_no_session"),
    path("facilitator/task/upload-video/", facilitator_task_views.facilitator_task_upload_video, name="facilitator_task_upload_video_no_session"),
    path("facilitator/task/facebook-link/", facilitator_task_views.facilitator_task_facebook_link, name="facilitator_task_facebook_link_no_session"),
    path("facilitator/task/facebook-links/", facilitator_task_views.facilitator_task_facebook_links, name="facilitator_task_facebook_links"),
    path("facilitator/task/<uuid:task_id>/delete/", facilitator_task_views.facilitator_task_delete, name="facilitator_task_delete"),
    path("facilitator/task/<uuid:actual_session_id>/complete/", facilitator_task_views.facilitator_task_complete, name="facilitator_task_complete"),
    
    # ======================
    # Student Performance (NEW)
    # ======================
    path("facilitator/performance/", facilitator_views.facilitator_performance_class_select, name="facilitator_performance_class_select"),
    path("facilitator/class/<uuid:class_section_id>/performance/", facilitator_views.student_performance_list, name="student_performance_list"),
    path("facilitator/class/<uuid:class_section_id>/performance/<uuid:student_id>/", facilitator_views.student_performance_detail, name="student_performance_detail"),
    path("facilitator/class/<uuid:class_section_id>/performance/<uuid:student_id>/save/", facilitator_views.student_performance_save, name="student_performance_save"),
    path("facilitator/class/<uuid:class_section_id>/performance/cutoff/", facilitator_views.performance_cutoff_settings, name="performance_cutoff_settings"),
    
    # ======================
    # Bulk Student Import (NEW)
        # ======================
    # Bulk Student Import (NEW)
    # ======================
    path("facilitator/class/<uuid:class_section_id>/students/import/", facilitator_views.facilitator_student_import, name="facilitator_student_import"),
    path("facilitator/students/download-sample/", facilitator_views.facilitator_download_sample_csv, name="facilitator_download_sample_csv"),
    path("supervisor/school/<uuid:school_id>/students/import/", supervisor_views.supervisor_student_import, name="supervisor_student_import"),
    path("supervisor/students/download-sample/", supervisor_views.supervisor_download_sample_csv, name="supervisor_download_sample_csv"),
    
    # ======================
    # Admin Session Sequence Management (NEW)
    # ======================
    path("admin/session-templates/", admin_session_templates_list, name="admin_session_templates_list"),
    path("admin/session-templates/create/", admin_session_template_create, name="admin_session_template_create"),
    path("admin/sessions/bulk-generate/", admin_bulk_generate_sessions, name="admin_bulk_generate_sessions"),
    path("admin/sessions/integrity-check/", admin_sequence_integrity_check, name="admin_sequence_integrity_check"),
    path("admin/sessions/analytics/", admin_session_analytics, name="admin_session_analytics"),
    path("api/admin/class-session-status/", ajax_class_session_status, name="ajax_class_session_status"),
    
    # ======================
    # Session Workflow (NEW)
    # ======================
    path("api/get-lesson-plan-uploads/", get_lesson_plan_uploads, name="get_lesson_plan_uploads"),
    path("api/upload-lesson-plan/", upload_lesson_plan, name="upload_lesson_plan"),
    path("api/delete-lesson-plan/<str:upload_id>/", delete_lesson_plan, name="delete_lesson_plan"),
    path("api/view-lesson-plan/<str:upload_id>/", view_lesson_plan, name="view_lesson_plan"),
    path("api/save-preparation-checklist/", save_preparation_checklist, name="save_preparation_checklist"),
    path("api/save-session-reward/", save_session_reward, name="save_session_reward"),
    path("api/save-session-tracking/", save_session_tracking, name="save_session_tracking"),
    path("api/mark-conduct-complete/", api_mark_conduct_complete, name="api_mark_conduct_complete"),
    path("api/save-session-feedback/", save_session_feedback, name="save_session_feedback"),
    path("api/session-state/", api_session_state, name="api_session_state"),
    path("api/session/<uuid:actual_session_id>/complete/", api_session_complete, name="api_session_complete"),
    path("api/detect-grouped-session/", api_detect_grouped_session, name="api_detect_grouped_session"),
    path("api/save-student-feedback/", save_student_feedback, name="save_student_feedback"),
    path("api/save-teacher-feedback/", save_teacher_feedback, name="save_teacher_feedback"),
    path("api/get-feedback-status/", get_feedback_status, name="get_feedback_status"),
    
    # Step Status API (NEW - for grouped session step tracking)
    path("api/step-status/save/", save_step_status, name="save_step_status"),
    path("api/step-status/get/", get_step_status, name="get_step_status"),
    path("api/step-status/clear/", clear_step_status, name="clear_step_status"),
    
    # Create Grouping API Endpoints
    path("api/get-available-classes/", api_get_available_classes, name="api_get_available_classes"),
    path("api/get-grouped-sessions/", api_get_grouped_sessions, name="api_get_grouped_sessions"),
    path("api/create-grouping/", api_create_grouping, name="api_create_grouping"),
    path("api/get-group-details/<uuid:group_id>/", api_get_group_details, name="api_get_group_details"),
    path("api/apply-group-to-today/", api_apply_group_to_today, name="api_apply_group_to_today"),
    
    # ======================
    # Performance API Endpoints
    # ======================
    path("api/lazy-load/sessions/", api_lazy_load_sessions, name="api_lazy_load_sessions"),
    path("api/lazy-load/schools/", api_lazy_load_schools, name="api_lazy_load_schools"),
    path("api/dashboard/stats/", api_dashboard_stats, name="api_dashboard_stats"),
    path("api/dashboard/recent-sessions/", api_dashboard_recent_sessions, name="api_dashboard_recent_sessions"),
    path("api/dashboard/curriculum-updates/", api_dashboard_curriculum_updates, name="api_dashboard_curriculum_updates"),
    path("api/curriculum-sessions/filter/", api_curriculum_sessions_filter, name="api_curriculum_sessions_filter"),
    
    # ======================
    # Supervisor Daily Profile API
    # ======================
    path("api/supervisor/facilitator/<uuid:facilitator_id>/daily-profile/", supervisor_facilitator_daily_profile_api, name="supervisor_facilitator_daily_profile_api"),
    path("api/supervisor/notifications/", supervisor_views.supervisor_get_notifications, name="supervisor_get_notifications"),
    
    # ======================
    # Reports System
    # ======================
    path("", include('class.urls_reports')),
]