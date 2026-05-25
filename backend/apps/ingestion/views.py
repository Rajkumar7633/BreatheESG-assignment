import hashlib
from datetime import datetime

from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import IngestionJob, RawRecord
from .serializers import IngestionJobSerializer, RawRecordSerializer
from .parsers.sap import parse_sap_csv
from .parsers.utility import parse_utility_csv
from .parsers.travel import parse_travel_csv
from apps.emissions.normalizers import normalize_and_save


PARSERS = {
    'sap': parse_sap_csv,
    'utility': parse_utility_csv,
    'travel': parse_travel_csv,
}


class IngestionJobViewSet(viewsets.ModelViewSet):
    serializer_class = IngestionJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return IngestionJob.objects.filter(
            organization=self.request.user.organization
        ).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """
        POST /api/ingestion/jobs/upload/
        Form fields: source_type, file, region (optional, for utility)
        """
        source_type = request.data.get('source_type', '').lower()
        if source_type not in PARSERS:
            return Response(
                {'error': f"source_type must be one of: {', '.join(PARSERS)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        file_content = uploaded_file.read().decode('utf-8', errors='replace')
        file_hash = hashlib.sha256(file_content.encode()).hexdigest()

        # Duplicate detection: warn but don't block
        duplicate = IngestionJob.objects.filter(
            organization=request.user.organization,
            file_hash=file_hash,
        ).first()

        with transaction.atomic():
            job = IngestionJob.objects.create(
                organization=request.user.organization,
                source_type=source_type,
                status='processing',
                filename=uploaded_file.name,
                file_hash=file_hash,
                created_by=request.user,
                metadata={'duplicate_of': str(duplicate.id) if duplicate else None},
            )

            try:
                parse_fn = PARSERS[source_type]
                # Utility parser accepts a region parameter
                if source_type == 'utility':
                    region = request.data.get('region', 'US')
                    parsed_rows = parse_fn(file_content, region=region)
                else:
                    parsed_rows = parse_fn(file_content)

                stats = normalize_and_save(parsed_rows, job)

                job.total_rows = stats['total']
                job.processed_rows = stats['processed']
                job.failed_rows = stats['failed']
                job.flagged_rows = stats['flagged']
                job.error_log = stats['errors'][:100]  # Cap stored errors
                job.status = (
                    'completed' if stats['failed'] == 0
                    else 'partial' if stats['processed'] > 0
                    else 'failed'
                )
                job.completed_at = datetime.utcnow()
                job.save()

            except Exception as e:
                job.status = 'failed'
                job.error_log = [{'error': str(e)}]
                job.save()
                return Response(
                    {'error': f'Processing failed: {str(e)}', 'job_id': str(job.id)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        serializer = IngestionJobSerializer(job)
        response_data = serializer.data
        if duplicate:
            response_data['warning'] = f'This file was previously uploaded (job {duplicate.id})'

        return Response(response_data, status=status.HTTP_201_CREATED)
