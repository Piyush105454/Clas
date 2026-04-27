"""
Integration tests for Supervisor Facilitator Daily Profile
Tests the complete workflow of viewing daily profile data
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from django.urls import reverse

from .models import (
    User, FacilitatorSchool, School, ClassSection, ActualSession,
    PlannedSession, Enrollment, Student, FacilitatorTask, SessionFeedback,
    LessonPlanUpload, Attendance
)
from .services.daily_profile_service import DailyProfileService

User = get_user_model()


class DailyProfileServiceTests(TestCase):
    """Test the DailyProfileService"""
    
    def setUp(self):
        """Set up test data"""
        # Create supervisor
        self.supervisor = User.objects.create_user(
            email='supervisor@test.com',
            password='testpass123',
            full_name='Test Supervisor',
            role=self._get_or_create_role('SUPERVISOR')
        )
        
        # Create facilitator
        self.facilitator = User.objects.create_user(
            email='facilitator@test.com',
            password='testpass123',
            full_name='Test Facilitator',
            role=self._get_or_create_role('FACILITATOR')
        )
        
        # Create school
        self.school = School.objects.create(
            name='Test School',
            udise='UDISE001',
            district='Test District',
            state='Test State'
        )
        
        # Assign facilitator to school
        FacilitatorSchool.objects.create(
            facilitator=self.facilitator,
            school=self.school,
            is_active=True
        )
        
        # Create class section
        self.class_section = ClassSection.objects.create(
            school=self.school,
            class_level='5',
            section='A'
        )
        
        # Create students
        self.students = []
        self.enrollments = []
        for i in range(5):
            student = Student.objects.create(
                full_name=f'Student {i}',
                enrollment_number=f'STU{i:03d}'
            )
            self.students.append(student)
            
            # Enroll student
            enrollment = Enrollment.objects.create(
                student=student,
                class_section=self.class_section,
                start_date=timezone.now().date(),
                is_active=True
            )
            self.enrollments.append(enrollment)
        
        # Create planned session
        self.planned_session = PlannedSession.objects.create(
            class_section=self.class_section,
            day_number=1,
            title='Test Session'
        )
        
        # Create actual session for today
        self.today = timezone.now().date()
        self.actual_session = ActualSession.objects.create(
            planned_session=self.planned_session,
            facilitator=self.facilitator,
            date=self.today,
            status=1 # Conducted
        )
        
        # Create attendance records
        for i, enrollment in enumerate(self.enrollments[:3]):  # 3 present, 2 absent
            Attendance.objects.create(
                actual_session=self.actual_session,
                enrollment=enrollment,
                status=1 # Present
            )
        
        for enrollment in self.enrollments[3:]:  # 2 absent
            Attendance.objects.create(
                actual_session=self.actual_session,
                enrollment=enrollment,
                status=2 # Absent
            )
    
    def _get_or_create_role(self, role_name):
        """Helper to get or create a role"""
        from .models import Role
        role_map = {
            'ADMIN': 0,
            'SUPERVISOR': 1,
            'FACILITATOR': 2
        }
        role_id = role_map.get(role_name.upper(), 1)
        role, _ = Role.objects.get_or_create(id=role_id, defaults={"name": role_name})
        return role
    
    def test_get_daily_profile_returns_all_data(self):
        """Test that get_daily_profile returns all required data"""
        service = DailyProfileService(self.facilitator, self.today)
        profile = service.get_daily_profile()
        
        # Check structure
        self.assertIn('facilitator', profile)
        self.assertIn('selected_date', profile)
        self.assertIn('sessions', profile)
        self.assertIn('lesson_plans', profile)
        self.assertIn('tasks', profile)
        self.assertIn('feedback', profile)
        self.assertIn('attendance_metrics', profile)
    
    def test_get_sessions_returns_correct_data(self):
        """Test that sessions are returned with correct data"""
        service = DailyProfileService(self.facilitator, self.today)
        profile = service.get_daily_profile()
        
        sessions = profile['sessions']
        self.assertEqual(len(sessions), 1)
        
        session = sessions[0]
        self.assertEqual(session['name'], 'Test Session')
        self.assertEqual(session['students_present'], 3)
        self.assertEqual(session['students_enrolled'], 5)
        self.assertEqual(session['attendance_rate'], 60)  # 3/5 = 60%
    
    def test_attendance_rate_calculation(self):
        """Test that attendance rate is calculated correctly"""
        service = DailyProfileService(self.facilitator, self.today)
        profile = service.get_daily_profile()
        
        metrics = profile['attendance_metrics']
        self.assertEqual(metrics['overall_rate'], 60)  # 3/5 = 60%
        self.assertEqual(metrics['total_present'], 3)
        self.assertEqual(metrics['total_enrolled'], 5)
    
    def test_empty_date_returns_empty_data(self):
        """Test that a date with no sessions returns empty data"""
        future_date = self.today + timedelta(days=10)
        service = DailyProfileService(self.facilitator, future_date)
        profile = service.get_daily_profile()
        
        self.assertEqual(len(profile['sessions']), 0)
        self.assertEqual(profile['attendance_metrics']['overall_rate'], 0)
    
    def test_validate_date_with_valid_date(self):
        """Test date validation with valid date"""
        valid_date = DailyProfileService.validate_date('2024-01-15')
        self.assertIsNotNone(valid_date)
        self.assertEqual(valid_date.year, 2024)
        self.assertEqual(valid_date.month, 1)
        self.assertEqual(valid_date.day, 15)
    
    def test_validate_date_with_invalid_date(self):
        """Test date validation with invalid date"""
        invalid_date = DailyProfileService.validate_date('invalid-date')
        self.assertIsNone(invalid_date)
    
    def test_facilitator_info_is_correct(self):
        """Test that facilitator info is returned correctly"""
        service = DailyProfileService(self.facilitator, self.today)
        profile = service.get_daily_profile()
        
        facilitator_info = profile['facilitator']
        self.assertEqual(facilitator_info['name'], 'Test Facilitator')
        self.assertEqual(facilitator_info['email'], 'facilitator@test.com')


class DailyProfileViewTests(TestCase):
    """Test the daily profile views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create supervisor
        self.supervisor = User.objects.create_user(
            email='supervisor@test.com',
            password='testpass123',
            full_name='Test Supervisor',
            role=self._get_or_create_role('SUPERVISOR')
        )
        
        # Create facilitator
        self.facilitator = User.objects.create_user(
            email='facilitator@test.com',
            password='testpass123',
            full_name='Test Facilitator',
            role=self._get_or_create_role('FACILITATOR')
        )
        
        # Create school
        self.school = School.objects.create(
            name='Test School',
            udise='UDISE001',
            district='Test District',
            state='Test State'
        )
        
        # Assign facilitator to school
        FacilitatorSchool.objects.create(
            facilitator=self.facilitator,
            school=self.school,
            is_active=True
        )
    
    def _get_or_create_role(self, role_name):
        """Helper to get or create a role"""
        from .models import Role
        role_map = {
            'ADMIN': 0,
            'SUPERVISOR': 1,
            'FACILITATOR': 2
        }
        role_id = role_map.get(role_name.upper(), 1)
        role, _ = Role.objects.get_or_create(id=role_id, defaults={"name": role_name})
        return role
    
    def test_daily_profile_page_loads(self):
        """Test that the daily profile page loads successfully"""
        self.client.login(email='supervisor@test.com', password='testpass123')
        
        url = reverse('supervisor_facilitator_daily_profile', args=[self.facilitator.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'supervisor/facilitators/daily_profile.html')
    
    def test_daily_profile_with_date_parameter(self):
        """Test that the daily profile page accepts date parameter"""
        self.client.login(email='supervisor@test.com', password='testpass123')
        
        url = reverse('supervisor_facilitator_daily_profile', args=[self.facilitator.id])
        response = self.client.get(url, {'date': '2024-01-15'})
        
        self.assertEqual(response.status_code, 200)
    
    def test_daily_profile_api_returns_json(self):
        """Test that the API endpoint returns JSON"""
        self.client.login(email='supervisor@test.com', password='testpass123')
        
        url = reverse('supervisor_facilitator_daily_profile_api', args=[self.facilitator.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertIn('facilitator', data)
        self.assertIn('sessions', data)
        self.assertIn('attendance_metrics', data)
    
    def test_daily_profile_requires_login(self):
        """Test that the daily profile page requires login"""
        url = reverse('supervisor_facilitator_daily_profile', args=[self.facilitator.id])
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_daily_profile_requires_supervisor_role(self):
        """Test that the daily profile page requires supervisor role"""
        # Create a non-supervisor user
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            full_name='Test User',
            role=self._get_or_create_role('FACILITATOR')
        )
        
        self.client.login(email='user@test.com', password='testpass123')
        
        url = reverse('supervisor_facilitator_daily_profile', args=[self.facilitator.id])
        response = self.client.get(url)
        
        # Should return 403 or redirect
        self.assertIn(response.status_code, [302, 403])
