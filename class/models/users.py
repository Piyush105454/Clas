import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# ---------------------------
# Custom User Manager
# ---------------------------
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, role=None, full_name=""):
        if not email:
            raise ValueError("Email is required")

        if role is None:
            raise ValueError("Role is required")

        user = self.model(
            email=self.normalize_email(email),
            full_name=full_name,
            role=role,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        admin_role, _ = Role.objects.get_or_create(id=0, defaults={"name": "Admin"})
        user = self.create_user(email=email, password=password, role=admin_role)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


# ---------------------------
# Roles Table
# ---------------------------
class Role(models.Model):
    id = models.SmallIntegerField(primary_key=True)  
    # 0=Admin, 1=Supervisor, 2=Facilitator

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# ---------------------------
# Custom User Table
# ---------------------------
class User(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)

    role = models.ForeignKey(Role, on_delete=models.PROTECT)

    # 🔹 NEW: Supervisor → Facilitator mapping
    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="facilitators",
        limit_choices_to={"role__id": 1}  # Only supervisors
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return f"{self.email} ({self.role.name})"


# =========================
# FACILITATOR SUMMARY (PHASE 2 SCALABILITY)
# =========================
class FacilitatorAttendanceSummary(models.Model):
    """
    Pre-calculated statistics for facilitators.
    Updated in real-time via signals for instant reporting performance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    facilitator = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='facilitator_summary',
        help_text="Link to the facilitator user"
    )
    
    # Denormalized totals
    sessions_conducted = models.PositiveIntegerField(
        default=0,
        help_text="Total number of sessions marked as CONDUCTED"
    )
    
    schools_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of active school assignments"
    )
    
    average_rating = models.FloatField(
        default=0.0,
        help_text="Lifetime average rating from FeedbackAnalytics"
    )
    
    # Last activity tracking
    last_active_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date of the last conducted session"
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Facilitator Attendance Summary"
        verbose_name_plural = "Facilitator Attendance Summaries"
        indexes = [
            models.Index(fields=['facilitator', 'updated_at'], name='fac_summary_perf_idx'),
        ]

    def __str__(self):
        return f"Summary: {self.facilitator.full_name}"
