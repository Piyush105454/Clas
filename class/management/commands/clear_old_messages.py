"""
Management command to clear old Django messages from sessions
"""

from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import pickle
import base64


class Command(BaseCommand):
    help = 'Clear old Django messages from user sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Clear messages older than this many days (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleared without actually clearing'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"Looking for sessions with messages older than {days} days...")
        
        sessions_processed = 0
        messages_cleared = 0
        
        # Get all sessions
        for session in Session.objects.filter(expire_date__lt=cutoff_date):
            try:
                # Decode session data
                session_data = session.get_decoded()
                
                # Check if session has messages
                if '_messages' in session_data:
                    messages_data = session_data['_messages']
                    
                    if messages_data:
                        messages_cleared += len(messages_data)
                        sessions_processed += 1
                        
                        if not dry_run:
                            # Clear messages from session
                            del session_data['_messages']
                            session.session_data = session.encode(session_data)
                            session.save()
                        
                        self.stdout.write(
                            f"Session {session.session_key}: {len(messages_data)} messages"
                        )
                        
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Error processing session {session.session_key}: {e}")
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: Would clear {messages_cleared} messages from {sessions_processed} sessions"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleared {messages_cleared} messages from {sessions_processed} sessions"
                )
            )
            
        # Also clear expired sessions
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        expired_count = expired_sessions.count()
        
        if not dry_run:
            expired_sessions.delete()
            
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would delete' if dry_run else 'Deleted'} {expired_count} expired sessions"
            )
        )