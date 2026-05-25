import uuid
from django.db import models
from django.conf import settings
from apps.core.models import Organization
from apps.ingestion.models import RawRecord


class EmissionFactor(models.Model):
    """
    Reference table for emission factors.
    Sourced from DEFRA 2024 (UK), EPA 2024 (US), and ICAO/IATA for aviation.
    Factor values are kg CO2e per activity unit.
    """
    SCOPE_CHOICES = [('1', 'Scope 1'), ('2', 'Scope 2'), ('3', 'Scope 3')]

    source_type = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)

    factor_value = models.DecimalField(max_digits=20, decimal_places=8)
    # Always expressed as 'kg_co2e_per_<unit>' e.g. kg_co2e_per_L, kg_co2e_per_kWh
    factor_unit = models.CharField(max_length=50)
    activity_unit = models.CharField(max_length=20)  # The denominator unit: L, kWh, km, night

    source_name = models.CharField(max_length=255)  # e.g. 'DEFRA 2024'
    source_year = models.IntegerField()
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    region = models.CharField(max_length=50, blank=True)

    # GHG breakdown so analysts can see CO2 vs CH4 vs N2O
    co2_factor = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    ch4_factor = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    n2o_factor = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-source_year', 'source_type']

    def __str__(self):
        return f"{self.name} ({self.source_name}): {self.factor_value} {self.factor_unit}"


class EmissionRecord(models.Model):
    """
    Normalized emission record — the canonical form.
    One row = one emission event with a known scope, period, and CO2e value.

    Design decisions:
    - activity_unit is always normalized (liters, kWh, km, nights) regardless of source
    - raw_record is immutable and always preserved for audit
    - status tracks review workflow state; is_locked prevents edits post-audit
    - suspicious_reasons is a list of strings so analysts understand WHY a flag was raised
    """
    SCOPE_CHOICES = [('1', 'Scope 1'), ('2', 'Scope 2'), ('3', 'Scope 3')]
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
    ]
    SOURCE_TYPES = [
        ('sap', 'SAP'),
        ('utility', 'Utility'),
        ('travel', 'Travel'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='emission_records'
    )

    # --- Source provenance (immutable after creation) ---
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    raw_record = models.OneToOneField(
        RawRecord, on_delete=models.PROTECT, related_name='emission_record'
    )
    emission_factor = models.ForeignKey(
        EmissionFactor, on_delete=models.PROTECT, null=True, blank=True
    )

    # --- GHG Protocol classification ---
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    # GHG Protocol category names: 'Stationary Combustion', 'Purchased Electricity',
    # 'Business Travel', 'Upstream Transportation', etc.
    category = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100, blank=True)  # e.g. 'Diesel', 'Natural Gas'

    # --- Normalized activity ---
    activity_description = models.TextField()
    activity_value = models.DecimalField(max_digits=20, decimal_places=6)
    # Always stored in a canonical unit regardless of what the source provided
    activity_unit = models.CharField(max_length=20)

    # --- Computed emissions (kg) ---
    co2e_kg = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    co2_kg = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    ch4_kg = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    n2o_kg = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    # --- Temporal ---
    period_start = models.DateField()
    period_end = models.DateField()

    # --- Organizational location ---
    facility = models.CharField(max_length=255, blank=True)
    cost_center = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # --- Review workflow ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # --- Suspicion flags ---
    is_suspicious = models.BooleanField(default=False)
    # Human-readable list: ["Value is 4.2x the monthly average", "Missing facility code"]
    suspicious_reasons = models.JSONField(default=list)

    # --- Audit lock ---
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    # --- Manual edit tracking ---
    was_edited = models.BooleanField(default=False)
    # Snapshot of fields before the last manual edit
    original_values = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_start', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'scope', 'status']),
            models.Index(fields=['organization', 'source_type', 'period_start']),
            models.Index(fields=['is_suspicious', 'status']),
            models.Index(fields=['organization', 'period_start', 'period_end']),
        ]

    def __str__(self):
        return f"{self.organization} | Scope {self.scope} | {self.category} | {self.period_start}"
