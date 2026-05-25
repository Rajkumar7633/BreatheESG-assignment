from rest_framework import serializers
from .models import IngestionJob, RawRecord


class IngestionJobSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            'id', 'source_type', 'source_type_display', 'status', 'status_display',
            'filename', 'total_rows', 'processed_rows', 'failed_rows', 'flagged_rows',
            'created_by', 'created_by_name', 'created_at', 'completed_at',
            'error_log', 'metadata',
        ]
        read_only_fields = [
            'id', 'status', 'total_rows', 'processed_rows', 'failed_rows',
            'flagged_rows', 'created_at', 'completed_at', 'error_log',
        ]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ['id', 'row_number', 'raw_data', 'parse_errors', 'created_at']
