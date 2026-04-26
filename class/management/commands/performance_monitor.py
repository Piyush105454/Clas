"""
Django management command to monitor and optimize performance
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor and optimize application performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear all cache entries',
        )
        parser.add_argument(
            '--analyze-queries',
            action='store_true',
            help='Analyze slow database queries',
        )
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='Warm up critical cache entries',
        )

    def handle(self, *args, **options):
        if options['clear_cache']:
            self.clear_cache()
        
        if options['analyze_queries']:
            self.analyze_queries()
        
        if options['warm_cache']:
            self.warm_cache()
        
        if not any([options['clear_cache'], options['analyze_queries'], options['warm_cache']]):
            self.show_performance_stats()

    def clear_cache(self):
        """Clear all cache entries"""
        self.stdout.write("Clearing cache...")
        cache.clear()
        self.stdout.write(
            self.style.SUCCESS("Cache cleared successfully!")
        )

    def analyze_queries(self):
        """Analyze database queries for performance issues"""
        self.stdout.write("Analyzing database queries...")
        
        # This would typically analyze query logs
        # For now, we'll show current connection info
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            self.stdout.write(f"Database version: {version}")
            
            # Show current connections
            cursor.execute("""
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE state = 'active';
            """)
            active_connections = cursor.fetchone()[0]
            self.stdout.write(f"Active connections: {active_connections}")

    def warm_cache(self):
        """Warm up critical cache entries"""
        self.stdout.write("Warming up cache...")
        
        from class.models import School, CurriculumSession, ClassSection
        
        # Cache school data
        schools = list(School.objects.select_related().prefetch_related(
            'classsection_set', 'facilitators'
        ))
        cache.set('schools_warmed', schools, 3600)
        
        # Cache curriculum session counts
        hindi_count = CurriculumSession.objects.filter(language='hindi').count()
        english_count = CurriculumSession.objects.filter(language='english').count()
        cache.set('curriculum_counts', {
            'hindi': hindi_count,
            'english': english_count
        }, 3600)
        
        self.stdout.write(
            self.style.SUCCESS(f"Cache warmed with {len(schools)} schools and curriculum counts")
        )

    def show_performance_stats(self):
        """Show current performance statistics"""
        self.stdout.write("=== Performance Statistics ===")
        
        # Cache stats
        try:
            cache_info = cache._cache.get_stats()
            self.stdout.write(f"Cache entries: {len(cache_info) if cache_info else 'N/A'}")
        except:
            self.stdout.write("Cache stats: Not available")
        
        # Database stats
        from class.models import School, CurriculumSession, User, ClassSection
        
        stats = {
            'Schools': School.objects.count(),
            'Users': User.objects.count(),
            'Classes': ClassSection.objects.count(),
            'Curriculum Sessions': CurriculumSession.objects.count(),
        }
        
        for name, count in stats.items():
            self.stdout.write(f"{name}: {count}")
        
        # Memory usage (if available)
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.stdout.write(f"Memory usage: {memory_mb:.1f} MB")
        except ImportError:
            self.stdout.write("Memory stats: psutil not available")