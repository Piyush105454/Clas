import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
ActualSession = apps.get_model('class', 'ActualSession')

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically marks unmarked facilitator attendance as Leave or Absent (Monday-Saturday)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Number of past days to check (0 = today only)'
        )
        parser.add_argument(
            '--all-past',
            action='store_true',
            help='Mark ALL unmarked sessions in the past as Leave'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='leave',
            choices=['leave', 'absent'],
            help='Status to set for unmarked attendance (default: leave)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Count unmarked sessions without updating them'
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        days_back = options['days']
        all_past = options['all_past']
        status = options['status']
        dry_run = options['dry_run']

        # Determine the date range
        if all_past:
            # All unmarked sessions before today
            unmarked_sessions = ActualSession.objects.filter(
                date__lt=today,
                facilitator_attendance=''
            )
            date_info = "all past dates"
        elif days_back > 0:
            # Specific range of days including today
            start_date = today - timezone.timedelta(days=days_back)
            unmarked_sessions = ActualSession.objects.filter(
                date__gte=start_date,
                date__lte=today,
                facilitator_attendance=''
            )
            date_info = f"last {days_back} days (since {start_date})"
        else:
            # Default: Today only
            # Skip Sundays for today-only check
            if today.weekday() == 6:
                self.stdout.write(self.style.SUCCESS("Skipping Sunday. No auto-leave marking needed for today."))
                return

            unmarked_sessions = ActualSession.objects.filter(
                date=today,
                facilitator_attendance=''
            )
            date_info = f"today ({today})"

        # Exclude Sundays if we are doing a range/all
        if all_past or days_back > 0:
            # Sunday is weekday 6 (or 7 depending on settings, but usually 6 in Django __week_day)
            # In Django query, week_day=1 is Sunday
            unmarked_sessions = unmarked_sessions.exclude(date__week_day=1)

        count = unmarked_sessions.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"No unmarked attendance found for {date_info}."))
            return

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"[DRY RUN] Found {count} unmarked sessions for {date_info}."))
            return

        # Update them
        unmarked_sessions.update(facilitator_attendance=status)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully marked {count} sessions as '{status}' for {date_info}."))
        logger.info(f"Auto-marked {count} facilitator unmarked records as '{status}' for {date_info}.")
