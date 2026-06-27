from django.contrib import admin

from .models import Pipeline, PipelineStage


class PipelineStageInline(admin.TabularInline):
    model = PipelineStage
    extra = 0
    fields = ['name', 'status', 'order', 'depends_on', 'started_at', 'ended_at']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    list_filter = ['user']
    search_fields = ['name']
    inlines = [PipelineStageInline]


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'pipeline', 'status', 'order']
    list_filter = ['status', 'pipeline']
    search_fields = ['name']
