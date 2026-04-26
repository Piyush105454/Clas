from django.contrib import admin
from .models import Cluster, School


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'state', 'created_at')
    list_filter = ('district', 'state', 'created_at')
    search_fields = ('name', 'district')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'district', 'state', 'description')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'udise', 'cluster', 'district', 'state', 'status')
    list_filter = ('district', 'state', 'cluster', 'status', 'created_at')
    search_fields = ('name', 'udise', 'district')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'udise', 'status')
        }),
        ('Location & Cluster', {
            'fields': ('cluster', 'block', 'district', 'state', 'area', 'latitude', 'longitude')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'contact_number', 'email', 'address')
        }),
        ('Media', {
            'fields': ('logo', 'profile_image')
        }),
        ('Statistics', {
            'fields': ('enrolled_students', 'avg_attendance_pct', 'validation_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
