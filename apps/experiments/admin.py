from django.contrib import admin

from .models import Experiment, Metric, Run


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    list_filter = ['user']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ['run', 'name', 'value', 'step', 'created_at']
    list_filter = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
