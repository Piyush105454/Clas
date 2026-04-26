# Generated migration for facilitator attendance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0026b_remove_realtime_tracking_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='actualsession',
            name='facilitator_attendance',
            field=models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave')], default='present', max_length=20),
        ),
    ]
