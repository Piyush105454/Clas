"""
Management command to manually trigger student growth analysis
"""

from django.core.management.base import BaseCommand
from ...models import Enrollment, StudentGrowthAnalysis
from ...services.student_growth_service import StudentGrowthAnalysisService


class Command(BaseCommand):
    help = 'Manually trigger student growth analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enrollment-id',
            type=str,
            help='Specific enrollment ID to analyze',
        )
        parser.add_argument(
            '--school-id',
            type=str,
            help='Analyze all students in a school',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Analyze all students',
        )

    def handle(self, *args, **options):
        enrollment_id = options.get('enrollment_id')
        school_id = options.get('school_id')
        analyze_all = options.get('all')

        if enrollment_id:
            try:
                enrollment = Enrollment.objects.get(id=enrollment_id)
                analysis = StudentGrowthAnalysisService.update_growth_analysis(enrollment)
                
                if analysis:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Growth analysis completed for {enrollment.student.full_name}\n'
                            f'  Growth Score: {analysis.growth_score:.1f}\n'
                            f'  Risk Level: {analysis.get_risk_level_display()}\n'
                            f'  Cluster: {analysis.get_student_cluster_display()}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Insufficient data for {enrollment.student.full_name}'
                        )
                    )
            except Enrollment.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ Enrollment with ID {enrollment_id} not found')
                )
        
        elif school_id:
            result = StudentGrowthAnalysisService.analyze_school_students(school_id)
            
            if 'error' in result:
                self.stdout.write(self.style.ERROR(f'✗ {result["error"]}'))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Analyzed {result["total_students_analyzed"]} students\n'
                        f'  At-Risk Students: {result["at_risk_count"]}'
                    )
                )
                
                if result['at_risk_students']:
                    self.stdout.write('\nAt-Risk Students:')
                    for student in result['at_risk_students']:
                        self.stdout.write(
                            f'  - {student["student_name"]} (Score: {student["growth_score"]:.1f})'
                        )
        
        elif analyze_all:
            enrollments = Enrollment.objects.filter(is_active=True)
            total = enrollments.count()
            analyzed = 0
            at_risk = 0
            
            self.stdout.write(f'Analyzing {total} students...')
            
            for enrollment in enrollments:
                analysis = StudentGrowthAnalysisService.update_growth_analysis(enrollment)
                if analysis and analysis.is_sufficient_data:
                    analyzed += 1
                    if analysis.is_at_risk:
                        at_risk += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Analysis complete!\n'
                    f'  Total Students: {total}\n'
                    f'  Analyzed: {analyzed}\n'
                    f'  At-Risk: {at_risk}'
                )
            )
        
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify --enrollment-id, --school-id, or --all flag'
                )
            )
