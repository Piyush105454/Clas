"""
Management command to generate test data for student growth analysis
Creates quiz scores and attendance records for testing
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from ...models import Enrollment, StudentQuiz, Attendance, AttendanceStatus


class Command(BaseCommand):
    help = 'Generate test data for student growth analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enrollment-id',
            type=str,
            help='Specific enrollment ID to generate data for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate data for all students with insufficient data',
        )
        parser.add_argument(
            '--quizzes',
            type=int,
            default=5,
            help='Number of quiz scores to generate (default: 5)',
        )
        parser.add_argument(
            '--attendance',
            type=int,
            default=10,
            help='Number of attendance records to generate (default: 10)',
        )

    def handle(self, *args, **options):
        enrollment_id = options.get('enrollment_id')
        generate_all = options.get('all')
        num_quizzes = options.get('quizzes', 5)
        num_attendance = options.get('attendance', 10)

        if enrollment_id:
            try:
                enrollment = Enrollment.objects.get(id=enrollment_id)
                self.generate_data_for_enrollment(enrollment, num_quizzes, num_attendance)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully generated test data for {enrollment.student.full_name}'
                    )
                )
            except Enrollment.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Enrollment with ID {enrollment_id} not found')
                )
        elif generate_all:
            enrollments = Enrollment.objects.filter(is_active=True)
            count = 0
            for enrollment in enrollments:
                quiz_count = StudentQuiz.objects.filter(enrollment=enrollment).count()
                attendance_count = Attendance.objects.filter(enrollment=enrollment).count()
                
                # Generate data if insufficient
                if quiz_count < 3 or attendance_count < 5:
                    self.generate_data_for_enrollment(enrollment, num_quizzes, num_attendance)
                    count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully generated test data for {count} students'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify --enrollment-id or --all flag'
                )
            )

    def generate_data_for_enrollment(self, enrollment, num_quizzes, num_attendance):
        """Generate test data for a specific enrollment"""
        
        # Generate quiz scores
        today = timezone.now().date()
        for i in range(num_quizzes):
            quiz_date = today - timedelta(days=(num_quizzes - i) * 7)
            quiz_month = quiz_date.strftime('%Y-%m')
            
            # Generate realistic scores with slight improvement trend
            base_score = 50 + (i * 5)  # Gradual improvement
            score = max(0, min(100, base_score + random.randint(-10, 10)))
            
            StudentQuiz.objects.get_or_create(
                enrollment=enrollment,
                quiz_date=quiz_date,
                defaults={
                    'quiz_month': quiz_month,
                    'score': score,
                    'total_marks': 100,
                    'questions_attempted': random.randint(15, 20),
                    'correct_answers': int(score / 5),
                    'notes': f'Test quiz generated on {quiz_date}',
                }
            )
        
        # Generate attendance records
        for i in range(num_attendance):
            attendance_date = today - timedelta(days=(num_attendance - i))
            
            # 80% attendance rate
            status = AttendanceStatus.PRESENT if random.random() < 0.8 else AttendanceStatus.ABSENT
            
            # Try to get or create attendance record
            from ...models import ActualSession
            
            # Find a session on this date for this class
            sessions = ActualSession.objects.filter(
                date=attendance_date,
                planned_session__class_section=enrollment.class_section
            )
            
            if sessions.exists():
                session = sessions.first()
                Attendance.objects.get_or_create(
                    enrollment=enrollment,
                    actual_session=session,
                    defaults={
                        'status': status,
                        'marked_at': timezone.now(),
                        'visible_change_notes': 'Generated test data',
                        'invisible_change_notes': 'Generated test data',
                    }
                )
