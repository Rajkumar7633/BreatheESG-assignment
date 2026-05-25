import uuid
from django.db import models
from django.conf import settings
from apps.emissions.models import EmissionRecord


class ReviewDecision(models.Model):
    """
    Immutable audit trail of every review action.
    Each approve/reject/flag/edit creates a new row — nothing is updated in place.
    This gives auditors a complete chain of custody.
    """
    ACTION_CHOICES = [
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('flag', 'Flagged'),
        ('unflag', 'Unflagged'),
        ('edit', 'Edited'),
        ('lock', 'Locked for Audit'),
        ('bulk_approve', 'Bulk Approved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emission_record = models.ForeignKey(
        EmissionRecord, on_delete=models.CASCADE, related_name='review_decisions'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='review_decisions'
    )
    notes = models.TextField(blank=True)
    # For 'edit' actions: {'field': 'activity_value', 'old': '1000', 'new': '1200'}
    changes = models.JSONField(default=dict)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']

    def __str__(self):
        return f"{self.action} on {self.emission_record_id} by {self.performed_by}"
