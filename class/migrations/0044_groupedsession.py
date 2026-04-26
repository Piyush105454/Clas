# Generated migration for GroupedSession model only

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0043_merge_20260202_final'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupedSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('grouped_session_id', models.UUIDField(help_text='Unique ID that links all PlannedSessions in this group', unique=True)),
                ('name', models.CharField(blank=True, help_text="Optional name for this grouped session (e.g., 'Section A & B Combined')", max_length=255)),
                ('description', models.TextField(blank=True, help_text='Optional description of why these classes are grouped')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='groupedsession',
            name='class_sections',
            field=models.ManyToManyField(help_text='All classes that share the same 150 sessions', related_name='grouped_sessions', to='class.classsection'),
        ),
        migrations.AddIndex(
            model_name='groupedsession',
            index=models.Index(fields=['grouped_session_id'], name='class_group_grouped_idx'),
        ),
    ]
