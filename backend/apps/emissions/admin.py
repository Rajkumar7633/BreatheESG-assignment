from django.contrib import admin
from .models import EmissionRecord, EmissionFactor


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['name', 'scope', 'factor_value', 'factor_unit', 'source_name', 'source_year', 'region']
    list_filter = ['scope', 'region', 'source_year']
    search_fields = ['name', 'source_type']


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'scope', 'category', 'activity_value', 'activity_unit',
        'co2e_kg', 'period_start', 'status', 'is_suspicious', 'is_locked'
    ]
    list_filter = ['scope', 'source_type', 'status', 'is_suspicious', 'is_locked', 'organization']
    search_fields = ['activity_description', 'facility', 'category']
    readonly_fields = ['raw_record', 'is_locked', 'locked_at', 'original_values']
