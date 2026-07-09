from django.db import models
import uuid
import datetime

def school_profile_image_path(instance, filename):
    now = datetime.datetime.now()
    return f"CLAS/{now.strftime('%Y')}/{now.strftime('%m')}/schools/profile/{filename}"

def school_logo_path(instance, filename):
    now = datetime.datetime.now()
    return f"CLAS/{now.strftime('%Y')}/{now.strftime('%m')}/schools/logos/{filename}"

class School(models.Model):

    STATUS_CHOICES = (
        (1, "Active"),
        (0, "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200)
    udise = models.CharField(max_length=50, unique=True)

    block = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="Madhya Pradesh", help_text="State/Province")
    
    # Cluster/Area relationship
    cluster = models.ForeignKey(
        'Cluster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schools',
        help_text="Cluster/Area this school belongs to"
    )
    
    # New fields for school details
    area = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Location coordinates for map display
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        default=28.7041,
        help_text="School latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        default=77.1025,
        help_text="School longitude coordinate"
    )

    status = models.SmallIntegerField(
        choices=STATUS_CHOICES,
        default=1
    )

    # 🔽 Derived / dashboard fields (cached)
    enrolled_students = models.PositiveIntegerField(default=0)
    avg_attendance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    validation_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    profile_image = models.ImageField(
        upload_to=school_profile_image_path,
        null=True,
        blank=True
    )
    
    logo = models.ImageField(
        upload_to=school_logo_path,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.district})"
