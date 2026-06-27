from django.contrib import admin

from .models import AlertEvent, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'condition', 'threshold', 'user', 'is_active', 'created_at']
    list_filter = ['condition', 'is_active']
    search_fields = ['metric_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ['rule', 'metric', 'triggered_at']
    readonly_fields = ['id', 'created_at', 'updated_at', 'triggered_at']
