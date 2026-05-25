from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class ParsedRow:
    """
    Intermediate representation after parsing but before emission calculation.
    All parsers produce this; the normalizer then converts it to EmissionRecord.
    """
    source_type: str
    row_number: int
    raw_data: dict

    # Normalized activity
    scope: str              # '1', '2', '3'
    category: str           # GHG Protocol category name
    sub_category: str = ''
    activity_description: str = ''
    activity_value: Optional[Decimal] = None
    activity_unit: str = ''  # canonical unit after conversion

    # Temporal
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    # Organizational
    facility: str = ''
    cost_center: str = ''
    department: str = ''
    country: str = ''

    # Emission factor lookup key
    emission_factor_key: str = ''

    # Per-row errors
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def is_valid(self):
        return len(self.errors) == 0 and self.activity_value is not None
