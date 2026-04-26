# Generated migration to remove real-time session tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0026a_student_performance'),
    ]

    operations = [
        # Remove real-time tracking fields from SessionFeedback
        migrations.RemoveField(
            model_name='sessionfeedback',
            name='student_engagement_level',
        ),
        migrations.RemoveField(
            model_name='sessionfeedback',
            name='student_understanding_level',
        ),
        migrations.RemoveField(
            model_name='sessionfeedback',
            name='challenging_topics',
        ),
        migrations.RemoveField(
            model_name='sessionfeedback',
            name='student_questions',
        ),
    ]
