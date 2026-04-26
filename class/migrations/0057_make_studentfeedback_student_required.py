# Migration to make student field required and clean up null values

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0056_merge_20260308_2056'),
    ]

    operations = [
        # Delete any StudentFeedback records with null student (orphaned records)
        migrations.RunPython(
            code=lambda apps, schema_editor: apps.get_model('class', 'StudentFeedback').objects.filter(student__isnull=True).delete(),
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Now make the student field non-nullable
        migrations.AlterField(
            model_name='studentfeedback',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='session_feedbacks',
                to='class.student',
                help_text='Student being given feedback'
            ),
        ),
    ]
