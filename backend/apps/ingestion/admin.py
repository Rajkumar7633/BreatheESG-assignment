from django.contrib import admin
from .models import IngestionJob, RawRecord


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ['filename', 'source_type', 'status', 'total_rows', 'processed_rows',
                    'failed_rows', 'flagged_rows', 'created_by', 'created_at']
    list_filter = ['source_type', 'status', 'organization']
    search_fields = ['filename', 'file_hash']
    readonly_fields = ['file_hash', 'error_log']


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ['ingestion_job', 'row_number', 'created_at']
    readonly_fields = ['raw_data', 'parse_errors']
