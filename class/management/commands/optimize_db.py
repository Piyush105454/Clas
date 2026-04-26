"""
Django management command to optimize database performance
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Optimize database performance with indexes and maintenance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create performance indexes',
        )
        parser.add_argument(
            '--analyze-tables',
            action='store_true',
            help='Analyze table statistics',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Vacuum database (PostgreSQL only)',
        )

    def handle(self, *args, **options):
        if options['create_indexes']:
            self.create_performance_indexes()
        
        if options['analyze_tables']:
            self.analyze_tables()
        
        if options['vacuum']:
            self.vacuum_database()
        
        if not any([options['create_indexes'], options['analyze_tables'], options['vacuum']]):
            self.show_help()

    def create_performance_indexes(self):
        """Create indexes for better query performance"""
        self.stdout.write("Creating performance indexes...")
        
        indexes = [
            # School-related indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_status ON class_school(status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_created_at ON class_school(created_at);",
            
            # ClassSection indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_classsection_school_active ON class_classsection(school_id, is_active);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_classsection_level_section ON class_classsection(class_level, section);",
            
            # Enrollment indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enrollment_active ON class_enrollment(is_active);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enrollment_class_active ON class_enrollment(class_section_id, is_active);",
            
            # CurriculumSession indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_curriculum_language_day ON class_curriculumsession(language, day_number);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_curriculum_status ON class_curriculumsession(status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_curriculum_updated_at ON class_curriculumsession(updated_at);",
            
            # PlannedSession indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_planned_session_class_day ON class_plannedsession(class_section_id, day_number);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_planned_session_active ON class_plannedsession(is_active);",
            
            # ActualSession indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actual_session_date_status ON class_actualsession(date, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actual_session_planned ON class_actualsession(planned_session_id);",
            
            # FacilitatorSchool indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_facilitator_school_active ON class_facilitatorschool(facilitator_id, is_active);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_facilitator_school_school_active ON class_facilitatorschool(school_id, is_active);",
            
            # User indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_active ON class_user(role_id, is_active);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email_active ON class_user(email, is_active);",
        ]
        
        with connection.cursor() as cursor:
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(f"✓ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    if "already exists" in str(e):
                        self.stdout.write(f"- Index already exists: {index_sql.split('idx_')[1].split(' ')[0]}")
                    else:
                        self.stdout.write(f"✗ Error creating index: {e}")
        
        self.stdout.write(self.style.SUCCESS("Index creation completed!"))

    def analyze_tables(self):
        """Analyze table statistics for query optimization"""
        self.stdout.write("Analyzing table statistics...")
        
        tables = [
            'class_school',
            'class_classsection', 
            'class_enrollment',
            'class_curriculumsession',
            'class_plannedsession',
            'class_actualsession',
            'class_facilitatorschool',
            'class_user',
            'class_attendance',
        ]
        
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f"ANALYZE {table};")
                    self.stdout.write(f"✓ Analyzed: {table}")
                except Exception as e:
                    self.stdout.write(f"✗ Error analyzing {table}: {e}")
        
        self.stdout.write(self.style.SUCCESS("Table analysis completed!"))

    def vacuum_database(self):
        """Vacuum database to reclaim space and update statistics"""
        self.stdout.write("Running database vacuum...")
        
        with connection.cursor() as cursor:
            try:
                # Use VACUUM ANALYZE for better performance
                cursor.execute("VACUUM ANALYZE;")
                self.stdout.write(self.style.SUCCESS("Database vacuum completed!"))
            except Exception as e:
                self.stdout.write(f"✗ Error during vacuum: {e}")

    def show_help(self):
        """Show available optimization options"""
        self.stdout.write("Available optimization options:")
        self.stdout.write("  --create-indexes    Create performance indexes")
        self.stdout.write("  --analyze-tables    Analyze table statistics")
        self.stdout.write("  --vacuum           Vacuum database")
        self.stdout.write("")
        self.stdout.write("Example: python manage.py optimize_db --create-indexes --analyze-tables")