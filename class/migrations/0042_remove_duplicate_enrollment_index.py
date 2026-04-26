# Generated migration to remove duplicate indexes

from django.db import migrations, models


def remove_duplicate_indexes(apps, schema_editor):
    """Safely remove all duplicate indexes that already exist in database"""
    duplicate_indexes = [
        'enroll_stud_active_idx',
        'attend_stud_date_idx',
        'attend_cls_date_idx',
        'attend_sch_date_idx',
        'attend_status_date_idx',
        'asess_sess_stat_idx',
        'asess_date_stat_idx',
        'asess_facil_date_idx',
        'asess_stat_date_idx',
    ]
    
    with schema_editor.connection.cursor() as cursor:
        for index_name in duplicate_indexes:
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
            except Exception as e:
                # Silently ignore if index doesn't exist
                pass


def reverse_remove_indexes(apps, schema_editor):
    """Reverse operation - do nothing"""
    pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('class', '0041_update_plannedsession_constraints'),
    ]

    operations = [
        # Safely remove all duplicate indexes using raw SQL
        migrations.RunPython(remove_duplicate_indexes, reverse_remove_indexes),
    ]
