import uuid
from django.db import models
from django.conf import settings
from .school import School
from .class_section import ClassSection


# PHASE 1 OPTIMIZATION: DateType choices
class DateType(models.IntegerChoices):
    """Date type choices for CalendarDate - optimized for performance"""
    SESSION = 1, "Planned Session"
    HOLIDAY = 2, "Holiday / No Session"
    OFFICE_WORK = 3, "Office Work / Task"


class SupervisorCalendar(models.Model):
    """
    Calendar management for a supervisor
    Tracks planned sessions, holidays, and office work dates
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    supervisor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Calendar for {self.supervisor.username}"


class CalendarDate(models.Model):
    """
    Individual date entries in supervisor's calendar
    Can be: planned session, holiday, or office work
    Supports multiple classes for grouped sessions
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    calendar = models.ForeignKey(
        SupervisorCalendar,
        on_delete=models.CASCADE,
        related_name="dates"
    )
    
    date = models.DateField()
    time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time for the session/office work"
    )
    # PHASE 1 OPTIMIZATION: Use SmallIntegerField with IntegerChoices
    date_type = models.SmallIntegerField(
        choices=DateType.choices,
        default=DateType.SESSION,
        help_text="Type: 1=Session, 2=Holiday, 3=Office Work"
    )
    
    # For session type - support multiple classes (grouped sessions)
    class_sections = models.ManyToManyField(
        ClassSection,
        blank=True,
        related_name="calendar_sessions"
    )
    
    # Legacy field for backward compatibility (deprecated)
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_sessions_legacy"
    )
    
    school = models.ForeignKey(
        'class.School',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="calendar_entries"
    )
    
    # For holiday type
    holiday_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of holiday (e.g., Diwali, Summer Break)"
    )
    
    # For office work type
    office_task_description = models.TextField(
        blank=True,
        help_text="Description of office work/task"
    )
    
    # Facilitator assignment for office work
    assigned_facilitators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_office_work_dates",
        help_text="Facilitators assigned to this office work"
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date']
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['calendar', 'date'], name='caldate_cal_date_idx'),
            models.Index(fields=['date_type', 'date'], name='caldate_type_date_idx'),
            models.Index(fields=['school', 'date'], name='caldate_sch_date_idx'),
        ]
    
    def __str__(self):
        return f"{self.calendar.supervisor.username} - {self.date} ({self.get_date_type_display()})"


class OfficeWorkAttendance(models.Model):
    """
    Track office work attendance (present/absent)
    """
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    calendar_date = models.ForeignKey(
        CalendarDate,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="office_work_attendance"
    )
    
    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        default='present'
    )
    
    remarks = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('calendar_date', 'facilitator')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['calendar_date', 'facilitator']),
            models.Index(fields=['facilitator', 'recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.facilitator.username} - {self.calendar_date.date} ({self.status})"
