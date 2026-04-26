# Generated migration for adding database indexes to improve curriculum session query performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0001_initial'),  # Replace with your actual last migration
    ]

    operations = [
        migrations.RunSQL(
            # Add composite indexes for common query patterns
            sql=[
                # Index for language + day_number filtering (most common query)
                "CREATE INDEX IF NOT EXISTS idx_curriculum_session_lang_day ON class_curriculumsession(language, day_number);",
                
                # Index for language + status filtering
                "CREATE INDEX IF NOT EXISTS idx_curriculum_session_lang_status ON class_curriculumsession(language, status);",
                
                # Index for day_number range queries
                "CREATE INDEX IF NOT EXISTS idx_curriculum_session_day_range ON class_curriculumsession(day_number);",
                
                # Index for updated_at for recent updates queries
                "CREATE INDEX IF NOT EXISTS idx_curriculum_session_updated ON class_curriculumsession(updated_at DESC);",
                
                # Index for created_by for filtering by creator
                "CREATE INDEX IF NOT EXISTS idx_curriculum_session_creator ON class_curriculumsession(created_by_id);",
                
                # Composite index for language + day_number + status (covers most filter combinations)
                "CREATE INDEX IF NOT EXISTS idx_curriculum_session_lang_day_status ON class_curriculumsession(language, day_number, status);",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS idx_curriculum_session_lang_day;",
                "DROP INDEX IF EXISTS idx_curriculum_session_lang_status;",
                "DROP INDEX IF EXISTS idx_curriculum_session_day_range;",
                "DROP INDEX IF EXISTS idx_curriculum_session_updated;",
                "DROP INDEX IF EXISTS idx_curriculum_session_creator;",
                "DROP INDEX IF EXISTS idx_curriculum_session_lang_day_status;",
            ]
        ),
    ]