from django.contrib import admin
from .models import ReportTemplate, SavedReport

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_default')
    list_filter = ('is_default',)

@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')