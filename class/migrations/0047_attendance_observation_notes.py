# Generated migration for adding observation notes to Attendance model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0046_alter_facilitatortask_actual_session_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='visible_change_notes',
            field=models.TextField(blank=True, null=True, help_text='Observable physical or behavioral changes in student'),
        ),
        migrations.AddField(
            model_name='attendance',
            name='invisible_change_notes',
            field=models.TextField(blank=True, null=True, help_text='Internal or cognitive changes not immediately visible'),
        ),
    ]
