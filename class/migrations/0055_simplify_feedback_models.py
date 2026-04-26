# Generated migration to simplify feedback models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0054_studentguardian'),
    ]

    operations = [
        # Add new fields for StudentFeedback - first as nullable
        migrations.AddField(
            model_name='studentfeedback',
            name='student',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='session_feedbacks',
                to='class.student',
                help_text='Student being given feedback'
            ),
        ),
        migrations.AddField(
            model_name='studentfeedback',
            name='description',
            field=models.TextField(
                default='',
                help_text='Feedback notes for the student'
            ),
            preserve_default=False,
        ),
        
        # Update unique_together for StudentFeedback
        migrations.AlterUniqueTogether(
            name='studentfeedback',
            unique_together={('actual_session', 'student')},
        ),
    ]
