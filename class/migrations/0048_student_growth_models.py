# Generated migration for Student Growth Intelligence System models

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('class', '0047_attendance_observation_notes'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentQuiz',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quiz_date', models.DateField(help_text='Date when quiz was conducted')),
                ('quiz_month', models.CharField(db_index=True, help_text='Month in YYYY-MM format for easy filtering', max_length=7)),
                ('score', models.PositiveIntegerField(help_text='Quiz score (0-100)')),
                ('total_marks', models.PositiveIntegerField(help_text='Total marks for the quiz')),
                ('questions_attempted', models.PositiveIntegerField(help_text='Number of questions attempted')),
                ('correct_answers', models.PositiveIntegerField(help_text='Number of correct answers')),
                ('notes', models.TextField(blank=True, help_text='Optional notes about the quiz performance', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('enrollment', models.ForeignKey(help_text='Student enrollment reference', on_delete=django.db.models.deletion.CASCADE, related_name='quizzes', to='class.enrollment')),
            ],
            options={
                'verbose_name': 'Student Quiz',
                'verbose_name_plural': 'Student Quizzes',
                'ordering': ['quiz_date'],
            },
        ),
        migrations.CreateModel(
            name='StudentGrowthAnalysis',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('analysis_date', models.DateField(auto_now=True, help_text='Date when analysis was performed')),
                ('growth_score', models.FloatField(help_text='Overall growth score (0-100)')),
                ('attendance_consistency', models.FloatField(help_text='Attendance consistency score (0-100)')),
                ('quiz_improvement_rate', models.FloatField(help_text='Quiz improvement rate as percentage')),
                ('text_complexity_growth', models.FloatField(help_text='Text complexity growth percentage')),
                ('engagement_level', models.CharField(choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], help_text='Overall engagement level', max_length=20)),
                ('risk_level', models.CharField(choices=[('low', 'Low Risk'), ('medium', 'Medium Risk'), ('high', 'High Risk')], db_index=True, help_text='Risk level for intervention', max_length=20)),
                ('student_cluster', models.CharField(choices=[('consistent_improver', 'Consistent Improver'), ('silent_learner', 'Silent Learner'), ('high_attendance_low_growth', 'High Attendance Low Growth'), ('unstable_performer', 'Unstable Performer'), ('at_risk', 'At-Risk Student')], help_text='Student cluster assignment', max_length=50)),
                ('cluster_confidence', models.FloatField(help_text='Confidence score for cluster assignment (0-1)')),
                ('growth_insights', models.TextField(help_text='Human-readable growth insights')),
                ('recommendations', models.TextField(help_text='Actionable recommendations for teacher')),
                ('at_risk_flags', models.JSONField(blank=True, default=dict, help_text='Flags indicating at-risk patterns')),
                ('data_points_used', models.PositiveIntegerField(default=0, help_text='Number of data points used in analysis')),
                ('is_sufficient_data', models.BooleanField(default=True, help_text='Whether analysis has sufficient data')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('enrollment', models.ForeignKey(help_text='Student enrollment reference', on_delete=django.db.models.deletion.CASCADE, related_name='growth_analyses', to='class.enrollment')),
            ],
            options={
                'verbose_name': 'Student Growth Analysis',
                'verbose_name_plural': 'Student Growth Analyses',
                'ordering': ['-analysis_date'],
            },
        ),
        migrations.AddIndex(
            model_name='studentquiz',
            index=models.Index(fields=['enrollment', 'quiz_month'], name='quiz_enroll_month_idx'),
        ),
        migrations.AddIndex(
            model_name='studentquiz',
            index=models.Index(fields=['enrollment', 'quiz_date'], name='quiz_enroll_date_idx'),
        ),
        migrations.AddIndex(
            model_name='studentquiz',
            index=models.Index(fields=['quiz_month'], name='quiz_month_idx'),
        ),
        migrations.AddIndex(
            model_name='studentgrowthanalysis',
            index=models.Index(fields=['enrollment', '-analysis_date'], name='growth_enroll_date_idx'),
        ),
        migrations.AddIndex(
            model_name='studentgrowthanalysis',
            index=models.Index(fields=['risk_level', '-analysis_date'], name='growth_risk_date_idx'),
        ),
        migrations.AddIndex(
            model_name='studentgrowthanalysis',
            index=models.Index(fields=['student_cluster'], name='growth_cluster_idx'),
        ),
    ]
