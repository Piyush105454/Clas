from django.db import models
import uuid
from django.conf import settings
from .school import School

User = settings.AUTH_USER_MODEL

class FacilitatorSchool(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    facilitator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assigned_schools",
        limit_choices_to={"role_id": 2}  # facilitator
    )

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="facilitators"
    )

    assigned_date = models.DateField(auto_now_add=True)

    is_primary = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("facilitator", "school")
        verbose_name = "Facilitator–School Mapping"
        verbose_name_plural = "Facilitator–School Mappings"
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['is_active', 'school'], name='facsch_active_sch_idx'),
            models.Index(fields=['facilitator', 'is_active'], name='facsch_facil_active_idx'),
        ]

    def __str__(self):
        return f"{self.facilitator} → {self.school}"
