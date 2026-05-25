from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import EmissionRecord, EmissionFactor
from .serializers import EmissionRecordSerializer, EmissionFactorSerializer, EmissionSummarySerializer


class EmissionRecordFilter:
    pass


class EmissionRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EmissionRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scope', 'source_type', 'status', 'is_suspicious', 'facility', 'category']
    search_fields = ['activity_description', 'facility', 'cost_center', 'category']
    ordering_fields = ['period_start', 'co2e_kg', 'activity_value', 'created_at', 'status']
    ordering = ['-period_start']

    def get_queryset(self):
        qs = EmissionRecord.objects.filter(
            organization=self.request.user.organization
        ).select_related('emission_factor', 'reviewed_by', 'raw_record__ingestion_job')

        # Additional query param filters
        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(period_start__year=year)

        month = self.request.query_params.get('month')
        if month:
            qs = qs.filter(period_start__month=month)

        return qs

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Dashboard summary statistics."""
        qs = self.get_queryset()

        # Only count approved+pending for emissions totals (not rejected)
        active_qs = qs.exclude(status='rejected')

        def safe_sum(queryset, field):
            result = queryset.aggregate(total=Sum(field))['total']
            return result or Decimal('0')

        scope1 = safe_sum(active_qs.filter(scope='1'), 'co2e_kg')
        scope2 = safe_sum(active_qs.filter(scope='2'), 'co2e_kg')
        scope3 = safe_sum(active_qs.filter(scope='3'), 'co2e_kg')

        status_counts = qs.values('status').annotate(count=Count('id'))
        status_map = {s['status']: s['count'] for s in status_counts}

        by_source = {}
        for row in active_qs.values('source_type').annotate(
            co2e=Sum('co2e_kg'), count=Count('id')
        ):
            by_source[row['source_type']] = {
                'co2e_kg': float(row['co2e'] or 0),
                'count': row['count'],
            }

        by_scope = []
        for s in ['1', '2', '3']:
            scope_qs = active_qs.filter(scope=s)
            by_scope.append({
                'scope': s,
                'label': f'Scope {s}',
                'co2e_kg': float(safe_sum(scope_qs, 'co2e_kg')),
                'count': scope_qs.count(),
            })

        monthly_trend = []
        for row in (
            active_qs
            .annotate(month=TruncMonth('period_start'))
            .values('month', 'scope')
            .annotate(co2e=Sum('co2e_kg'))
            .order_by('month', 'scope')
        ):
            monthly_trend.append({
                'month': row['month'].strftime('%Y-%m') if row['month'] else None,
                'scope': row['scope'],
                'co2e_kg': float(row['co2e'] or 0),
            })

        return Response({
            'total_records': qs.count(),
            'pending_count': status_map.get('pending', 0),
            'approved_count': status_map.get('approved', 0),
            'rejected_count': status_map.get('rejected', 0),
            'flagged_count': status_map.get('flagged', 0),
            'scope1_co2e_kg': float(scope1),
            'scope2_co2e_kg': float(scope2),
            'scope3_co2e_kg': float(scope3),
            'total_co2e_kg': float(scope1 + scope2 + scope3),
            'by_source': by_source,
            'by_scope': by_scope,
            'monthly_trend': monthly_trend,
        })


class EmissionFactorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmissionFactorSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = EmissionFactor.objects.all().order_by('scope', 'source_type')
