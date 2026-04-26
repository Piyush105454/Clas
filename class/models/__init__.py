from .users import User, Role, FacilitatorAttendanceSummary
from .school import School  # ✅ THIS LINE FIXES YOUR ERROR
from .cluster import Cluster
from .class_section import ClassSection
from .facilitor_school import FacilitatorSchool
from .students import (
    Student, Enrollment, PlannedSession, ActualSession, Attendance, SessionStep,
    SessionBulkTemplate, LessonPlanUpload, SessionReward, SessionFeedback, 
    SessionPreparationChecklist, StudentFeedback, FeedbackAnalytics, CANCELLATION_REASONS,
    SessionStatus, AttendanceStatus, SessionCancellation, GroupedSession, StudentGuardian,
    ClassSessionProgress, SessionStepStatus, StudentAttendanceSummary
)
from .curriculum_sessions import (
    CurriculumSession, ImportHistory, 
    CurriculumUsageLog, SessionContentMapping, CurriculumStatus
)
from .calendar import (
    SupervisorCalendar, CalendarDate, OfficeWorkAttendance, DateType
)
from .facilitator_task import FacilitatorTask
from .student_performance import (
    Subject, PerformanceCutoff, StudentPerformance, StudentPerformanceSummary
)
from .student_growth import (
    StudentQuiz, StudentGrowthAnalysis
)

