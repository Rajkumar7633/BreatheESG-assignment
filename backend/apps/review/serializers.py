from rest_framework import serializers
from .models import ReviewDecision


class ReviewDecisionSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ReviewDecision
        fields = [
            'id', 'emission_record', 'action', 'action_display',
            'performed_by', 'performed_by_name', 'notes', 'changes', 'performed_at'
        ]
        read_only_fields = ['id', 'performed_by', 'performed_at']


class ReviewActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject', 'flag', 'unflag'])
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class BulkReviewSerializer(serializers.Serializer):
    record_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=500
    )
    action = serializers.ChoiceField(choices=['approve', 'reject', 'flag'])
    notes = serializers.CharField(required=False, allow_blank=True, default='')
