from django.core.management.base import BaseCommand
from django.apps import apps

Subject = apps.get_model('class', 'Subject')


class Command(BaseCommand):
    help = 'Populate default subjects for student performance tracking'

    def handle(self, *args, **options):
        subjects_data = [
            {'name': 'Hindi', 'code': 'HIN'},
            {'name': 'English', 'code': 'ENG'},
            {'name': 'Mathematics', 'code': 'MATH'},
            {'name': 'Science', 'code': 'SCI'},
            {'name': 'Social Studies', 'code': 'SS'},
            {'name': 'Physical Education', 'code': 'PE'},
            {'name': 'Art', 'code': 'ART'},
            {'name': 'Music', 'code': 'MUS'},
            {'name': 'Computer Science', 'code': 'CS'},
            {'name': 'General Knowledge', 'code': 'GK'},
        ]
        
        created_count = 0
        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                code=subject_data['code'],
                defaults={
                    'name': subject_data['name'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created subject: {subject.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Subject already exists: {subject.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal subjects created: {created_count}')
        )
