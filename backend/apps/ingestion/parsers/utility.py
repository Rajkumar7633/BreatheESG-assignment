"""
Utility electricity parser — Green Button Alliance CSV format.

Format decision: Green Button CSV (ESPI standard, used by most US/UK utilities).
Green Button is an industry standard originated by US DOE and now adopted broadly.
Most major utilities (National Grid, PG&E, ConEd, Enel) offer Green Button exports
from their customer portals. The alternative (PDF bills) requires OCR which is
fragile; API access requires utility-specific OAuth setup.

Real-world quirks handled:
- Billing periods don't align with calendar months (e.g. 15th to 15th)
- Mix of kWh and MWh readings in the same file
- Demand vs. energy readings (we want kWh consumption, not kW demand)
- Interval data (15-min or hourly) must be aggregated to billing period
- Unit column may contain 'kWh', 'Wh', 'MWh', 'thm', 'CCF' (for gas)
- Some exports include reactive power (kVARh) — we skip those
- Cost is informational only; we derive emissions from consumption, not cost
- ReadingType may be 'Consumption', 'Demand', 'Net' — we want Consumption
"""
import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List

from .base import ParsedRow

# Canonical unit: kWh
UNIT_TO_KWH = {
    'KWH':  Decimal('1'),
    'WH':   Decimal('0.001'),
    'MWH':  Decimal('1000'),
    'GWH':  Decimal('1000000'),
    # Gas units — convert to kWh for Scope 2 if combined meter, otherwise skip
    'THERM': Decimal('29.3071'),
    'THM':   Decimal('29.3071'),
    'CCF':   Decimal('29.3071'),  # hundred cubic feet of natural gas ≈ 1 therm
    'MCF':   Decimal('293.071'),  # thousand cubic feet
    'BTU':   Decimal('0.000293071'),
    'MMBTU': Decimal('293.071'),
}

# Electricity grid regions for emission factor lookup
# In a real deployment this would come from the meter's service territory
GRID_REGION_EF_KEY = {
    'US': 'electricity_us_avg',
    'UK': 'electricity_uk',
    'EU': 'electricity_eu_avg',
    'DEFAULT': 'electricity_us_avg',
}

# Column aliases across different utility portal exports
COLUMN_ALIASES = {
    'start_date': 'period_start',
    'startdatetime': 'period_start',
    'start': 'period_start',
    'interval_start': 'period_start',
    'end_date': 'period_end',
    'enddatetime': 'period_end',
    'end': 'period_end',
    'interval_end': 'period_end',
    'reading_type': 'reading_type',
    'type': 'reading_type',
    'servicecategory': 'service_category',
    'service': 'service_category',
    'value': 'value',
    'usage': 'value',
    'consumption': 'value',
    'quantity': 'value',
    'unit': 'unit',
    'uom': 'unit',
    'units': 'unit',
    'cost': 'cost',
    'charges': 'cost',
    'currency': 'currency',
    'meter_id': 'meter_id',
    'meterid': 'meter_id',
    'account_number': 'meter_id',
    'facility': 'facility',
    'site': 'facility',
    'location': 'facility',
}

ELECTRICITY_READING_TYPES = {'consumption', 'energy', 'usage', 'net metered usage'}
SKIP_READING_TYPES = {'demand', 'reactive', 'kvarh', 'power factor'}


def _normalize_header(h: str) -> str:
    return COLUMN_ALIASES.get(h.strip().lower().replace(' ', '_'), h.strip().lower())


def _parse_datetime(val: str) -> date:
    val = val.strip()
    # ISO 8601 with time
    for fmt in (
        '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d',
        '%m/%d/%Y %H:%M', '%m/%d/%Y',
        '%d/%m/%Y', '%d-%m-%Y',
    ):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {val!r}")


def _parse_decimal(val: str) -> Decimal:
    val = val.strip().replace(',', '')
    if not val:
        return Decimal('0')
    try:
        return Decimal(val)
    except InvalidOperation:
        raise ValueError(f"Cannot parse number: {val!r}")


def parse_utility_csv(file_content: str, region: str = 'US') -> List[ParsedRow]:
    """
    Parse Green Button Alliance CSV electricity export.

    Aggregates interval data by billing period.
    Skips demand readings; only processes energy consumption.
    """
    delimiter = '\t' if file_content[:2000].count('\t') > file_content[:2000].count(',') else ','
    reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)

    raw_fieldnames = reader.fieldnames or []
    norm_map = {f: _normalize_header(f) for f in raw_fieldnames}

    ef_key = GRID_REGION_EF_KEY.get(region.upper(), GRID_REGION_EF_KEY['DEFAULT'])
    rows = []

    for i, raw_row in enumerate(reader, start=2):
        row = {norm_map.get(k, k.lower()): v for k, v in raw_row.items()}

        parsed = ParsedRow(
            source_type='utility',
            row_number=i,
            raw_data=dict(raw_row),
        )

        # Skip non-electricity / demand rows
        reading_type = row.get('reading_type', '').strip().lower()
        service_cat = row.get('service_category', '').strip().lower()

        if reading_type in SKIP_READING_TYPES:
            parsed.errors.append(f"Skipped: reading type '{reading_type}' is not energy consumption")
            rows.append(parsed)
            continue

        if service_cat and service_cat not in ('electricity', 'electric', ''):
            parsed.warnings.append(f"Non-electricity service category: '{service_cat}' — check if in scope")

        # Parse start date
        start_raw = row.get('period_start', '').strip()
        end_raw = row.get('period_end', '').strip()

        try:
            parsed.period_start = _parse_datetime(start_raw) if start_raw else None
        except ValueError as e:
            parsed.errors.append(f"Invalid start date '{start_raw}': {e}")

        try:
            if end_raw:
                parsed.period_end = _parse_datetime(end_raw)
            elif parsed.period_start:
                # Assume monthly if no end date
                parsed.period_end = parsed.period_start + timedelta(days=30)
        except ValueError as e:
            parsed.errors.append(f"Invalid end date '{end_raw}': {e}")

        # Parse value
        value_raw = row.get('value', '').strip()
        try:
            raw_value = _parse_decimal(value_raw)
        except ValueError as e:
            parsed.errors.append(f"Invalid consumption value '{value_raw}': {e}")
            raw_value = None

        # Parse and convert unit
        unit_raw = row.get('unit', 'kWh').strip().upper()
        if unit_raw in UNIT_TO_KWH and raw_value is not None:
            parsed.activity_value = raw_value * UNIT_TO_KWH[unit_raw]
            parsed.activity_unit = 'kWh'
        elif raw_value is not None:
            parsed.warnings.append(f"Unknown unit '{unit_raw}'; assuming kWh")
            parsed.activity_value = raw_value
            parsed.activity_unit = 'kWh'

        # Facility / meter
        parsed.facility = row.get('facility', '').strip()
        parsed.cost_center = row.get('meter_id', '').strip()

        # Classification
        parsed.scope = '2'
        parsed.category = 'Purchased Electricity'
        parsed.sub_category = 'Grid Electricity'
        parsed.emission_factor_key = ef_key
        parsed.activity_description = (
            f"Grid electricity consumption"
            + (f" at {parsed.facility}" if parsed.facility else '')
            + (f", meter {parsed.cost_center}" if parsed.cost_center else '')
        )

        if parsed.activity_value and parsed.activity_value > 1_000_000:
            parsed.warnings.append(
                f"Value {parsed.activity_value} kWh is very large — verify unit conversion"
            )

        rows.append(parsed)

    return rows
