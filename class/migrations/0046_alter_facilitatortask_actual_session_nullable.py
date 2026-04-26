# Migration to fix FacilitatorTask.actual_session NOT NULL constraint

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0045_performancecutoff_studentperformancesummary_subject_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facilitatortask',
            name='actual_session',
            field=models.ForeignKey(blank=True, help_text='Optional - task can be created without a session', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='facilitator_tasks', to='class.actualsession'),
        ),
    ]
