import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


# PHASE 1 OPTIMIZATION: CurriculumStatus choices
class CurriculumStatus(models.IntegerChoices):
    """Status choices for CurriculumSession - optimized for performance"""
    DRAFT = 1, "Draft"
    PUBLISHED = 2, "Published"
    ARCHIVED = 3, "Archived"


class CurriculumSession(models.Model):
    """
    Represents a curriculum session for admin management.
    Language-specific and day-based for the entire curriculum (not class-specific).
    """
    
    LANGUAGE_CHOICES = [
        ('hindi', 'Hindi'),
        ('english', 'English'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    title = models.CharField(
        max_length=255,
        help_text="Session title/name"
    )
    
    day_number = models.PositiveIntegerField(
        help_text="Day in curriculum sequence (1-150)"
    )
    
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        help_text="Session language (Hindi/English)"
    )
    
    content = models.TextField(
        blank=True,
        help_text="Rich text session content"
    )
    
    learning_objectives = models.TextField(
        blank=True,
        help_text="Session learning goals"
    )
    
    activities = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured activity data"
    )
    
    resources = models.JSONField(
        default=dict,
        blank=True,
        help_text="Links to videos, documents, media"
    )
    

    
    status = models.SmallIntegerField(
        choices=CurriculumStatus.choices,
        default=CurriculumStatus.DRAFT,
        help_text="Status: 1=Draft, 2=Published, 3=Archived"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sessions',
        help_text="Administrator who created session"
    )
    
    # New integration fields
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times accessed by facilitators"
    )
    
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time content was accessed by a facilitator"
    )
    
    is_active_for_facilitators = models.BooleanField(
        default=True,
        help_text="Whether facilitators should see this content"
    )
    
    fallback_to_static = models.BooleanField(
        default=False,
        help_text="Force fallback to static content for this day/language"
    )

    class Meta:
        ordering = ['language', 'day_number']
        unique_together = ('day_number', 'language')
        verbose_name = "Curriculum Session"
        verbose_name_plural = "Curriculum Sessions"

    def clean(self):
        if self.day_number < 1 or self.day_number > 150:
            raise ValidationError("Day number must be between 1 and 150")

    def __str__(self):
        return f"{self.get_language_display()} - Day {self.day_number}: {self.title}"








class ImportHistory(models.Model):
    """
    Records session import operations for audit and rollback purposes.
    """
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    import_file = models.FileField(
        upload_to='session_imports/',
        help_text="Original import file"
    )
    
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='import_operations',
        help_text="Administrator who performed import"
    )
    
    import_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When import was performed"
    )
    
    sessions_created = models.PositiveIntegerField(
        default=0,
        help_text="Number of new sessions created"
    )
    
    sessions_updated = models.PositiveIntegerField(
        default=0,
        help_text="Number of existing sessions updated"
    )
    
    errors = models.JSONField(
        default=list,
        blank=True,
        help_text="Import errors and warnings"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='success'
    )

    class Meta:
        ordering = ['-import_timestamp']
        verbose_name = "Import History"
        verbose_name_plural = "Import Histories"

    def __str__(self):
        return f"Import by {self.imported_by} on {self.import_timestamp} - {self.status}"





class CurriculumUsageLog(models.Model):
    """
    Tracks facilitator access to curriculum content for analytics.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    curriculum_session = models.ForeignKey(
        CurriculumSession,
        on_delete=models.CASCADE,
        related_name='curriculum_usage_logs'
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='curriculum_accesses'
    )
    
    class_section = models.ForeignKey(
        'ClassSection',
        on_delete=models.CASCADE,
        related_name='curriculum_accesses'
    )
    
    planned_session = models.ForeignKey(
        'PlannedSession',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Associated PlannedSession if applicable"
    )
    
    access_timestamp = models.DateTimeField(auto_now_add=True)
    session_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time spent viewing content in seconds"
    )
    
    content_source = models.CharField(
        max_length=20,
        choices=[
            ('admin_managed', 'Admin Managed'),
            ('static_fallback', 'Static Fallback'),
        ],
        help_text="Source of the curriculum content"
    )
    
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-access_timestamp']
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['curriculum_session', 'facilitator'], name='culog_curr_facil_idx'),
            models.Index(fields=['facilitator', 'access_timestamp'], name='culog_facil_ts_idx'),
        ]
        verbose_name = "Curriculum Usage Log"
        verbose_name_plural = "Curriculum Usage Logs"

    def __str__(self):
        return f"{self.facilitator} accessed {self.curriculum_session} at {self.access_timestamp}"


class SessionContentMapping(models.Model):
    """
    Links PlannedSessions with their corresponding CurriculumSessions.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    planned_session = models.OneToOneField(
        'PlannedSession',
        on_delete=models.CASCADE,
        related_name='curriculum_mapping'
    )
    
    curriculum_session = models.ForeignKey(
        CurriculumSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planned_mappings'
    )
    
    content_source = models.CharField(
        max_length=20,
        choices=[
            ('admin_managed', 'Admin Managed'),
            ('static_fallback', 'Static Fallback'),
            ('not_available', 'Not Available'),
        ],
        default='static_fallback'
    )
    
    last_sync = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('synced', 'Synced'),
            ('outdated', 'Outdated'),
            ('failed', 'Failed'),
        ],
        default='synced'
    )

    class Meta:
        verbose_name = "Session Content Mapping"
        verbose_name_plural = "Session Content Mappings"

    def __str__(self):
        return f"{self.planned_session} -> {self.curriculum_session or 'Static Content'}"