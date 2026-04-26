# Generated migration for student performance models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0025a_facilitatortask'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentPerformance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('subject', models.CharField(max_length=100)),
                ('score', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('class_section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='class.classsection')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='class.student')),
            ],
        ),
    ]
