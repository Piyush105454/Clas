"""
Management command to initialize 1-150 planned sessions for all classes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from class.models import ClassSection, PlannedSession
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize 1-150 planned sessions for all classes that do not have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if some sessions exist',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting class session initialization...'))
        
        # Get all class sections
        all_classes = ClassSection.objects.all().select_related('school')
        
        if not all_classes.exists():
            self.stdout.write(self.style.WARNING('No classes found in the system.'))
            return
        
        classes_updated = 0
        total_sessions_created = 0
        
        for class_section in all_classes:
            # Check existing sessions
            existing_count = PlannedSession.objects.filter(
                class_section=class_section,
                is_active=True
            ).count()
            
            if existing_count == 0 or (options['force'] and existing_count < 150):
                try:
                    with transaction.atomic():
                        if options['force'] and existing_count > 0:
                            # Get existing day numbers
                            existing_days = set(
                                PlannedSession.objects.filter(
                                    class_section=class_section,
                                    is_active=True
                                ).values_list('day_number', flat=True)
                            )
                            missing_days = set(range(1, 151)) - existing_days
                        else:
                            missing_days = set(range(1, 151))
                        
                        if missing_days:
                            sessions_to_create = []
                            for day_number in sorted(missing_days):
                                session = PlannedSession(
                                    class_section=class_section,
                                    day_number=day_number,
                                    title=f"Day {day_number} Session",
                                    description=f"Session for day {day_number}",
                                    sequence_position=day_number,
                                    is_required=True,
                                    is_active=True
                                )
                                sessions_to_create.append(session)
                            
                            # Bulk create sessions
                            PlannedSession.objects.bulk_create(sessions_to_create)
                            
                            classes_updated += 1
                            sessions_created = len(sessions_to_create)
                            total_sessions_created += sessions_created
                            
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✅ Created {sessions_created} sessions for {class_section.school.name} - {class_section.class_level}-{class_section.section}'
                                )
                            )
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ Error creating sessions for {class_section}: {e}'
                        )
                    )
            else:
                self.stdout.write(
                    f'⏭️  Skipping {class_section.school.name} - {class_section.class_level}-{class_section.section} (already has {existing_count} sessions)'
                )
        
        # Summary
        if classes_updated > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Successfully initialized {total_sessions_created} sessions for {classes_updated} classes!'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  No classes needed session initialization. All classes already have sessions.'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('Session initialization complete!'))