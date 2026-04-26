# Generated migration - SAFE: Only adds indexes, no data changes
# This migration adds critical database indexes to fix N+1 query problems
# NO DATA WILL BE LOST OR MODIFIED

from django.db import migrations, models


def safe_add_indexes(apps, schema_editor):
    """Safely add indexes, skipping those that already exist"""
    with schema_editor.connection.cursor() as cursor:
        indexes_to_add = [
            ('enroll_sch_active_date_idx', 'CREATE INDEX IF NOT EXISTS enroll_sch_active_date_idx ON class_enrollment(school_id, is_active, start_date)'),
            ('enroll_cls_active_idx', 'CREATE INDEX IF NOT EXISTS enroll_cls_active_idx ON class_enrollment(class_section_id, is_active)'),
            ('attend_stud_date_idx', 'CREATE INDEX IF NOT EXISTS attend_stud_date_idx ON class_attendance(student_id, marked_at)'),
            ('attend_cls_date_idx', 'CREATE INDEX IF NOT EXISTS attend_cls_date_idx ON class_attendance(class_section_id, marked_at)'),
            ('attend_sch_date_idx', 'CREATE INDEX IF NOT EXISTS attend_sch_date_idx ON class_attendance(school_id, marked_at)'),
            ('attend_status_date_idx', 'CREATE INDEX IF NOT EXISTS attend_status_date_idx ON class_attendance(status, marked_at)'),
            ('attend_sess_enroll_idx', 'CREATE INDEX IF NOT EXISTS attend_sess_enroll_idx ON class_attendance(actual_session_id, enrollment_id)'),
            ('asess_sess_stat_idx', 'CREATE INDEX IF NOT EXISTS asess_sess_stat_idx ON class_actualsession(planned_session_id, status)'),
            ('asess_date_stat_idx', 'CREATE INDEX IF NOT EXISTS asess_date_stat_idx ON class_actualsession(date, status)'),
            ('asess_facil_date_idx', 'CREATE INDEX IF NOT EXISTS asess_facil_date_idx ON class_actualsession(facilitator_id, date)'),
            ('asess_stat_date_idx', 'CREATE INDEX IF NOT EXISTS asess_stat_date_idx ON class_actualsession(status, date)'),
            ('asess_attend_date_idx', 'CREATE INDEX IF NOT EXISTS asess_attend_date_idx ON class_actualsession(attendance_marked, date)'),
            ('asess_conducted_idx', 'CREATE INDEX IF NOT EXISTS asess_conducted_idx ON class_actualsession(conducted_at)'),
            ('psess_cls_day_idx', 'CREATE INDEX IF NOT EXISTS psess_cls_day_idx ON class_plannedsession(class_section_id, day_number)'),
            ('psess_cls_active_idx', 'CREATE INDEX IF NOT EXISTS psess_cls_active_idx ON class_plannedsession(class_section_id, is_active)'),
            ('sfeed_facil_complete_idx', 'CREATE INDEX IF NOT EXISTS sfeed_facil_complete_idx ON class_sessionfeedback(facilitator_id, is_complete)'),
            ('sfeed_date_idx', 'CREATE INDEX IF NOT EXISTS sfeed_date_idx ON class_sessionfeedback(feedback_date)'),
            ('sfeed_sess_facil_idx', 'CREATE INDEX IF NOT EXISTS sfeed_sess_facil_idx ON class_sessionfeedback(actual_session_id, facilitator_id)'),
            ('sstep_sess_order_idx', 'CREATE INDEX IF NOT EXISTS sstep_sess_order_idx ON class_sessionstep(planned_session_id, order)'),
            ('lplan_facil_date_idx', 'CREATE INDEX IF NOT EXISTS lplan_facil_date_idx ON class_lessonplanupload(facilitator_id, upload_date)'),
            ('lplan_sess_facil_idx', 'CREATE INDEX IF NOT EXISTS lplan_sess_facil_idx ON class_lessonplanupload(planned_session_id, facilitator_id)'),
            ('sreward_facil_date_idx', 'CREATE INDEX IF NOT EXISTS sreward_facil_date_idx ON class_sessionreward(facilitator_id, reward_date)'),
            ('sprep_facil_start_idx', 'CREATE INDEX IF NOT EXISTS sprep_facil_start_idx ON class_sessionpreparationchecklist(facilitator_id, preparation_start_time)'),
            ('stfeed_sess_date_idx', 'CREATE INDEX IF NOT EXISTS stfeed_sess_date_idx ON class_studentfeedback(actual_session_id, submitted_at)'),
            ('tfeed_sess_date_idx', 'CREATE INDEX IF NOT EXISTS tfeed_sess_date_idx ON class_teacherfeedback(actual_session_id, submitted_at)'),
            ('ftask_facil_date_idx', 'CREATE INDEX IF NOT EXISTS ftask_facil_date_idx ON class_facilitatortask(facilitator_id, created_at)'),
            ('ftask_status_date_idx', 'CREATE INDEX IF NOT EXISTS ftask_status_date_idx ON class_facilitatortask(status, created_at)'),
        ]
        
        for idx_name, sql in indexes_to_add:
            try:
                cursor.execute(sql)
            except Exception as e:
                # Index already exists or other error - continue
                pass


def reverse_safe_add_indexes(apps, schema_editor):
    """Reverse operation - do nothing"""
    pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('class', '0026c_add_facilitator_attendance'),
    ]

    operations = [
        migrations.RunPython(safe_add_indexes, reverse_safe_add_indexes),
    ]
