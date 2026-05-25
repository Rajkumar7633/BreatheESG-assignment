"""
Converts ParsedRow objects into EmissionRecord database rows.
Also runs suspicion checks (statistical anomaly detection).
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
import hashlib
import json

from apps.ingestion.models import IngestionJob, RawRecord
from apps.ingestion.parsers.base import ParsedRow
from apps.emissions.models import EmissionRecord, EmissionFactor
from apps.emissions.emission_factors import EMISSION_FACTORS, calculate_co2e


# ── Suspicion check thresholds ────────────────────────────────────────────────
# These are simple heuristics; a real system would use per-client baselines.
SUSPICION_RULES = {
    # co2e_kg absolute limits per source type
    'sap': {'max_single_co2e': 500_000},    # 500 tCO2e in one transaction is unusual
    'utility': {'max_single_co2e': 1_000_000},
    'travel': {'max_single_co2e': 50_000},
    # Activity value limits
    'fuel_diesel': {'max_L': 500_000},       # 500kL diesel in one SAP posting
    'electricity': {'max_kWh': 10_000_000},  # 10 GWh in one billing period
    'flight': {'max_km': 25_000},            # > circumference of Earth is suspicious
}


def _build_suspicion_reasons(
    parsed: ParsedRow,
    co2e_kg: Optional[Decimal],
) -> List[str]:
    reasons = []
    reasons.extend(parsed.warnings)

    if co2e_kg is not None:
        threshold = SUSPICION_RULES.get(parsed.source_type, {}).get('max_single_co2e')
        if threshold and co2e_kg > threshold:
            reasons.append(
                f"CO2e value {float(co2e_kg):.0f} kg exceeds single-record threshold "
                f"of {threshold:,} kg for {parsed.source_type} data"
            )

    if parsed.activity_value is not None and parsed.activity_value < 0:
        reasons.append("Negative activity value — possible data entry error or return transaction")

    if parsed.source_type == 'travel' and parsed.activity_unit == 'km':
        if parsed.activity_value and parsed.activity_value > 25000:
            reasons.append(
                f"Flight distance {float(parsed.activity_value):.0f} km exceeds "
                "maximum possible great-circle distance (20,037 km)"
            )

    return reasons


def _get_or_create_emission_factor(ef_key: str) -> Optional[EmissionFactor]:
    """Get EmissionFactor from DB, creating from constants if not present."""
    if not ef_key or ef_key not in EMISSION_FACTORS:
        return None

    ef_data = EMISSION_FACTORS[ef_key]
    ef, _ = EmissionFactor.objects.get_or_create(
        source_type=ef_key,
        source_year=ef_data['source_year'],
        defaults={
            'name': ef_data['name'],
            'scope': ef_data['scope'],
            'factor_value': ef_data['factor'],
            'factor_unit': f"kg_co2e_per_{ef_data['activity_unit']}",
            'activity_unit': ef_data['activity_unit'],
            'source_name': ef_data.get('source', 'Unknown'),
            'valid_from': date(ef_data['source_year'], 1, 1),
            'region': ef_data.get('region', ''),
            'co2_factor': ef_data.get('co2', Decimal('0')),
            'ch4_factor': ef_data.get('ch4', Decimal('0')),
            'n2o_factor': ef_data.get('n2o', Decimal('0')),
            'notes': ef_data.get('notes', ''),
        }
    )
    return ef


def normalize_and_save(
    parsed_rows: List[ParsedRow],
    ingestion_job: IngestionJob,
) -> dict:
    """
    Convert ParsedRow list to EmissionRecord + RawRecord pairs.
    Returns summary stats dict.
    """
    stats = {
        'total': len(parsed_rows),
        'processed': 0,
        'failed': 0,
        'flagged': 0,
        'errors': [],
    }

    for parsed in parsed_rows:
        # Always save raw record regardless of parse errors
        raw_record = RawRecord.objects.create(
            ingestion_job=ingestion_job,
            row_number=parsed.row_number,
            raw_data=parsed.raw_data,
            parse_errors=parsed.errors,
        )

        if not parsed.is_valid:
            stats['failed'] += 1
            stats['errors'].append({
                'row': parsed.row_number,
                'errors': parsed.errors,
            })
            continue

        # Compute emissions
        emissions = calculate_co2e(parsed.activity_value, parsed.emission_factor_key)
        co2e_kg = emissions.get('co2e_kg')

        # Run suspicion checks
        suspicion_reasons = _build_suspicion_reasons(parsed, co2e_kg)
        is_suspicious = len(suspicion_reasons) > 0

        # Get or create emission factor record
        ef = _get_or_create_emission_factor(parsed.emission_factor_key)

        period_end = parsed.period_end or parsed.period_start

        EmissionRecord.objects.create(
            organization=ingestion_job.organization,
            source_type=parsed.source_type,
            raw_record=raw_record,
            emission_factor=ef,
            scope=parsed.scope,
            category=parsed.category,
            sub_category=parsed.sub_category,
            activity_description=parsed.activity_description,
            activity_value=parsed.activity_value,
            activity_unit=parsed.activity_unit,
            co2e_kg=co2e_kg,
            co2_kg=emissions.get('co2_kg'),
            ch4_kg=emissions.get('ch4_kg'),
            n2o_kg=emissions.get('n2o_kg'),
            period_start=parsed.period_start,
            period_end=period_end,
            facility=parsed.facility,
            cost_center=parsed.cost_center,
            department=parsed.department,
            country=parsed.country,
            is_suspicious=is_suspicious,
            suspicious_reasons=suspicion_reasons,
            status='flagged' if is_suspicious else 'pending',
        )

        if is_suspicious:
            stats['flagged'] += 1
        stats['processed'] += 1

    return stats
