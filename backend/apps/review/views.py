from datetime import datetime

from django.db import transaction
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.emissions.models import EmissionRecord
from apps.emissions.serializers import EmissionRecordSerializer
from .models import ReviewDecision
from .serializers import ReviewDecisionSerializer, ReviewActionSerializer, BulkReviewSerializer

STATUS_MAP = {
    'approve': 'approved',
    'reject': 'rejected',
    'flag': 'flagged',
    'unflag': 'pending',
}


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def review_queue(request):
    """Records awaiting review: pending + flagged, ordered by suspicion then date."""
    qs = EmissionRecord.objects.filter(
        organization=request.user.organization,
        status__in=['pending', 'flagged'],
    ).select_related(
        'emission_factor', 'reviewed_by', 'raw_record__ingestion_job'
    ).order_by('-is_suspicious', '-created_at')[:200]

    serializer = EmissionRecordSerializer(qs, many=True)
    return Response({
        'count': EmissionRecord.objects.filter(
            organization=request.user.organization,
            status__in=['pending', 'flagged'],
        ).count(),
        'results': serializer.data,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def single_action(request, record_id):
    """Apply a review action to a single record."""
    try:
        record = EmissionRecord.objects.get(
            id=record_id,
            organization=request.user.organization,
        )
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)

    if record.is_locked:
        return Response(
            {'error': 'Record is locked for audit and cannot be modified'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ReviewActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    action_name = serializer.validated_data['action']
    notes = serializer.validated_data.get('notes', '')
    new_status = STATUS_MAP[action_name]

    with transaction.atomic():
        old_status = record.status
        record.status = new_status
        record.reviewed_by = request.user
        record.reviewed_at = datetime.utcnow()
        record.review_notes = notes
        if action_name == 'unflag':
            record.is_suspicious = False
        record.save()

        ReviewDecision.objects.create(
            emission_record=record,
            action=action_name,
            performed_by=request.user,
            notes=notes,
            changes={'status': {'from': old_status, 'to': new_status}},
        )

    return Response(EmissionRecordSerializer(record).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_action(request):
    """Apply an action to multiple records at once."""
    serializer = BulkReviewSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    record_ids = serializer.validated_data['record_ids']
    action_name = serializer.validated_data['action']
    notes = serializer.validated_data.get('notes', '')
    new_status = STATUS_MAP[action_name]

    records = EmissionRecord.objects.filter(
        id__in=record_ids,
        organization=request.user.organization,
        is_locked=False,
    )

    updated_count = 0
    with transaction.atomic():
        for record in records:
            old_status = record.status
            record.status = new_status
            record.reviewed_by = request.user
            record.reviewed_at = datetime.utcnow()
            record.review_notes = notes
            record.save()

            ReviewDecision.objects.create(
                emission_record=record,
                action='bulk_approve' if action_name == 'approve' else action_name,
                performed_by=request.user,
                notes=notes,
                changes={'status': {'from': old_status, 'to': new_status}},
            )
            updated_count += 1

    return Response({
        'updated': updated_count,
        'skipped': len(record_ids) - updated_count,
        'message': f'{updated_count} records {action_name}d',
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def audit_log(request):
    """Full audit trail of all review decisions for this org."""
    decisions = ReviewDecision.objects.filter(
        emission_record__organization=request.user.organization
    ).select_related('performed_by', 'emission_record').order_by('-performed_at')

    record_id = request.query_params.get('record_id')
    if record_id:
        decisions = decisions.filter(emission_record_id=record_id)

    serializer = ReviewDecisionSerializer(decisions[:500], many=True)
    return Response({
        'count': decisions.count(),
        'results': serializer.data,
    })
