"""
Emission factor reference data.
Sources: DEFRA 2024 (UK), US EPA 2024, ICAO Carbon Calculator methodology.

All factors expressed as kg CO2e per activity unit.
GWP values: CO2=1, CH4=28 (AR5), N2O=265 (AR5).
"""
from decimal import Decimal


EMISSION_FACTORS = {
    # ── Scope 1: Stationary Combustion (DEFRA 2024) ──────────────────────────
    'fuel_diesel': {
        'name': 'Diesel (class A gas oil)',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('2.68732'),   # kg CO2e / litre
        'co2': Decimal('2.65000'),
        'ch4': Decimal('0.00141'),
        'n2o': Decimal('0.02591'),
        'source': 'DEFRA 2024 UK GHG Conversion Factors',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_petrol': {
        'name': 'Petrol (gasoline)',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('2.30790'),
        'co2': Decimal('2.27100'),
        'ch4': Decimal('0.00353'),
        'n2o': Decimal('0.03337'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_gas_oil': {
        'name': 'Gas oil (red diesel)',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('2.75664'),
        'co2': Decimal('2.71700'),
        'ch4': Decimal('0.00141'),
        'n2o': Decimal('0.03823'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_natural_gas': {
        'name': 'Natural gas (combustion)',
        'scope': '1',
        'activity_unit': 'M3',
        'factor': Decimal('2.04190'),   # kg CO2e / cubic metre
        'co2': Decimal('2.02000'),
        'ch4': Decimal('0.01974'),
        'n2o': Decimal('0.00216'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
        'notes': 'Gross calorific value basis. For US SCF, convert first.',
    },
    'fuel_lpg': {
        'name': 'LPG',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('1.51280'),
        'co2': Decimal('1.49300'),
        'ch4': Decimal('0.00058'),
        'n2o': Decimal('0.01922'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_hfo': {
        'name': 'Heavy fuel oil',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('3.17910'),
        'co2': Decimal('3.13100'),
        'ch4': Decimal('0.00165'),
        'n2o': Decimal('0.04645'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_kerosene': {
        'name': 'Kerosene',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('2.53540'),
        'co2': Decimal('2.49900'),
        'ch4': Decimal('0.00073'),
        'n2o': Decimal('0.03567'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_coal': {
        'name': 'Coal (industrial)',
        'scope': '1',
        'activity_unit': 'KG',
        'factor': Decimal('2.42000'),   # kg CO2e / kg coal
        'co2': Decimal('2.39400'),
        'ch4': Decimal('0.01560'),
        'n2o': Decimal('0.01040'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },
    'fuel_biodiesel': {
        'name': 'Biodiesel (B100)',
        'scope': '1',
        'activity_unit': 'L',
        'factor': Decimal('0.17280'),   # Lower due to biogenic carbon
        'co2': Decimal('0.00000'),      # biogenic CO2 excluded per GHG Protocol
        'ch4': Decimal('0.00141'),
        'n2o': Decimal('0.17139'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
    },

    # ── Scope 2: Purchased Electricity ───────────────────────────────────────
    'electricity_uk': {
        'name': 'Grid electricity — UK',
        'scope': '2',
        'activity_unit': 'kWh',
        'factor': Decimal('0.20705'),   # kg CO2e / kWh (location-based)
        'co2': Decimal('0.20380'),
        'ch4': Decimal('0.00076'),
        'n2o': Decimal('0.00249'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'region': 'UK',
        'notes': 'Location-based. Market-based would use supplier contract data.',
    },
    'electricity_us_avg': {
        'name': 'Grid electricity — US average',
        'scope': '2',
        'activity_unit': 'kWh',
        'factor': Decimal('0.38610'),   # kg CO2e / kWh (EPA eGRID 2023 national)
        'co2': Decimal('0.38260'),
        'ch4': Decimal('0.00213'),
        'n2o': Decimal('0.00137'),
        'source': 'US EPA eGRID 2023',
        'source_year': 2024,
        'region': 'US',
    },
    'electricity_eu_avg': {
        'name': 'Grid electricity — EU average',
        'scope': '2',
        'activity_unit': 'kWh',
        'factor': Decimal('0.27500'),
        'co2': Decimal('0.27200'),
        'ch4': Decimal('0.00100'),
        'n2o': Decimal('0.00200'),
        'source': 'EEA 2023',
        'source_year': 2024,
        'region': 'EU',
    },

    # ── Scope 3: Business Travel — Flights ───────────────────────────────────
    # DEFRA 2024 with radiative forcing (RF) multiplier of 1.891
    # RF accounts for contrail and cirrus effects at altitude
    'flight_short_haul_economy': {
        'name': 'Short-haul flight economy (< 1500km)',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.25502'),   # kg CO2e / km / passenger
        'co2': Decimal('0.13489'),
        'ch4': Decimal('0.00003'),
        'n2o': Decimal('0.00003'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'notes': 'Includes radiative forcing multiplier 1.891. Per passenger-km.',
    },
    'flight_short_haul_business': {
        'name': 'Short-haul flight business class',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.51004'),   # economy × 2.0 (short-haul cabin premium)
        'co2': Decimal('0.26978'),
        'ch4': Decimal('0.00006'),
        'n2o': Decimal('0.00006'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'flight_medium_haul_economy': {
        'name': 'Medium-haul flight economy (1500–3500km)',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.21636'),
        'co2': Decimal('0.11440'),
        'ch4': Decimal('0.00003'),
        'n2o': Decimal('0.00003'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'flight_medium_haul_business': {
        'name': 'Medium-haul flight business class',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.60581'),   # economy × 2.8
        'co2': Decimal('0.32032'),
        'ch4': Decimal('0.00008'),
        'n2o': Decimal('0.00008'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'flight_long_haul_economy': {
        'name': 'Long-haul flight economy (> 3500km)',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.19512'),
        'co2': Decimal('0.10318'),
        'ch4': Decimal('0.00003'),
        'n2o': Decimal('0.00003'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'flight_long_haul_business': {
        'name': 'Long-haul flight business class',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.56585'),   # economy × 2.9
        'co2': Decimal('0.29922'),
        'ch4': Decimal('0.00009'),
        'n2o': Decimal('0.00009'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'flight_long_haul_first': {
        'name': 'Long-haul flight first class',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('1.08567'),   # economy × 5.56
        'co2': Decimal('0.57383'),
        'ch4': Decimal('0.00016'),
        'n2o': Decimal('0.00016'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'flight_premium_economy': {
        'name': 'Long-haul flight premium economy',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.28607'),   # economy × 1.465
        'co2': Decimal('0.15126'),
        'ch4': Decimal('0.00004'),
        'n2o': Decimal('0.00004'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },

    # ── Scope 3: Business Travel — Hotels ────────────────────────────────────
    'hotel_stay': {
        'name': 'Hotel stay',
        'scope': '3',
        'activity_unit': 'night',
        'factor': Decimal('20.60000'),  # kg CO2e / room-night
        'co2': Decimal('20.00000'),
        'ch4': Decimal('0.30000'),
        'n2o': Decimal('0.30000'),
        'source': 'DEFRA 2024 / Cornell Hotel Sustainability Benchmarking',
        'source_year': 2024,
        'notes': 'Average across hotel categories. A 5-star hotel averages ~31 kg CO2e/night.',
    },

    # ── Scope 3: Business Travel — Ground Transport ──────────────────────────
    'car_rental_avg': {
        'name': 'Car rental (average)',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.19208'),   # kg CO2e / km
        'co2': Decimal('0.18890'),
        'ch4': Decimal('0.00100'),
        'n2o': Decimal('0.00218'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'notes': 'Average petrol car. EV rental would use Scope 2 grid factor.',
    },
    'personal_car_avg': {
        'name': 'Personal vehicle (mileage reimbursement)',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.17100'),
        'co2': Decimal('0.16900'),
        'ch4': Decimal('0.00080'),
        'n2o': Decimal('0.00120'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'taxi_avg': {
        'name': 'Taxi / rideshare',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.21300'),
        'co2': Decimal('0.21000'),
        'ch4': Decimal('0.00100'),
        'n2o': Decimal('0.00200'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
    },
    'rail_avg': {
        'name': 'Rail (national average)',
        'scope': '3',
        'activity_unit': 'km',
        'factor': Decimal('0.03694'),   # kg CO2e / km (UK national rail avg)
        'co2': Decimal('0.03650'),
        'ch4': Decimal('0.00020'),
        'n2o': Decimal('0.00024'),
        'source': 'DEFRA 2024',
        'source_year': 2024,
        'notes': 'UK national rail average. Eurostar ≈ 0.006 kg CO2e/km.',
    },

    # ── Scope 3: Upstream goods (procurement) ────────────────────────────────
    'upstream_goods': {
        'name': 'Purchased goods and services (spend-based)',
        'scope': '3',
        'activity_unit': 'USD',
        'factor': Decimal('0.31000'),   # kg CO2e / USD spend (EEIO average)
        'co2': Decimal('0.31000'),
        'ch4': Decimal('0.00000'),
        'n2o': Decimal('0.00000'),
        'source': 'US EPA EEIO v2.0',
        'source_year': 2024,
        'notes': 'Spend-based fallback. Activity-based preferred when available.',
    },
}


def get_factor(key: str) -> dict:
    return EMISSION_FACTORS.get(key, {})


def calculate_co2e(activity_value, ef_key: str) -> dict:
    """
    Return dict with co2e_kg, co2_kg, ch4_kg, n2o_kg.
    Returns zeros if factor not found (flags record for review).
    """
    factor_data = get_factor(ef_key)
    if not factor_data:
        return {'co2e_kg': None, 'co2_kg': None, 'ch4_kg': None, 'n2o_kg': None}

    from decimal import Decimal as D
    val = D(str(activity_value))
    return {
        'co2e_kg': val * factor_data['factor'],
        'co2_kg':  val * factor_data.get('co2', D('0')),
        'ch4_kg':  val * factor_data.get('ch4', D('0')),
        'n2o_kg':  val * factor_data.get('n2o', D('0')),
    }
