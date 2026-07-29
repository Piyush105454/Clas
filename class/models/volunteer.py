import uuid
from django.db import models
from django.core.exceptions import ValidationError

class Volunteer(models.Model):
    """
    Model representing Guest Teachers & Speaker Volunteers
    """
    class OrganizationType(models.TextChoices):
        COMPANY = 'COMPANY', 'Company'
        INDIVIDUAL = 'INDIVIDUAL', 'Individual'
        NGO = 'NGO', 'NGO'
        ACADEMIC = 'ACADEMIC', 'Academic'
        OTHER = 'OTHER', 'Other'

    class VolunteerRole(models.TextChoices):
        GUEST_TEACHER = 'GUEST_TEACHER', 'Guest Teacher'
        GUEST_SPEAKER = 'GUEST_SPEAKER', 'Guest Speaker'
        BOTH = 'BOTH', 'Both'

    class VolunteerStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    class PreferredDay(models.TextChoices):
        NONE = 'NONE', 'None'
        MONDAY = 'MONDAY', 'Monday'
        TUESDAY = 'TUESDAY', 'Tuesday'
        WEDNESDAY = 'WEDNESDAY', 'Wednesday'
        THURSDAY = 'THURSDAY', 'Thursday'
        FRIDAY = 'FRIDAY', 'Friday'
        SATURDAY = 'SATURDAY', 'Saturday'
        SUNDAY = 'SUNDAY', 'Sunday'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Volunteer Details
    full_name = models.CharField(max_length=255)
    role_type = models.CharField(
        max_length=50, 
        choices=VolunteerRole.choices, 
        default=VolunteerRole.GUEST_TEACHER
    )
    organization_type = models.CharField(
        max_length=50, 
        choices=OrganizationType.choices, 
        default=OrganizationType.INDIVIDUAL
    )
    organization_name = models.CharField(max_length=255, blank=True, default='')
    personal_email = models.EmailField(blank=True, default='')
    work_email = models.EmailField(blank=True, default='')
    country = models.CharField(max_length=100, default='India')
    city = models.CharField(max_length=100, default='Bangalore')
    phone_number = models.CharField(max_length=20)
    linkedin_profile = models.URLField(max_length=500, blank=True, default='')

    # Volunteering Preferences
    regular_volunteering = models.BooleanField(default=False)
    frequency_per_month = models.PositiveIntegerField(default=0)
    interested_area = models.CharField(max_length=255, blank=True, default='')
    interested_topic = models.CharField(max_length=255, blank=True, default='')
    preferred_day = models.CharField(
        max_length=50,
        choices=PreferredDay.choices,
        default=PreferredDay.NONE
    )
    preferred_class = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=VolunteerStatus.choices,
        default=VolunteerStatus.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if not self.personal_email and not self.work_email:
            raise ValidationError("At least one email (personal or work) is required.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
