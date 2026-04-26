"""
Management command to set up grouped sessions for classes
Usage: python manage.py setup_grouped_sessions
"""
from django.core.management.base import BaseCommand
from class.models import PlannedSession, GroupedSession, ClassSection
from uuid import uuid4


class Command(BaseCommand):
    help = 'Set up grouped sessions for classes'

    def handle(self, *args, **options):
        self.stdout.write("Setting up grouped sessions...\n")
        
        # Get all active classes
        classes = ClassSection.objects.filter(is_active=True).order_by('school__name', 'display_name')
        
        if not classes.exists():
            self.stdout.write(self.style.WARNING("No classes found"))
            return
        
        self.stdout.write(f"Found {classes.count()} classes\n")
        
        # Group classes by school
        schools = {}
        for cls in classes:
            if cls.school_id not in schools:
                schools[cls.school_id] = []
            schools[cls.school_id].append(cls)
        
        # For each school, create grouped sessions
        for school_id, school_classes in schools.items():
            school_name = school_classes[0].school.name
            self.stdout.write(f"\n{school_name}:")
            self.stdout.write(f"  Classes: {', '.join([c.display_name for c in school_classes])}")
            
            # Create groupings (example: pair consecutive classes)
            # You can modify this logic based on your needs
            groupings = []
            for i in range(0, len(school_classes), 2):
                if i + 1 < len(school_classes):
                    groupings.append([school_classes[i], school_classes[i+1]])
                else:
                    groupings.append([school_classes[i]])
            
            self.stdout.write(f"  Groupings: {len(groupings)}")
            
            for idx, grouping in enumerate(groupings):
                # Create a GroupedSession
                grouped_session = GroupedSession.objects.create(
                    name=f"{school_name} Group {idx+1}"
                )
                
                class_names = ', '.join([c.display_name for c in grouping])
                self.stdout.write(f"    Group {idx+1}: {class_names}")
                
                # Create PlannedSessions for each class in the group
                for day_num in range(1, 6):  # Assuming 5 days
                    for cls in grouping:
                        # Check if ungrouped session exists
                        ungrouped = PlannedSession.objects.filter(
                            class_section=cls,
                            day_number=day_num,
                            grouped_session_id__isnull=True,
                            is_active=True
                        ).first()
                        
                        if ungrouped:
                            # Create grouped version
                            PlannedSession.objects.get_or_create(
                                class_section=cls,
                                day_number=day_num,
                                grouped_session_id=grouped_session.id,
                                defaults={'is_active': True}
                            )
        
        self.stdout.write(self.style.SUCCESS("\n✓ Grouped sessions set up successfully!"))
        self.stdout.write("\nNow facilitators can use the 'Change' button to switch between grouped and ungrouped sessions.")
