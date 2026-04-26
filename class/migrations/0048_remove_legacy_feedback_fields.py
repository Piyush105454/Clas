# Generated migration to remove legacy fields from SessionFeedback table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0047_add_pending_session_status'),
    ]

    operations = [
        # Remove legacy fields that were supposed to be removed but still exist in database
        migrations.RunSQL(
            sql="ALTER TABLE class_sessionfeedback DROP COLUMN IF EXISTS student_engagement_level;",
            reverse_sql="ALTER TABLE class_sessionfeedback ADD COLUMN student_engagement_level INTEGER;",
            state_operations=[],
        ),
        migrations.RunSQL(
            sql="ALTER TABLE class_sessionfeedback DROP COLUMN IF EXISTS student_understanding_level;",
            reverse_sql="ALTER TABLE class_sessionfeedback ADD COLUMN student_understanding_level INTEGER;",
            state_operations=[],
        ),
        migrations.RunSQL(
            sql="ALTER TABLE class_sessionfeedback DROP COLUMN IF EXISTS challenging_topics;",
            reverse_sql="ALTER TABLE class_sessionfeedback ADD COLUMN challenging_topics TEXT;",
            state_operations=[],
        ),
        migrations.RunSQL(
            sql="ALTER TABLE class_sessionfeedback DROP COLUMN IF EXISTS student_questions;",
            reverse_sql="ALTER TABLE class_sessionfeedback ADD COLUMN student_questions TEXT;",
            state_operations=[],
        ),
    ]
