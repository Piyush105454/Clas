"""
Management command to create ActualSession records for today based on CalendarDate
Run: python manage.py create_today_sessions
"""
from django.core.management.base import BaseCommand
from datetime import date
from importlib import import_module

# Import from class app (using getattr to avoid keyword conflict)
class_models = import_module('class.models')
ActualSession = class_models.ActualSession
PlannedSession = class_models.PlannedSession
ClassSection = class_models.ClassSection
CalendarDate = class_models.CalendarDate
DateType = class_models.DateType

class Command(BaseCommand):
    help = 'Create ActualSession records for all classes for today based on CalendarDate'

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(f'\nCreating sessions for {today}...\n')

        # Get calendar entry for today
        calendar_entry = CalendarDate.objects.filter(date=today, date_type=DateType.SESSION).first()
        
        if not calendar_entry:
            self.stdout.write(self.style.ERROR(f'❌ No calendar entry for {today}'))
            return

        self.stdout.write(f'✓ Calendar entry found: {calendar_entry}')
        
        # Get the day_number from calendar
        day_number = calendar_entry.day_number
        self.stdout.write(f'✓ Day number: {day_number}\n')

        # Get all active classes
        classes = ClassSection.objects.filter(is_active=True)
        self.stdout.write(f'Found {classes.count()} active classes\n')

        created_count = 0
        skipped_count = 0

        for cls in classes:
            # Check if session already exists for today
            existing = ActualSession.objects.filter(
                planned_session__class_section=cls,
                date=today
            ).first()

            if existing:
                skipped_count += 1
                continue

            # Get PlannedSession for this class at the current day_number
            planned_session = PlannedSession.objects.filter(
                class_section=cls,
                day_number=day_number,
                is_active=True
            ).first()

            if not planned_session:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️  {cls.display_name}: No PlannedSession for day {day_number}')
                )
                continue

            # Create ActualSession
            session = ActualSession.objects.create(
                planned_session=planned_session,
                date=today,
                status=0,  # PENDING
                facilitator=None
            )

            created_count += 1
            grouping_status = 'Grouped' if planned_session.grouped_session_id else 'Single'
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ {cls.display_name}: Created (Day {day_number}, {grouping_status})')
            )

        self.stdout.write(f'\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'✓ Created: {created_count} sessions'))
        self.stdout.write(f'⊘ Skipped: {skipped_count} sessions (already exist)')
        self.stdout.write('='*70 + '\n')
