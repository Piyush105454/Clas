from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Aggressive Global Repair: Synchronizes every class session sequence with physical conduct history'

    def handle(self, *args, **options):
        ClassSection = apps.get_model('class', 'ClassSection')
        PlannedSession = apps.get_model('class', 'PlannedSession')
        ActualSession = apps.get_model('class', 'ActualSession')
        ClassSessionProgress = apps.get_model('class', 'ClassSessionProgress')
        
        # Use importlib to avoid reserved 'class' keyword issues in some environments
        import importlib
        session_mgmt = importlib.import_module('class.session_management')
        SessionSequenceCalculator = session_mgmt.SessionSequenceCalculator
        class_models = importlib.import_module('class.models')
        SessionStatus = class_models.SessionStatus
        
        self.stdout.write(self.style.MIGRATE_HEADING('\n--- GLOBAL SESSION SEQUENCE REPAIR ---\n'))
        
        classes = ClassSection.objects.all().select_related('school')
        total = classes.count()
        repaired = 0
        errors = 0
        
        self.stdout.write(f"Auditing {total} classes...\n")
        
        for i, class_section in enumerate(classes):
            try:
                # 4. PERFORM CHRONO-SHIFTING (Gap Normalization)
                # This ensures that if a class has 3 physical records, they are ALWAYS Days 1, 2, and 3.
                history = list(ActualSession.objects.filter(
                    planned_session__class_section=class_section,
                    planned_session__day_number__lte=150,
                    status__in=[SessionStatus.CONDUCTED, SessionStatus.CANCELLED]
                ).order_by('date', 'created_at'))
                
                shift_count = 0
                for j, session in enumerate(history):
                    target_day = j + 1
                    if session.planned_session.day_number != target_day:
                        try:
                            correct_ps = PlannedSession.objects.get(class_section=class_section, day_number=target_day)
                            session.planned_session = correct_ps
                            session.save(update_fields=['planned_session'])
                            shift_count += 1
                        except Exception:
                            pass
                
                if shift_count > 0:
                    self.stdout.write(self.style.SUCCESS(f" [REPAIRED] Shifted {shift_count} sessions to fill gaps for {class_section}"))

                # 5. RE-SYNC TRACKER
                # The next day is simply history_count + 1
                final_next_day = len(history) + 1
                if final_next_day > 150: final_next_day = 151
                
                ClassSessionProgress.objects.filter(class_section=class_section).update(day_number=final_next_day)
                
                # Recalculate and display result
                next_session = SessionSequenceCalculator.get_next_pending_session(class_section)
                next_day_num = next_session.day_number if next_session else "N/A"
                self.stdout.write(f"[{i+1}/{total}] {class_section.display_name} -> Day {next_day_num}")
                repaired += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{i+1}/{total}] Failed to repair {class_section}: {e}"))
                errors += 1
        
        self.stdout.write(self.style.SUCCESS(f'\nRepair Complete!'))
        self.stdout.write(f'Classes scanned/healed: {repaired}')
        if errors > 0:
            self.stdout.write(self.style.WARNING(f'Errors encountered: {errors}'))
