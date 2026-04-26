# Generated migration for grouped session support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0027_calendardate_grouped_classes'),
    ]

    operations = [
        migrations.AddField(
            model_name='plannedsession',
            name='grouped_session_id',
            field=models.UUIDField(blank=True, help_text='If set, this session is part of a grouped session. All classes with same grouped_session_id share this session.', null=True),
        ),
        migrations.AddIndex(
            model_name='plannedsession',
            index=models.Index(fields=['grouped_session_id'], name='class_plann_grouped_idx'),
        ),
    ]
