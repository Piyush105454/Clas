from django.db import models
import uuid
from .school import School

class ClassSection(models.Model):
    # Define class level ordering
    CLASS_LEVEL_ORDER = {
        'LKG': 1,
        'UKG': 2,
        '1': 3, '2': 4, '3': 5, '4': 6, '5': 7,
        '6': 8, '7': 9, '8': 10, '9': 11, '10': 12
    }
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='class_sections'
    )

    class_level = models.CharField(max_length=8)   # LKG, UKG, 1, 2, etc.
    section = models.CharField(max_length=8, blank=True, null=True)  # A, B

    academic_year = models.CharField(max_length=9, default="2024-2025")
    display_name = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('school', 'class_level', 'section', 'academic_year')
        verbose_name = "Class Section"
        verbose_name_plural = "Class Sections"
        ordering = ['school__name', 'class_level', 'section']

    def save(self, *args, **kwargs):
        self.display_name = f"{self.class_level}{self.section or ''}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school.name} - {self.display_name} ({self.academic_year})"
    
    @property
    def class_level_order(self):
        """Return numeric order for sorting"""
        return self.CLASS_LEVEL_ORDER.get(self.class_level, 999)
