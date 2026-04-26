from django.apps import AppConfig


class ClassConfig(AppConfig):
    name = 'class'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals when the app is ready"""
        from . import signals
        from . import signals_optimization