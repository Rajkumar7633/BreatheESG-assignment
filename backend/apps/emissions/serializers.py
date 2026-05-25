from rest_framework import serializers
from .models import EmissionRecord, EmissionFactor


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = ['id', 'name', 'scope', 'factor_value', 'factor_unit',
                  'activity_unit', 'source_name', 'source_year', 'region']


class EmissionRecordSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    emission_factor_name = serializers.CharField(source='emission_factor.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    ingestion_job_id = serializers.CharField(source='raw_record.ingestion_job.id', read_only=True)
    raw_data = serializers.JSONField(source='raw_record.raw_data', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'source_type', 'source_type_display',
            'scope', 'scope_display', 'category', 'sub_category',
            'activity_description', 'activity_value', 'activity_unit',
            'co2e_kg', 'co2_kg', 'ch4_kg', 'n2o_kg',
            'period_start', 'period_end',
            'facility', 'cost_center', 'department', 'country',
            'status', 'status_display',
            'is_suspicious', 'suspicious_reasons',
            'is_locked', 'locked_at',
            'was_edited', 'original_values',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes',
            'emission_factor', 'emission_factor_name',
            'ingestion_job_id', 'raw_data',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'source_type', 'scope', 'category', 'emission_factor',
            'ingestion_job_id', 'raw_data', 'created_at', 'updated_at',
            'is_locked', 'locked_at',
        ]


class EmissionSummarySerializer(serializers.Serializer):
    """Aggregated stats for dashboard."""
    total_records = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    flagged_count = serializers.IntegerField()
    scope1_co2e_kg = serializers.DecimalField(max_digits=20, decimal_places=2)
    scope2_co2e_kg = serializers.DecimalField(max_digits=20, decimal_places=2)
    scope3_co2e_kg = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_co2e_kg = serializers.DecimalField(max_digits=20, decimal_places=2)
    by_source = serializers.DictField()
    by_scope = serializers.ListField()
    monthly_trend = serializers.ListField()
