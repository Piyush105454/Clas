# Generated migration for grouped classes support

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0027_remove_actualsession_as_date_idx_and_more'),
    ]

    operations = [
        # Add ManyToMany field for grouped classes
        migrations.AddField(
            model_name='calendardate',
            name='class_sections',
            field=models.ManyToManyField(blank=True, related_name='calendar_sessions', to='class.classsection'),
        ),
        # Make class_section nullable for backward compatibility
        migrations.AlterField(
            model_name='calendardate',
            name='class_section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='calendar_sessions_legacy', to='class.classsection'),
        ),
        # Remove unique_together constraint
        migrations.AlterUniqueTogether(
            name='calendardate',
            unique_together=set(),
        ),
    ]
