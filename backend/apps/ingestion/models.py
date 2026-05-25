import uuid
from django.db import models
from django.conf import settings
from apps.core.models import Organization


class IngestionJob(models.Model):
    SOURCE_TYPES = [
        ('sap', 'SAP Fuel & Procurement'),
        ('utility', 'Utility Electricity'),
        ('travel', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='ingestion_jobs'
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    filename = models.CharField(max_length=255, blank=True)
    # SHA-256 fingerprint for duplicate detection
    file_hash = models.CharField(max_length=64, blank=True)

    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    flagged_rows = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='ingestion_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_source_type_display()} — {self.filename} ({self.status})"


class RawRecord(models.Model):
    """
    Stores the original, un-normalized record exactly as received.
    This is the immutable source-of-truth: if we re-derive emissions later,
    we re-derive them from here, not from EmissionRecord.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingestion_job = models.ForeignKey(
        IngestionJob, on_delete=models.CASCADE, related_name='raw_records'
    )
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    parse_errors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ingestion_job', 'row_number']
        unique_together = [['ingestion_job', 'row_number']]

    def __str__(self):
        return f"Row {self.row_number} of {self.ingestion_job}"
