from django.contrib import admin
from .models import ReviewDecision


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ['action', 'emission_record', 'performed_by', 'performed_at']
    list_filter = ['action']
    readonly_fields = ['emission_record', 'changes', 'performed_at']
