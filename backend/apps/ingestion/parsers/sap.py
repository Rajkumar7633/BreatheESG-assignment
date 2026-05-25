"""
SAP MM (Materials Management) flat-file parser.

Format decision: SAP SE16N / MB51 transaction export as tab-separated flat file.
This is the most common way enterprise clients share SAP data —
they run a transaction, press "Export to spreadsheet", and send the file.
IDoc would be better for EDI integration but requires SAP Basis setup.
OData requires a Gateway — most clients don't have it configured for ESG data.

Real-world quirks handled:
- Dates in YYYYMMDD format (SAP internal format, no separator)
- SAP unit codes: M3 (cubic metres), TO (metric tons), GAL (US gallons),
  SCF (standard cubic feet), MBT (thousand BTU), L (litres), KG (kilograms)
- German decimal separators in some regional exports (1.234,56 → 1234.56)
- Column headers may be German field names (BUCHUNGSDATUM, WERK, MENGE)
- Movement type 261 = goods issue (fuel consumed), 201 = to cost centre
- Plant code (WERKS) is a 4-char code like 'DE01' — meaningless without lookup
- MATNR (material number) encodes fuel type in client-specific naming convention
"""
import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List

from .base import ParsedRow

# SAP unit of measure codes → (canonical_unit, conversion_factor_to_canonical)
# Canonical units: L (litres), M3 (cubic metres), KG (kilograms), T (tonnes)
SAP_UOM_MAP = {
    'L':   ('L',  Decimal('1')),
    'LTR': ('L',  Decimal('1')),
    'M3':  ('M3', Decimal('1')),
    'KG':  ('KG', Decimal('1')),
    'TO':  ('T',  Decimal('1')),     # SAP metric tonne
    'T':   ('T',  Decimal('1')),
    'GAL': ('L',  Decimal('3.78541')),   # US gallon → litres
    'GLL': ('L',  Decimal('3.78541')),   # SAP alternate for US gallon
    'SCF': ('M3', Decimal('0.0283168')), # standard cubic foot → M3
    'MBT': ('kWh', Decimal('293.071')),  # thousand BTU → kWh
    'KWH': ('kWh', Decimal('1')),
    'MWH': ('kWh', Decimal('1000')),
    'GJ':  ('kWh', Decimal('277.778')),
}

# Plant code → facility name lookup (client would provide this mapping)
PLANT_LOOKUP = {
    'DE01': 'Hamburg Manufacturing Plant',
    'DE02': 'Munich Distribution Center',
    'UK01': 'London Office',
    'UK02': 'Manchester Warehouse',
    'US01': 'New York HQ',
    'US02': 'Chicago Distribution',
    'IN01': 'Mumbai Operations',
    'SG01': 'Singapore APAC Hub',
}

# Material number prefix → (fuel_type, scope, category, sub_category, ef_key)
MATERIAL_FUEL_MAP = {
    'DIESEL':  ('Diesel',       '1', 'Stationary Combustion', 'Diesel',       'fuel_diesel'),
    'PETROL':  ('Petrol',       '1', 'Mobile Combustion',     'Petrol',       'fuel_petrol'),
    'GASOIL':  ('Gas Oil',      '1', 'Stationary Combustion', 'Gas Oil',      'fuel_gas_oil'),
    'NATGAS':  ('Natural Gas',  '1', 'Stationary Combustion', 'Natural Gas',  'fuel_natural_gas'),
    'LPG':     ('LPG',          '1', 'Stationary Combustion', 'LPG',          'fuel_lpg'),
    'HFO':     ('Heavy Fuel Oil','1','Stationary Combustion', 'Heavy Fuel Oil','fuel_hfo'),
    'KEROSENE':('Kerosene',     '1', 'Stationary Combustion', 'Kerosene',     'fuel_kerosene'),
    'COAL':    ('Coal',         '1', 'Stationary Combustion', 'Coal',         'fuel_coal'),
    'BIOD':    ('Biodiesel',    '1', 'Stationary Combustion', 'Biodiesel',    'fuel_biodiesel'),
    # Procurement items go to Scope 3 upstream
    'PROCURE': ('Purchased Goods', '3', 'Purchased Goods and Services', '', 'upstream_goods'),
}

# SAP column name aliases — handles both English and German headers
COLUMN_ALIASES = {
    # English → canonical
    'posting_date': 'BUDAT', 'date': 'BUDAT',
    'plant': 'WERKS', 'werk': 'WERKS',
    'material': 'MATNR', 'material_number': 'MATNR',
    'document': 'MBLNR', 'material_document': 'MBLNR',
    'movement_type': 'BWART', 'mvt_type': 'BWART',
    'quantity': 'MENGE', 'menge': 'MENGE',
    'unit': 'MEINS', 'uom': 'MEINS',
    'amount': 'DMBTR', 'value': 'DMBTR',
    'currency': 'WAERS',
    'cost_center': 'KOSTL',
    # German field names as they appear in some SAP exports
    'buchungsdatum': 'BUDAT',
    'materialnummer': 'MATNR',
    'werk_0': 'WERKS',
    'bewegungsart': 'BWART',
    'buchungsmenge': 'MENGE',
    'mengeneinheit': 'MEINS',
    'betrag_in_hkwährung': 'DMBTR',
    'währung': 'WAERS',
    'kostenstelle': 'KOSTL',
}

# Movement types indicating actual consumption (not returns/adjustments)
CONSUMPTION_MOVEMENT_TYPES = {'261', '201', '551', '601', '641', '101'}


def _normalize_header(h: str) -> str:
    cleaned = h.strip().lower().replace(' ', '_').replace('ä', 'a').replace('ü', 'u').replace('ö', 'o')
    return COLUMN_ALIASES.get(cleaned, h.strip().upper())


def _parse_sap_date(val: str) -> date:
    """SAP stores dates as YYYYMMDD in internal format."""
    val = val.strip()
    if len(val) == 8 and val.isdigit():
        return datetime.strptime(val, '%Y%m%d').date()
    # Some exports add separators: YYYY.MM.DD or YYYY/MM/DD
    for fmt in ('%Y.%m.%d', '%Y/%m/%d', '%d.%m.%Y', '%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse SAP date: {val!r}")


def _parse_decimal(val: str) -> Decimal:
    """Handle both German (1.234,56) and English (1,234.56) decimal formats."""
    val = val.strip()
    if not val or val in ('-', ''):
        return Decimal('0')
    # Detect German format: period as thousands sep, comma as decimal
    if ',' in val and '.' in val:
        if val.index('.') < val.index(','):
            # German: 1.234,56
            val = val.replace('.', '').replace(',', '.')
        else:
            # English: 1,234.56
            val = val.replace(',', '')
    elif ',' in val:
        # Could be German decimal only: 123,45
        val = val.replace(',', '.')
    elif '.' in val:
        # English: 1234.56 or 1,234 already cleaned
        pass
    try:
        return Decimal(val)
    except InvalidOperation:
        raise ValueError(f"Cannot parse number: {val!r}")


def _identify_fuel(matnr: str) -> tuple:
    """Map SAP material number to fuel type and emission factor key."""
    matnr_upper = matnr.upper().strip()
    for prefix, info in MATERIAL_FUEL_MAP.items():
        if matnr_upper.startswith(prefix):
            return info
    return None, None, None, None, None


def parse_sap_csv(file_content: str) -> List[ParsedRow]:
    """
    Parse SAP MM flat-file export (CSV or TSV).

    Accepts both comma-separated and tab-separated files.
    Handles German and English column headers.
    Filters to consumption movement types only.
    Converts all quantities to canonical units.
    """
    # Detect delimiter
    sample = file_content[:2000]
    delimiter = '\t' if sample.count('\t') > sample.count(',') else ','

    reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)

    # Normalize headers
    raw_fieldnames = reader.fieldnames or []
    normalized_map = {f: _normalize_header(f) for f in raw_fieldnames}

    rows = []
    for i, raw_row in enumerate(reader, start=2):  # row 2 because row 1 is header
        # Re-key the row with normalized column names
        row = {normalized_map.get(k, k): v for k, v in raw_row.items()}

        parsed = ParsedRow(
            source_type='sap',
            row_number=i,
            raw_data=dict(raw_row),
        )

        # Movement type filter — only consumption events
        bwart = row.get('BWART', '').strip()
        if bwart and bwart not in CONSUMPTION_MOVEMENT_TYPES:
            parsed.errors.append(f"Skipped: movement type {bwart} is not a consumption event")
            rows.append(parsed)
            continue

        # Parse date
        budat_raw = row.get('BUDAT', '').strip()
        try:
            txn_date = _parse_sap_date(budat_raw)
            parsed.period_start = txn_date
            parsed.period_end = txn_date
        except (ValueError, KeyError) as e:
            parsed.errors.append(f"Invalid posting date '{budat_raw}': {e}")

        # Parse quantity
        menge_raw = row.get('MENGE', '').strip()
        try:
            qty = _parse_decimal(menge_raw)
            if qty <= 0:
                parsed.warnings.append("Quantity is zero or negative — possible return transaction")
        except ValueError as e:
            parsed.errors.append(f"Invalid quantity '{menge_raw}': {e}")
            qty = None

        # Parse unit of measure
        meins = row.get('MEINS', '').strip().upper()
        if meins in SAP_UOM_MAP:
            canonical_unit, factor = SAP_UOM_MAP[meins]
            if qty is not None:
                parsed.activity_value = qty * factor
                parsed.activity_unit = canonical_unit
        else:
            parsed.errors.append(f"Unknown SAP unit of measure: {meins!r}")

        # Plant / facility
        werks = row.get('WERKS', '').strip()
        parsed.facility = PLANT_LOOKUP.get(werks, f"Plant {werks}")
        parsed.cost_center = row.get('KOSTL', '').strip()

        # Material → fuel type
        matnr = row.get('MATNR', '').strip()
        fuel_name, scope, category, sub_cat, ef_key = _identify_fuel(matnr)

        if fuel_name is None:
            parsed.errors.append(
                f"Material number '{matnr}' could not be mapped to a fuel type. "
                "Add it to the material-fuel mapping table."
            )
        else:
            parsed.scope = scope
            parsed.category = category
            parsed.sub_category = sub_cat
            parsed.emission_factor_key = ef_key
            parsed.activity_description = (
                f"{fuel_name} consumption at {parsed.facility}"
            )

        rows.append(parsed)

    return rows
