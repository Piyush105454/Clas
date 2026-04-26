"""
Student Growth Intelligence System Models

This module contains models for tracking and analyzing student growth:
- StudentQuiz: Monthly quiz scores for each student
- StudentGrowthAnalysis: ML-based growth analysis results and insights
"""

import uuid
from django.db import models
from django.conf import settings


# =========================
# STUDENT QUIZ - MONTHLY TRACKING
# =========================
class StudentQuiz(models.Model):
    """
    Tracks monthly quiz scores for each student.
    Supports month-wise analysis and trend detection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    enrollment = models.ForeignKey(
        'Enrollment',
        on_delete=models.CASCADE,
        related_name='quizzes',
        help_text="Student enrollment reference"
    )
    
    quiz_date = models.DateField(
        help_text="Date when quiz was conducted"
    )
    
    quiz_month = models.CharField(
        max_length=7,  # Format: "2026-02"
        db_index=True,
        help_text="Month in YYYY-MM format for easy filtering"
    )
    
    score = models.PositiveIntegerField(
        help_text="Quiz score (0-100)"
    )
    
    total_marks = models.PositiveIntegerField(
        help_text="Total marks for the quiz"
    )
    
    questions_attempted = models.PositiveIntegerField(
        help_text="Number of questions attempted"
    )
    
    correct_answers = models.PositiveIntegerField(
        help_text="Number of correct answers"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes about the quiz performance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['quiz_date']
        verbose_name = "Student Quiz"
        verbose_name_plural = "Student Quizzes"
        indexes = [
            models.Index(fields=['enrollment', 'quiz_month'], name='quiz_enroll_month_idx'),
            models.Index(fields=['enrollment', 'quiz_date'], name='quiz_enroll_date_idx'),
            models.Index(fields=['quiz_month'], name='quiz_month_idx'),
        ]
    
    def __str__(self):
        return f"{self.enrollment.student.full_name} - {self.quiz_month} ({self.score}%)"
    
    def save(self, *args, **kwargs):
        # Auto-populate quiz_month from quiz_date if not set
        if not self.quiz_month and self.quiz_date:
            self.quiz_month = self.quiz_date.strftime('%Y-%m')
        super().save(*args, **kwargs)


# =========================
# STUDENT GROWTH ANALYSIS - ML RESULTS
# =========================
class StudentGrowthAnalysis(models.Model):
    """
    Stores ML-based growth analysis results for each student.
    Updated weekly or on-demand with comprehensive metrics and insights.
    """
    
    # Risk level choices
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ]
    
    # Engagement level choices
    ENGAGEMENT_LEVEL_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    # Student cluster choices
    CLUSTER_CHOICES = [
        ('consistent_improver', 'Consistent Improver'),
        ('silent_learner', 'Silent Learner'),
        ('high_attendance_low_growth', 'High Attendance Low Growth'),
        ('unstable_performer', 'Unstable Performer'),
        ('at_risk', 'At-Risk Student'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    enrollment = models.ForeignKey(
        'Enrollment',
        on_delete=models.CASCADE,
        related_name='growth_analyses',
        help_text="Student enrollment reference"
    )
    
    analysis_date = models.DateField(
        auto_now=True,
        help_text="Date when analysis was performed"
    )
    
    # ===== GROWTH METRICS =====
    growth_score = models.FloatField(
        help_text="Overall growth score (0-100)"
    )
    
    attendance_consistency = models.FloatField(
        help_text="Attendance consistency score (0-100)"
    )
    
    quiz_improvement_rate = models.FloatField(
        help_text="Quiz improvement rate as percentage"
    )
    
    text_complexity_growth = models.FloatField(
        help_text="Text complexity growth percentage"
    )
    
    engagement_level = models.CharField(
        max_length=20,
        choices=ENGAGEMENT_LEVEL_CHOICES,
        help_text="Overall engagement level"
    )
    
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        db_index=True,
        help_text="Risk level for intervention"
    )
    
    # ===== CLUSTERING =====
    student_cluster = models.CharField(
        max_length=50,
        choices=CLUSTER_CHOICES,
        help_text="Student cluster assignment"
    )
    
    cluster_confidence = models.FloatField(
        help_text="Confidence score for cluster assignment (0-1)"
    )
    
    # ===== INSIGHTS & RECOMMENDATIONS =====
    growth_insights = models.TextField(
        help_text="Human-readable growth insights"
    )
    
    recommendations = models.TextField(
        help_text="Actionable recommendations for teacher"
    )
    
    at_risk_flags = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flags indicating at-risk patterns"
    )
    
    # ===== METADATA =====
    data_points_used = models.PositiveIntegerField(
        default=0,
        help_text="Number of data points used in analysis"
    )
    
    is_sufficient_data = models.BooleanField(
        default=True,
        help_text="Whether analysis has sufficient data"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-analysis_date']
        verbose_name = "Student Growth Analysis"
        verbose_name_plural = "Student Growth Analyses"
        indexes = [
            models.Index(fields=['enrollment', '-analysis_date'], name='growth_enroll_date_idx'),
            models.Index(fields=['risk_level', '-analysis_date'], name='growth_risk_date_idx'),
            models.Index(fields=['student_cluster'], name='growth_cluster_idx'),
        ]
    
    def __str__(self):
        return f"{self.enrollment.student.full_name} - Growth Analysis ({self.analysis_date})"
    
    @property
    def is_at_risk(self):
        """Check if student is flagged as at-risk"""
        return self.risk_level == 'high'
    
    @property
    def summary(self):
        """Get a brief summary of the analysis"""
        return {
            'growth_score': self.growth_score,
            'risk_level': self.get_risk_level_display(),
            'cluster': self.get_student_cluster_display(),
            'engagement': self.get_engagement_level_display(),
        }
