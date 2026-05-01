import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


# =========================
# CHOICE ENUMS (PHASE 1 OPTIMIZATION)
# =========================

class SessionStatus(models.IntegerChoices):
    """Status choices for ActualSession - optimized for performance"""
    PENDING = 0, "Pending"
    CONDUCTED = 1, "Conducted"
    HOLIDAY = 2, "Holiday"
    CANCELLED = 3, "Cancelled"


class AttendanceStatus(models.IntegerChoices):
    """Status choices for Attendance - optimized for performance"""
    PRESENT = 1, "Present"
    ABSENT = 2, "Absent"
    LEAVE = 3, "Leave"


# =========================
# GROUPED SESSION - PERMANENT GROUPING
# =========================
class GroupedSession(models.Model):
    """
    Represents a permanent grouping of multiple classes that share the same 150 sessions.
    This is the master record that tracks which classes are grouped together.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # The unique identifier used in PlannedSession.grouped_session_id
    grouped_session_id = models.UUIDField(
        unique=True,
        help_text="Unique ID that links all PlannedSessions in this group"
    )
    
    # The classes that are part of this group
    class_sections = models.ManyToManyField(
        'class.ClassSection',
        related_name='grouped_sessions',
        help_text="All classes that share the same 150 sessions"
    )
    
    # Metadata
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional name for this grouped session (e.g., 'Section A & B Combined')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional description of why these classes are grouped"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['grouped_session_id']),
        ]
    
    def __str__(self):
        classes_str = ', '.join([c.display_name for c in self.class_sections.all()])
        return f"Grouped Session: {classes_str}"


# =========================
# STUDENT
# =========================
class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment_number = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("M", "Male"), ("F", "Female")]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


# =========================
# ENROLLMENT
# =========================
class Enrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="enrollments"
    )
    school = models.ForeignKey(
        "class.School", on_delete=models.CASCADE, related_name="enrollments"
    )
    class_section = models.ForeignKey(
        "class.ClassSection", on_delete=models.CASCADE, related_name="enrollments"
    )

    start_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("student", "class_section", "is_active")
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['is_active', 'school'], name='enroll_active_sch_idx'),
            models.Index(fields=['student', 'is_active'], name='enroll_stud_active_idx'),
        ]

    def save(self, *args, **kwargs):
        if not hasattr(self, 'school_id') or self.school_id is None:
            if self.class_section_id:
                self.school = self.class_section.school
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} → {self.class_section}"



# =========================
# PLANNED SESSION (DAY LEVEL) - ENHANCED
# =========================
class PlannedSession(models.Model):
    """
    Represents ONE logical teaching day (Day 1, Day 2, ...)
    Enhanced with sequence tracking and validation
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class_section = models.ForeignKey(
        "class.ClassSection",
        on_delete=models.CASCADE,
        related_name="planned_sessions"
    )

    day_number = models.PositiveIntegerField(
        help_text="Logical day number (Day 1, Day 2, ...)"
    )

    title = models.CharField(
        max_length=255,
        help_text="Session title (e.g. CLAS - Computer Literacy At School)"
    )

    description = models.TextField(
        blank=True,
        help_text="Optional day-level description"
    )

    is_active = models.BooleanField(default=True)
    
    # New sequence management fields
    sequence_position = models.PositiveIntegerField(
        help_text="Enforced sequential position",
        null=True,
        blank=True
    )
    
    is_required = models.BooleanField(
        default=True,
        help_text="Cannot be skipped (default True)"
    )
    
    prerequisite_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Days that must be completed first"
    )
    
    # Grouped session support
    grouped_session_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="If set, this session is part of a grouped session. All classes with same grouped_session_id share this session."
    )
    
    # PHASE 2: Content Versioning Fields
    curriculum_session = models.ForeignKey(
        'CurriculumSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planned_sessions',
        help_text="Linked curriculum content"
    )
    
    content_version = models.PositiveIntegerField(
        default=1,
        help_text="Version of curriculum content"
    )
    
    last_content_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When content was last synced"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_number"]
        # Allow multiple sessions per day_number if they have different grouped_session_id
        # For non-grouped sessions (grouped_session_id=None), enforce unique (class_section, day_number)
        # For grouped sessions, allow multiple classes to have same day_number with same grouped_session_id
        constraints = [
            models.UniqueConstraint(
                fields=['class_section', 'day_number'],
                condition=models.Q(grouped_session_id__isnull=True),
                name='unique_planned_session_non_grouped'
            ),
            models.UniqueConstraint(
                fields=['class_section', 'day_number', 'grouped_session_id'],
                condition=models.Q(grouped_session_id__isnull=False),
                name='unique_planned_session_grouped'
            ),
        ]
        verbose_name = "Planned Session (Day)"
        verbose_name_plural = "Planned Sessions (Days)"
        indexes = [
            models.Index(fields=['class_section', 'day_number']),
            models.Index(fields=['class_section', 'is_active']),
            models.Index(fields=['grouped_session_id', 'day_number']),  # OPTIMIZATION: For grouped session detection
        ]

    def __str__(self):
        return f"{self.class_section} - Day {self.day_number}"


# =========================
# SESSION STEP (ACTIVITIES INSIDE DAY)
# =========================
class SessionStep(models.Model):
    """
    Represents ONE activity/step inside a day
    Example: English rhyme, Math activity, Computer video, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    planned_session = models.ForeignKey(
        PlannedSession,
        on_delete=models.CASCADE,
        related_name="steps"
    )

    order = models.PositiveIntegerField(
        help_text="Execution order inside the day (1, 2, 3...)"
    )

    subject = models.CharField(
        max_length=30,
        choices=[
            ("english", "English"),
            ("hindi", "Hindi"),
            ("maths", "Maths"),
            ("computer", "Computer"),
            ("activity", "Activity / Energizer"),
            ("mindfulness", "Mindfulness"),
        ]
    )

    title = models.CharField(
        max_length=255,
        help_text="Activity title (from CSV 'What' column)"
    )

    description = models.TextField(
        blank=True,
        help_text="Detailed teacher instructions"
    )

    youtube_url = models.URLField(
        blank=True,
        null=True,
        help_text="Optional YouTube video for this step"
    )

    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes"
    )

    class Meta:
        ordering = ["order"]
        unique_together = ("planned_session", "order")
        verbose_name = "Session Step"
        verbose_name_plural = "Session Steps"

    def __str__(self):
        return f"Day {self.planned_session.day_number} - Step {self.order}"


# =========================
# ACTUAL SESSION (CALENDAR EXECUTION) - ENHANCED
# =========================

# Cancellation reason choices
CANCELLATION_REASONS = [
    ('school_shutdown', 'School permanently shuts down for this class'),
    ('syllabus_change', 'Government removes topic from syllabus'),
    ('exam_period', 'Exam period replaces class permanently'),
    ('duplicate_session', 'Duplicate or wrongly created planned session'),
    ('emergency', 'Emergency where session will never happen again'),
]

class ActualSession(models.Model):
    """
    Represents REAL execution of a PlannedSession on a calendar date
    Enhanced with detailed status tracking and cancellation reasons
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    planned_session = models.ForeignKey(
        PlannedSession,
        on_delete=models.CASCADE,
        related_name="actual_sessions"
    )

    date = models.DateField()

    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_sessions"
    )

    status = models.SmallIntegerField(
        choices=SessionStatus.choices,
        default=SessionStatus.CONDUCTED,
        help_text="Session status: 1=Conducted, 2=Holiday, 3=Cancelled"
    )

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Enhanced tracking fields
    conducted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Exact time of conduct"
    )
    
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Session duration"
    )
    
    attendance_marked = models.BooleanField(
        default=False,
        help_text="Whether attendance was completed"
    )
    
    facilitator_attendance = models.CharField(
        max_length=10,
        choices=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('leave', 'Leave'),
            ('', 'Not Marked')
        ],
        default='',
        blank=True,
        help_text="Facilitator attendance status"
    )
    
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes",
        help_text="Who changed the status"
    )
    
    status_change_reason = models.TextField(
        blank=True,
        help_text="Why status was changed"
    )
    
    can_be_rescheduled = models.BooleanField(
        default=True,
        help_text="For holiday sessions"
    )
    
    # Cancellation tracking
    cancellation_reason = models.CharField(
        max_length=50,
        choices=CANCELLATION_REASONS,
        blank=True,
        null=True,
        help_text="Predefined cancellation reasons"
    )
    
    cancellation_category = models.CharField(
        max_length=50,
        blank=True,
        help_text="school_shutdown, syllabus_change, exam_period, duplicate, emergency"
    )
    
    is_permanent_cancellation = models.BooleanField(
        default=False,
        help_text="Cannot be undone"
    )

    is_conduct_completed = models.BooleanField(
        default=False,
        help_text="Whether the conduct step (Step 3) was marked as completed"
    )

    class Meta:
        unique_together = ("planned_session", "date")
        verbose_name = "Actual Session"
        
    @property
    def display_status(self):
        if self.status == 3:
            return "Class Not Available"
        elif self.status == 2:
            return "Holiday"
        elif self.status == 1:
            try:
                day_number = self.planned_session.day_number
            except AttributeError:
                day_number = 0
                
            if day_number == 999:
                return "FLN Curriculum"
            elif day_number == 998:
                return "Exam Time"
            elif day_number == 997:
                return "Present Office"
            return "Present Class"
        return "Pending"

    @property
    def status_color_class(self):
        if self.status == 3:
            return "bg-red-100 text-red-800"
        elif self.status == 2:
            return "bg-yellow-100 text-yellow-800"
        elif self.status == 1:
            try:
                day_number = self.planned_session.day_number
            except AttributeError:
                day_number = 0
            
            if day_number == 999:
                return "bg-blue-100 text-blue-800"
            elif day_number == 998:
                return "bg-purple-100 text-purple-800"
            elif day_number == 997:
                return "bg-indigo-100 text-indigo-800"
            return "bg-green-100 text-green-800"
        return "bg-gray-100 text-gray-800"
        verbose_name_plural = "Actual Sessions"
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['planned_session', 'status'], name='asess_sess_stat_idx'),
            models.Index(fields=['date', 'status'], name='asess_date_stat_idx'),
            models.Index(fields=['facilitator', 'date'], name='asess_facil_date_idx'),
            models.Index(fields=['status', 'date'], name='asess_stat_date_idx'),
        ]

    def __str__(self):
        return f"{self.planned_session} on {self.date}"
    
    def save(self, *args, **kwargs):
        # Set conducted_at when status changes to conducted
        if self.status == SessionStatus.CONDUCTED and not self.conducted_at:
            from django.utils import timezone
            self.conducted_at = timezone.now()
        
        # Set permanent cancellation flag
        if self.status == SessionStatus.CANCELLED:
            self.is_permanent_cancellation = True
            self.can_be_rescheduled = False
        
        super().save(*args, **kwargs)


class ClassSessionProgress(models.Model):
    """
    Tracks the curriculum progress for each class section.
    Used to reliably determine the next curriculum day number.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(default=timezone.now)
    class_section = models.ForeignKey('ClassSection', on_delete=models.CASCADE, related_name="session_progress")
    
    # Grouping info
    is_grouped = models.BooleanField(default=False)
    grouped_session_id = models.UUIDField(null=True, blank=True)
    group_classes_info = models.TextField(blank=True, help_text="Names of classes in the group")
    
    # Progress info
    day_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed')],
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('date', 'class_section')
        verbose_name = "Class Session Progress"
        verbose_name_plural = "Class Session Progress Logs"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.class_section.class_name} - Day {self.day_number} on {self.date}"


# =========================
# SESSION CANCELLATION - NEW (Phase 2)
# =========================
class SessionCancellation(models.Model):
    """
    Stores cancellation details for ActualSession
    Only created when status = CANCELLED
    Reduces ActualSession row size by moving cancellation fields
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actual_session = models.OneToOneField(
        ActualSession,
        on_delete=models.CASCADE,
        related_name='cancellation',
        help_text="Reference to the cancelled session"
    )
    
    reason = models.CharField(
        max_length=50,
        choices=CANCELLATION_REASONS,
        help_text="Why session was cancelled"
    )
    
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Cancellation category"
    )
    
    is_permanent = models.BooleanField(
        default=False,
        help_text="Cannot be undone"
    )
    
    can_be_rescheduled = models.BooleanField(
        default=True,
        help_text="Can be rescheduled"
    )
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_cancellations',
        help_text="Who changed the status"
    )
    
    change_reason = models.TextField(
        blank=True,
        help_text="Why status was changed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Session Cancellation"
        verbose_name_plural = "Session Cancellations"
        indexes = [
            models.Index(fields=['actual_session', 'is_permanent'], name='scancel_sess_perm_idx'),
        ]
    
    def __str__(self):
        return f"Cancellation - {self.actual_session}"


class Attendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actual_session = models.ForeignKey(
        ActualSession,
        on_delete=models.CASCADE,
        related_name="attendances"
    )

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="attendances"
    )

    # PHASE 1 OPTIMIZATION: Denormalized fields for faster reports
    student_id = models.UUIDField(db_index=True, null=True, blank=True, help_text="Cached from enrollment.student_id")
    class_section_id = models.UUIDField(db_index=True, null=True, blank=True, help_text="Cached from enrollment.class_section_id")
    school_id = models.UUIDField(db_index=True, null=True, blank=True, help_text="Cached from enrollment.school_id")

    status = models.SmallIntegerField(
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        help_text="Attendance status: 1=Present, 2=Absent, 3=Leave"
    )

    # Observation notes fields
    visible_change_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Observable physical or behavioral changes in student"
    )

    invisible_change_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal or cognitive changes not immediately visible"
    )

    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("actual_session", "enrollment")
        # PHASE 1 OPTIMIZATION: Add critical indexes
        indexes = [
            models.Index(fields=['status', 'marked_at'], name='attend_status_date_idx'),
            models.Index(fields=['student_id', 'marked_at'], name='attend_stud_date_idx'),
            models.Index(fields=['class_section_id', 'marked_at'], name='attend_cls_date_idx'),
            models.Index(fields=['school_id', 'marked_at'], name='attend_sch_date_idx'),
        ]

    def save(self, *args, **kwargs):
        # PHASE 1 OPTIMIZATION: Auto-populate denormalized fields
        if self.enrollment:
            self.student_id = self.enrollment.student_id
            self.class_section_id = self.enrollment.class_section_id
            self.school_id = self.enrollment.school_id
        super().save(*args, **kwargs)

    def clean(self):
        if self.actual_session.status != SessionStatus.CONDUCTED:
            raise ValidationError("Attendance can only be marked for conducted sessions.")

    def __str__(self):
        return f"{self.enrollment} - {self.get_status_display()}"


# =========================
# SESSION BULK TEMPLATE - NEW
# =========================
class SessionBulkTemplate(models.Model):
    """
    Enhanced template model for bulk session generation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=255,
        help_text="Template name (e.g., 'Standard CLAS Curriculum')"
    )
    
    description = models.TextField(
        help_text="Template description"
    )
    
    language = models.CharField(
        max_length=20,
        choices=[
            ('english', 'English'),
            ('hindi', 'Hindi'),
            ('both', 'Both'),
        ],
        default='english',
        help_text="Target language (Hindi/English/Both)"
    )
    
    total_days = models.PositiveIntegerField(
        default=150,
        help_text="Number of days in template (default 150)"
    )
    
    # Template structure
    day_templates = models.JSONField(
        default=dict,
        help_text="Day-wise content templates"
    )
    
    default_activities = models.JSONField(
        default=dict,
        help_text="Standard activities per day"
    )
    
    learning_objectives = models.JSONField(
        default=dict,
        help_text="Objectives for each day"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Administrator who created template"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether template can be used"
    )
    
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times applied"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Session Bulk Template"
        verbose_name_plural = "Session Bulk Templates"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.language})"


# =========================
# LESSON PLAN UPLOAD - NEW
# =========================
class LessonPlanUpload(models.Model):
    """
    New model to track facilitator lesson plan uploads
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    planned_session = models.ForeignKey(
        PlannedSession,
        on_delete=models.CASCADE,
        related_name="lesson_plan_uploads",
        help_text="Reference to the session"
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_plan_uploads",
        help_text="Who uploaded the lesson plan"
    )
    
    upload_date = models.DateField(
        auto_now_add=True,
        help_text="When it was uploaded"
    )
    
    lesson_plan_file = models.FileField(
        upload_to='clas/lessonplan/%Y/%m/',
        help_text="The actual lesson plan file"
    )
    
    # [NEW] Direct URL for cloud-native access
    direct_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="Permanent full URL to the file"
    )
    
    file_name = models.CharField(
        max_length=255,
        help_text="Original file name"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    upload_notes = models.TextField(
        blank=True,
        help_text="Optional notes from facilitator"
    )
    
    is_approved = models.BooleanField(
        default=False,
        help_text="Admin approval status"
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_lesson_plans",
        help_text="Admin who approved"
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Approval timestamp"
    )
    
    class Meta:
        unique_together = ('planned_session', 'facilitator')
        verbose_name = "Lesson Plan Upload"
        verbose_name_plural = "Lesson Plan Uploads"
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"Lesson Plan - {self.planned_session} by {self.facilitator.full_name}"


# =========================
# SESSION REWARD - NEW
# =========================
class SessionReward(models.Model):
    """
    New model to track student rewards
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actual_session = models.ForeignKey(
        ActualSession,
        on_delete=models.CASCADE,
        related_name="rewards",
        help_text="Reference to the conducted session"
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_rewards",
        help_text="Who gave the reward"
    )
    
    reward_type = models.CharField(
        max_length=20,
        choices=[
            ('photo', 'Photo'),
            ('text', 'Text'),
            ('both', 'Both'),
        ],
        default='text',
        help_text="photo, text, both"
    )
    
    reward_photo = models.ImageField(
        upload_to='session_rewards/%Y/%m/',
        null=True,
        blank=True,
        help_text="Photo of reward/student"
    )
    
    reward_description = models.TextField(
        help_text="Text description of reward"
    )
    
    student_names = models.TextField(
        help_text="Names of students who received rewards"
    )
    
    reward_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When reward was given"
    )
    
    is_visible_to_admin = models.BooleanField(
        default=True,
        help_text="Admin visibility"
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text="Admin comments on reward"
    )
    
    class Meta:
        ordering = ['-reward_date']
        verbose_name = "Session Reward"
        verbose_name_plural = "Session Rewards"
    
    def __str__(self):
        return f"Reward - {self.actual_session} by {self.facilitator.full_name}"


# =========================
# SESSION FEEDBACK - NEW
# =========================
class SessionFeedback(models.Model):
    """
    Simplified teacher reflection - only 1 question: How was the day?
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actual_session = models.ForeignKey(
        ActualSession,
        on_delete=models.CASCADE,
        related_name="feedback",
        help_text="Reference to conducted session"
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_feedback",
        help_text="Who provided feedback"
    )
    
    # Simplified: Only 1 question - How was the day?
    day_reflection = models.TextField(
        blank=True,
        help_text="How was the day? - Free text reflection"
    )
    rating = models.IntegerField(
        default=10,
        help_text="Session rating out of 10"
    )
    
    # Metadata
    feedback_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('actual_session', 'facilitator')
        verbose_name = "Session Feedback"
        verbose_name_plural = "Session Feedback"
        ordering = ['-feedback_date']
    
    def __str__(self):
        return f"Feedback - {self.actual_session} by {self.facilitator.full_name} ({self.day_reflection})"


# =========================
# SESSION PREPARATION CHECKLIST - NEW
# =========================
class SessionPreparationChecklist(models.Model):
    """
    New model for session preparation tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    planned_session = models.ForeignKey(
        PlannedSession,
        on_delete=models.CASCADE,
        related_name="preparation_checklists",
        help_text="Reference to session"
    )
    
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preparation_checklists",
        help_text="Who is preparing"
    )
    
    # Preparation Checkpoints
    lesson_plan_reviewed = models.BooleanField(default=False)
    materials_prepared = models.BooleanField(default=False)
    technology_tested = models.BooleanField(default=False)
    classroom_setup_ready = models.BooleanField(default=False)
    student_list_reviewed = models.BooleanField(default=False)
    previous_session_feedback_reviewed = models.BooleanField(default=False)
    
    # Checkpoint Timestamps
    checkpoints_completed_at = models.JSONField(
        default=dict,
        help_text="Track when each checkpoint was completed"
    )
    
    preparation_start_time = models.DateTimeField(
        null=True,
        blank=True
    )
    
    preparation_complete_time = models.DateTimeField(
        null=True,
        blank=True
    )
    
    total_preparation_minutes = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    
    # Preparation Notes
    preparation_notes = models.TextField(blank=True)
    anticipated_challenges = models.TextField(blank=True)
    special_requirements = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('planned_session', 'facilitator')
        verbose_name = "Session Preparation Checklist"
        verbose_name_plural = "Session Preparation Checklists"
        ordering = ['-preparation_start_time']
    
    def __str__(self):
        return f"Preparation - {self.planned_session} by {self.facilitator.full_name}"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage of checklist"""
        checkpoints = [
            self.lesson_plan_reviewed,
            self.materials_prepared,
            self.technology_tested,
            self.classroom_setup_ready,
            self.student_list_reviewed,
            self.previous_session_feedback_reviewed,
        ]
        completed = sum(checkpoints)
        return (completed / len(checkpoints)) * 100


# =========================
# STUDENT FEEDBACK - NEW
# =========================
class StudentFeedback(models.Model):
    """
    Student feedback with student selector and description notes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actual_session = models.ForeignKey(
        ActualSession,
        on_delete=models.CASCADE,
        related_name="student_feedback",
        help_text="Reference to the conducted session"
    )
    
    # Student reference
    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name="session_feedbacks",
        help_text="Student being given feedback"
    )
    
    # Description/Notes
    description = models.TextField(
        help_text="Feedback notes for the student"
    )
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('actual_session', 'student')
        ordering = ['-submitted_at']
        verbose_name = "Student Feedback"
        verbose_name_plural = "Student Feedback"
    
    def __str__(self):
        return f"Feedback - {self.actual_session} for {self.student.full_name}"


# TEACHER FEEDBACK REMOVED - Using SessionFeedback instead


# =========================
# FEEDBACK ANALYTICS - NEW
# =========================
class FeedbackAnalytics(models.Model):
    """
    Calculated analytics and metrics for session feedback
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    actual_session = models.ForeignKey(
        ActualSession,
        on_delete=models.CASCADE,
        related_name="feedback_analytics",
        help_text="Reference to the session"
    )
    
    # Student Feedback Analytics
    average_student_rating = models.FloatField(
        null=True, 
        blank=True,
        help_text="Average session rating from students"
    )
    
    understanding_percentage = models.FloatField(
        null=True, 
        blank=True,
        help_text="Percentage of students who understood the topic"
    )
    
    clarity_percentage = models.FloatField(
        null=True, 
        blank=True,
        help_text="Percentage of students who found teacher clear"
    )
    
    student_feedback_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of student feedback responses"
    )
    
    # Teacher Feedback Analytics
    engagement_score = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Engagement level score (1-3)"
    )
    
    completion_score = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Session completion score (1-3)"
    )
    
    # Correlation and Quality Metrics
    feedback_correlation_score = models.FloatField(
        null=True, 
        blank=True,
        help_text="Correlation between student and teacher feedback"
    )
    
    session_quality_score = models.FloatField(
        null=True, 
        blank=True,
        help_text="Overall session quality score"
    )
    
    # Metadata
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('actual_session',)
        verbose_name = "Feedback Analytics"
        verbose_name_plural = "Feedback Analytics"
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"Analytics - {self.actual_session}"
    
    def calculate_analytics(self):
        """Calculate analytics from feedback data"""
        # Get student feedback
        student_feedback = self.actual_session.student_feedback.all()
        
        if student_feedback.exists():
            # Calculate student metrics
            ratings = [f.session_rating for f in student_feedback]
            self.average_student_rating = sum(ratings) / len(ratings)
            
            understanding_yes = student_feedback.filter(topic_understanding='yes').count()
            self.understanding_percentage = (understanding_yes / student_feedback.count()) * 100
            
            clarity_yes = student_feedback.filter(teacher_clarity='yes').count()
            self.clarity_percentage = (clarity_yes / student_feedback.count()) * 100
            
            self.student_feedback_count = student_feedback.count()
        
        # Get teacher feedback
        teacher_feedback = self.actual_session.teacher_feedback.first()
        if teacher_feedback:
            # Convert engagement to score
            engagement_map = {'highly': 3, 'moderate': 2, 'low': 1}
            self.engagement_score = engagement_map.get(teacher_feedback.class_engagement, 0)
            
            # Convert completion to score
            completion_map = {'yes': 3, 'partly': 2, 'no': 1}
            self.completion_score = completion_map.get(teacher_feedback.session_completion, 0)
        
        # Calculate overall quality score
        if self.average_student_rating and self.engagement_score:
            self.session_quality_score = (
                (self.average_student_rating / 5) * 0.6 +
                (self.engagement_score / 3) * 0.4
            ) * 100
        
        self.save()


# =========================
# STUDENT GUARDIAN - NEW
# =========================
class StudentGuardian(models.Model):
    """
    Model to store guardian information for students
    Includes attachment assessment questions
    """
    RELATION_CHOICES = [
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('grandmother', 'Grandmother'),
        ('grandfather', 'Grandfather'),
        ('aunt', 'Aunt'),
        ('uncle', 'Uncle'),
        ('cousin', 'Cousin'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='guardians',
        help_text="Student this guardian is associated with"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Full name of the guardian"
    )
    
    relation = models.CharField(
        max_length=50,
        choices=RELATION_CHOICES,
        help_text="Relation to the student"
    )
    
    phone_number = models.CharField(
        max_length=20,
        help_text="Contact phone number"
    )
    
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address (optional)"
    )
    
    connection_notes = models.TextField(
        blank=True,
        help_text="Additional notes about connection (e.g., Primary contact, Emergency contact)"
    )
    
    # Attachment Assessment Questions
    attachment_q1 = models.BooleanField(
        default=False,
        help_text="Student shows strong emotional bond with this guardian"
    )
    
    attachment_q2 = models.BooleanField(
        default=False,
        help_text="Student seeks comfort/support from this guardian"
    )
    
    attachment_q3 = models.BooleanField(
        default=False,
        help_text="This guardian is actively involved in student's education"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Student Guardian"
        verbose_name_plural = "Student Guardians"
        indexes = [
            models.Index(fields=['student', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_relation_display()}) - {self.student.full_name}"
    
    @property
    def attachment_score(self):
        """Calculate attachment score based on questions"""
        score = 0
        if self.attachment_q1:
            score += 1
        if self.attachment_q2:
            score += 1
        if self.attachment_q3:
            score += 1
        return score


# =========================
# SESSION STEP STATUS - NEW (For Grouped Session Tracking)
# =========================
class SessionStepStatus(models.Model):
    """
    Tracks the completion status of each workflow step for a session.
    For grouped sessions, this is shared across all classes in the group.
    For non-grouped sessions, this is per class section.
    
    This model ensures step status persists across page refreshes by storing
    in the database instead of relying on browser localStorage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session reference
    planned_session = models.ForeignKey(
        PlannedSession,
        on_delete=models.CASCADE,
        related_name="step_statuses",
        help_text="Reference to the planned session (day)"
    )
    
    # Date of execution
    session_date = models.DateField(
        help_text="The calendar date when this session was conducted"
    )
    
    # Facilitator who completed the step
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="step_statuses",
        help_text="Facilitator who completed this step"
    )
    
    # Step number (1-7)
    step_number = models.PositiveIntegerField(
        choices=[
            (1, "Lesson Plan"),
            (2, "Preparation"),
            (3, "Conduct"),
            (4, "Attendance"),
            (5, "Upload"),
            (6, "Feedback"),
            (7, "Reward"),
        ],
        help_text="Which workflow step (1-7)"
    )
    
    # Status
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether this step is completed"
    )
    
    # Step content/data
    step_content = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON data associated with this step (images, notes, etc.)"
    )
    
    # Timestamps
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this step was marked as completed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Unique constraint: one status per step per session per date
        unique_together = ('planned_session', 'session_date', 'step_number')
        verbose_name = "Session Step Status"
        verbose_name_plural = "Session Step Statuses"
        ordering = ['session_date', 'step_number']
        indexes = [
            models.Index(fields=['planned_session', 'session_date']),
            models.Index(fields=['session_date', 'step_number']),
            models.Index(fields=['facilitator', 'session_date']),
        ]
    
    def __str__(self):
        status = "✓ Completed" if self.is_completed else "○ Pending"
        return f"Step {self.step_number} - {self.planned_session} on {self.session_date} - {status}"
    
    def mark_completed(self, facilitator=None, content=None):
        """Mark this step as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        if facilitator:
            self.facilitator = facilitator
        if content:
            self.step_content = content
        self.save()
    
    def mark_incomplete(self):
        """Mark this step as incomplete"""
        self.is_completed = False
        self.completed_at = None
        self.save()


# =========================
# ATTENDANCE SUMMARY (PHASE 2 SCALABILITY)
# =========================
class StudentAttendanceSummary(models.Model):
    """
    Pre-calculated attendance statistics for each enrollment.
    Updated in real-time via signals for instant reporting performance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    enrollment = models.OneToOneField(
        Enrollment, 
        on_delete=models.CASCADE, 
        related_name='attendance_summary',
        help_text="Direct link to student enrollment"
    )
    
    # Denormalized totals
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    leave_count = models.PositiveIntegerField(default=0)
    
    # Last activity tracking
    last_marked_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time any attendance was marked for this student"
    )
    
    total_sessions_conducted = models.PositiveIntegerField(
        default=0,
        help_text="Total conducted sessions for the class at last summary update"
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Attendance Summary"
        verbose_name_plural = "Student Attendance Summaries"
        indexes = [
            models.Index(fields=['enrollment', 'updated_at'], name='att_summary_perf_idx'),
        ]

    def __str__(self):
        return f"Summary: {self.enrollment.student.full_name}"

    @property
    def attendance_rate(self):
        """Calculates attendance rate on the fly from summary data"""
        total = self.present_count + self.absent_count
        if total == 0:
            return 0.0
        return round((self.present_count / total) * 100, 1)
