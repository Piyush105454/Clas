import uuid
from django.db import models
from django.conf import settings
from .students import Student
from .class_section import ClassSection


class Subject(models.Model):
    """Subject model - linked to curriculum"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PerformanceCutoff(models.Model):
    """Performance cutoff settings per class"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class_section = models.OneToOneField(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="performance_cutoff"
    )
    passing_score = models.IntegerField(default=40, help_text="Minimum score to pass (0-100)")
    excellent_score = models.IntegerField(default=80, help_text="Score for excellent performance (0-100)")
    good_score = models.IntegerField(default=60, help_text="Score for good performance (0-100)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Performance Cutoffs"
    
    def __str__(self):
        return f"{self.class_section.display_name} - Cutoff: {self.passing_score}"


class StudentPerformance(models.Model):
    """Student performance scores by subject"""
    GRADE_CHOICES = [
        ('A', 'Excellent (80-100)'),
        ('B', 'Good (60-79)'),
        ('C', 'Average (40-59)'),
        ('F', 'Failed (0-39)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="performance_records"
    )
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="student_performances"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="student_performances"
    )
    score = models.IntegerField(help_text="Score out of 100")
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES, default='C')
    remarks = models.TextField(blank=True, help_text="Teacher remarks")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_performances"
    )
    recorded_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'class_section', 'subject')
        ordering = ['-recorded_date']
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['student', 'subject'], name='perf_stud_subj_idx'),
            models.Index(fields=['class_section', 'subject'], name='perf_cls_subj_idx'),
        ]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name}: {self.score}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate grade based on score and cutoff"""
        try:
            cutoff = self.class_section.performance_cutoff
            if self.score >= cutoff.excellent_score:
                self.grade = 'A'
            elif self.score >= cutoff.good_score:
                self.grade = 'B'
            elif self.score >= cutoff.passing_score:
                self.grade = 'C'
            else:
                self.grade = 'F'
        except:
            # Default grading if no cutoff set
            if self.score >= 80:
                self.grade = 'A'
            elif self.score >= 60:
                self.grade = 'B'
            elif self.score >= 40:
                self.grade = 'C'
            else:
                self.grade = 'F'
        
        super().save(*args, **kwargs)


class StudentPerformanceSummary(models.Model):
    """Summary of student performance across all subjects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name="performance_summary"
    )
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="performance_summaries"
    )
    average_score = models.FloatField(default=0, help_text="Average score across all subjects")
    total_subjects = models.IntegerField(default=0)
    passed_subjects = models.IntegerField(default=0)
    failed_subjects = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True, help_text="Rank in class")
    is_passed = models.BooleanField(default=False, help_text="Overall pass/fail status")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'class_section')
        ordering = ['rank']
    
    def __str__(self):
        return f"{self.student.full_name} - Avg: {self.average_score:.1f}, Rank: {self.rank}"
