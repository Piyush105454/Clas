import uuid
from django.db import models
from django.conf import settings


class FacilitatorTask(models.Model):
    """
    Facilitator task/preparation for a session
    Can include photos, videos, or Facebook links
    """
    MEDIA_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('facebook_link', 'Facebook Link'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actual_session = models.ForeignKey(
        'class.ActualSession',
        on_delete=models.CASCADE,
        related_name="facilitator_tasks",
        null=True,
        blank=True,
        help_text="Optional - task can be created without a session"
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="facilitator_tasks"
    )
    
    media_type = models.CharField(
        max_length=20,
        choices=MEDIA_TYPE_CHOICES,
        default='photo'
    )
    
    # For photo/video uploads
    media_file = models.FileField(
        upload_to='facilitator_tasks/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Photo or video file"
    )
    
    # For Facebook links
    facebook_link = models.URLField(
        null=True,
        blank=True,
        help_text="Facebook post or video link"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the task/preparation"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actual_session', 'facilitator']),
            models.Index(fields=['facilitator', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.facilitator.full_name} - {self.get_media_type_display()} - {self.actual_session.date}"
