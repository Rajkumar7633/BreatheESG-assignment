"""
Corporate travel parser — Concur Expense Report CSV format.

Format decision: Concur standard expense report export CSV.
Concur is the dominant corporate T&E platform (used by ~50% of Fortune 500).
Their "Report Export" (Analytics > Standard Reports > Expense > Expense Detail)
produces a consistent CSV. Navan/TripActions has a similar export schema.

Real-world quirks handled:
- Expense type classification (Airfare, Hotel, Car Rental, Train, Taxi)
- Airfare rows don't always include distance — must infer from city/airport codes
- Cabin class is often in a sub-field; affects emission factor multiplier
- Hotel nights vs. hotel cost — extract night count from check-in/check-out dates
- Currency varies per transaction — cost is informational, not used for emissions
- Vendor names are free text and inconsistent
- Missing airport codes for some domestic routes
- 'Personal car' mileage claims are in miles or km depending on country setting

Emission factor approach:
- Flights: DEFRA 2024 radiative forcing multiplier of 1.891x applied to CO2
- Distance calculation: Haversine formula on lat/lng of airport IATA codes
  (subset embedded in constants — production would use an aviation API)
- Hotels: DEFRA/Cornell Hotel Sustainability Benchmarking average 20.6 kg CO2e/night
- Car rental: DEFRA 2024 average car emission factor
"""
import csv
import io
import math
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from .base import ParsedRow

# GHG Protocol categories for Scope 3
TRAVEL_CATEGORIES = {
    'flight':   ('3', 'Business Travel', 'Air Travel'),
    'hotel':    ('3', 'Business Travel', 'Hotel Stay'),
    'car':      ('3', 'Business Travel', 'Rental Car'),
    'train':    ('3', 'Business Travel', 'Rail Travel'),
    'taxi':     ('3', 'Business Travel', 'Ground Transport'),
    'mileage':  ('3', 'Business Travel', 'Personal Vehicle'),
}

# Expense type keyword mapping
EXPENSE_TYPE_MAP = {
    'airfare': 'flight', 'air': 'flight', 'flight': 'flight',
    'hotel': 'hotel', 'lodging': 'hotel', 'accommodation': 'hotel',
    'car rental': 'car', 'rental car': 'car', 'vehicle rental': 'car', 'hire car': 'car',
    'train': 'train', 'rail': 'train', 'eurostar': 'train', 'amtrak': 'train',
    'taxi': 'taxi', 'uber': 'taxi', 'lyft': 'taxi', 'rideshare': 'taxi', 'cab': 'taxi',
    'mileage': 'mileage', 'personal vehicle': 'mileage', 'personal car': 'mileage',
}

# Cabin class → emission factor key
CABIN_EF_MAP = {
    'economy':          'flight_economy',
    'economy plus':     'flight_economy_plus',
    'premium economy':  'flight_premium_economy',
    'business':         'flight_business',
    'business class':   'flight_business',
    'first':            'flight_first',
    'first class':      'flight_first',
}

# Airport IATA → (lat, lng, country) for common business hubs
# Production would use a full IATA database (~8000 airports)
AIRPORT_COORDS = {
    'JFK': (40.6413, -73.7781, 'US'), 'LGA': (40.7773, -73.8726, 'US'),
    'EWR': (40.6895, -74.1745, 'US'), 'ORD': (41.9742, -87.9073, 'US'),
    'LAX': (33.9425, -118.4081, 'US'), 'SFO': (37.6213, -122.379, 'US'),
    'BOS': (42.3656, -71.0096, 'US'), 'ATL': (33.6407, -84.4277, 'US'),
    'DFW': (32.8998, -97.0403, 'US'), 'MIA': (25.7959, -80.2870, 'US'),
    'SEA': (47.4502, -122.3088, 'US'), 'DEN': (39.8561, -104.6737, 'US'),
    'IAD': (38.9531, -77.4565, 'US'), 'IAH': (29.9902, -95.3368, 'US'),
    'LHR': (51.4700, -0.4543, 'GB'), 'LGW': (51.1537, -0.1821, 'GB'),
    'LCY': (51.5048, 0.0495, 'GB'),  'MAN': (53.3537, -2.2750, 'GB'),
    'CDG': (49.0097, 2.5479, 'FR'),  'ORY': (48.7233, 2.3794, 'FR'),
    'AMS': (52.3086, 4.7639, 'NL'),  'FRA': (50.0379, 8.5622, 'DE'),
    'MUC': (48.3537, 11.7750, 'DE'), 'ZRH': (47.4647, 8.5492, 'CH'),
    'SIN': (1.3644, 103.9915, 'SG'), 'HKG': (22.3080, 113.9185, 'HK'),
    'NRT': (35.7720, 140.3929, 'JP'), 'HND': (35.5533, 139.7811, 'JP'),
    'SYD': (-33.9399, 151.1753, 'AU'),'MEL': (-37.6690, 144.8410, 'AU'),
    'DXB': (25.2532, 55.3657, 'AE'), 'BOM': (19.0896, 72.8656, 'IN'),
    'DEL': (28.5562, 77.1000, 'IN'),  'PEK': (40.0799, 116.6031, 'CN'),
    'PVG': (31.1443, 121.8083, 'CN'), 'YYZ': (43.6772, -79.6306, 'CA'),
    'YVR': (49.1967, -123.1815, 'CA'),
}

COLUMN_ALIASES = {
    'report_name': 'report_name', 'report name': 'report_name',
    'report_id': 'report_id', 'report id': 'report_id',
    'employee_name': 'employee_name', 'employee name': 'employee_name',
    'employee_id': 'employee_id', 'employee id': 'employee_id',
    'cost_center': 'cost_center', 'cost center': 'cost_center',
    'expense_type': 'expense_type', 'expense type': 'expense_type',
    'transaction_date': 'transaction_date', 'transaction date': 'transaction_date',
    'amount': 'amount',
    'currency': 'currency',
    'vendor_name': 'vendor_name', 'vendor name': 'vendor_name', 'vendor': 'vendor_name',
    'city_from': 'city_from', 'from': 'city_from', 'origin': 'city_from',
    'city_to': 'city_to', 'to': 'city_to', 'destination': 'city_to',
    'miles/km': 'distance', 'distance': 'distance', 'miles': 'distance', 'km': 'distance',
    'class': 'travel_class', 'cabin_class': 'travel_class',
    'nights': 'nights',
    'check_in': 'check_in', 'check in': 'check_in',
    'check_out': 'check_out', 'check out': 'check_out',
    'department': 'department',
}


def _norm_header(h: str) -> str:
    return COLUMN_ALIASES.get(h.strip().lower(), h.strip().lower())


def _parse_date(val: str) -> Optional[date]:
    if not val or not val.strip():
        return None
    val = val.strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(val: str) -> Optional[Decimal]:
    val = str(val).strip().replace(',', '')
    if not val:
        return None
    try:
        return Decimal(val)
    except InvalidOperation:
        return None


def _classify_expense(expense_type: str) -> Optional[str]:
    lower = expense_type.lower().strip()
    for keyword, category in EXPENSE_TYPE_MAP.items():
        if keyword in lower:
            return category
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> Decimal:
    """Great-circle distance between two lat/lng points in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return Decimal(str(round(R * c, 2)))


def _airport_distance_km(orig: str, dest: str) -> Tuple[Optional[Decimal], list]:
    """
    Calculate great-circle distance from IATA codes.
    Returns (distance_km, warnings).
    """
    warnings = []
    orig = orig.strip().upper()
    dest = dest.strip().upper()

    if orig not in AIRPORT_COORDS:
        warnings.append(f"Unknown origin airport code: {orig!r} — distance not calculated")
        return None, warnings
    if dest not in AIRPORT_COORDS:
        warnings.append(f"Unknown destination airport code: {dest!r} — distance not calculated")
        return None, warnings

    lat1, lon1, _ = AIRPORT_COORDS[orig]
    lat2, lon2, _ = AIRPORT_COORDS[dest]
    dist = _haversine_km(lat1, lon1, lat2, lon2)
    return dist, warnings


def _get_flight_ef_key(distance_km: Optional[Decimal], cabin: str) -> str:
    """
    Select emission factor based on flight length and cabin class.
    Short-haul < 1500km, medium-haul 1500-3000km, long-haul > 3000km.
    """
    cabin_lower = cabin.lower().strip() if cabin else 'economy'

    if distance_km and distance_km < 1500:
        prefix = 'flight_short_haul'
    elif distance_km and distance_km < 3500:
        prefix = 'flight_medium_haul'
    else:
        prefix = 'flight_long_haul'

    # Cabin suffix
    if 'business' in cabin_lower:
        suffix = '_business'
    elif 'first' in cabin_lower:
        suffix = '_first'
    elif 'premium' in cabin_lower:
        suffix = '_premium_economy'
    else:
        suffix = '_economy'

    return prefix + suffix


def parse_travel_csv(file_content: str) -> List[ParsedRow]:
    """
    Parse Concur expense report CSV export.

    Handles multi-type rows (airfare, hotel, car rental, ground transport).
    Derives flight distances from airport IATA codes where not provided.
    """
    delimiter = '\t' if file_content[:2000].count('\t') > file_content[:2000].count(',') else ','
    reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)

    raw_fieldnames = reader.fieldnames or []
    norm_map = {f: _norm_header(f) for f in raw_fieldnames}

    rows = []
    for i, raw_row in enumerate(reader, start=2):
        row = {norm_map.get(k, k.lower()): v for k, v in raw_row.items()}

        parsed = ParsedRow(
            source_type='travel',
            row_number=i,
            raw_data=dict(raw_row),
        )

        # Classify expense type
        expense_type_raw = row.get('expense_type', '').strip()
        category_key = _classify_expense(expense_type_raw)
        if not category_key:
            parsed.errors.append(
                f"Cannot classify expense type: '{expense_type_raw}'. "
                "Add mapping in EXPENSE_TYPE_MAP."
            )
            rows.append(parsed)
            continue

        scope, category, sub_category = TRAVEL_CATEGORIES[category_key]
        parsed.scope = scope
        parsed.category = category
        parsed.sub_category = sub_category
        parsed.cost_center = row.get('cost_center', '').strip()
        parsed.department = row.get('department', '').strip()

        # Date
        txn_date = _parse_date(row.get('transaction_date', ''))
        if txn_date:
            parsed.period_start = txn_date

        employee = row.get('employee_name', '').strip()
        vendor = row.get('vendor_name', '').strip()

        if category_key == 'flight':
            city_from = row.get('city_from', '').strip()
            city_to = row.get('city_to', '').strip()

            # Try provided distance first
            dist_raw = _parse_decimal(row.get('distance', ''))
            dist_km: Optional[Decimal] = None

            if dist_raw and dist_raw > 0:
                # Assume miles if < 300 and looks like domestic US, else km
                if dist_raw < 500 and 'US' in str(AIRPORT_COORDS.get(city_from.upper(), ('','','US'))):
                    dist_km = dist_raw * Decimal('1.60934')
                    parsed.warnings.append(f"Converted {dist_raw} miles to {dist_km:.0f} km")
                else:
                    dist_km = dist_raw
            elif city_from and city_to:
                dist_km, dist_warnings = _airport_distance_km(city_from, city_to)
                parsed.warnings.extend(dist_warnings)
                if dist_km:
                    parsed.warnings.append(
                        f"Distance derived from IATA codes {city_from}→{city_to}: {dist_km:.0f} km"
                    )

            if dist_km is None:
                parsed.errors.append(
                    "Cannot determine flight distance. Provide airport codes or distance."
                )
            else:
                parsed.activity_value = dist_km
                parsed.activity_unit = 'km'

            cabin = row.get('travel_class', 'Economy').strip()
            parsed.emission_factor_key = _get_flight_ef_key(dist_km, cabin)
            parsed.activity_description = (
                f"Flight: {city_from} → {city_to}"
                + (f" ({cabin})" if cabin else '')
                + (f" — {employee}" if employee else '')
            )
            parsed.period_end = txn_date

        elif category_key == 'hotel':
            check_in = _parse_date(row.get('check_in', ''))
            check_out = _parse_date(row.get('check_out', ''))
            nights_raw = _parse_decimal(row.get('nights', ''))

            nights = None
            if nights_raw and nights_raw > 0:
                nights = nights_raw
            elif check_in and check_out:
                nights = Decimal(str((check_out - check_in).days))
                if nights <= 0:
                    parsed.warnings.append("Check-out is not after check-in; defaulting to 1 night")
                    nights = Decimal('1')

            if nights is None:
                parsed.errors.append("Cannot determine hotel nights. Provide nights or check-in/check-out dates.")
            else:
                parsed.activity_value = nights
                parsed.activity_unit = 'night'

            city = row.get('city_to', row.get('city_from', '')).strip()
            parsed.emission_factor_key = 'hotel_stay'
            parsed.activity_description = (
                f"Hotel stay: {nights} night(s)"
                + (f" in {city}" if city else '')
                + (f" — {employee}" if employee else '')
            )
            parsed.period_start = check_in or txn_date
            parsed.period_end = check_out or txn_date

        elif category_key in ('car', 'mileage'):
            dist_raw = _parse_decimal(row.get('distance', ''))
            if dist_raw and dist_raw > 0:
                # Concur reports in miles for US/UK, km for continental Europe
                # If no explicit unit, check cost center country or default to km
                dist_km = dist_raw * Decimal('1.60934') if dist_raw < 500 else dist_raw
                parsed.activity_value = dist_km
                parsed.activity_unit = 'km'
            else:
                # Fall back to amount if no distance (will need manual review)
                parsed.warnings.append(
                    "No distance for car/mileage expense — record flagged for manual review"
                )
                amount = _parse_decimal(row.get('amount', ''))
                if amount:
                    # Rough estimate: average business car ~$0.67/mile, ~$0.42/km
                    dist_km = amount / Decimal('0.42')
                    parsed.activity_value = dist_km
                    parsed.activity_unit = 'km'
                    parsed.warnings.append(f"Distance estimated from cost: ${amount} → ~{dist_km:.0f} km")

            parsed.emission_factor_key = 'car_rental_avg' if category_key == 'car' else 'personal_car_avg'
            city_from = row.get('city_from', '').strip()
            city_to = row.get('city_to', '').strip()
            parsed.activity_description = (
                f"{'Car rental' if category_key == 'car' else 'Personal vehicle'}: "
                + (f"{city_from} → {city_to}" if city_from else vendor)
                + (f" — {employee}" if employee else '')
            )
            parsed.period_end = txn_date

        elif category_key in ('train', 'taxi'):
            dist_raw = _parse_decimal(row.get('distance', ''))
            if dist_raw and dist_raw > 0:
                parsed.activity_value = dist_raw
                parsed.activity_unit = 'km'
            else:
                amount = _parse_decimal(row.get('amount', ''))
                if amount:
                    parsed.warnings.append("No distance for ground transport; emissions approximated from cost")
                    # £/€/$0.30 per km rough taxi average
                    parsed.activity_value = amount / Decimal('0.30')
                    parsed.activity_unit = 'km'

            parsed.emission_factor_key = 'rail_avg' if category_key == 'train' else 'taxi_avg'
            parsed.activity_description = (
                f"{'Rail' if category_key == 'train' else 'Ground transport'}: "
                + row.get('city_from', '') + (' → ' + row.get('city_to', '') if row.get('city_to') else '')
                + (f" — {employee}" if employee else '')
            )
            parsed.period_end = txn_date

        rows.append(parsed)

    return rows
