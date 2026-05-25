"""
Creates a demo organization, users, and sample emission records for the review UI.
Run once after initial migration: python manage.py seed_demo
"""
from datetime import date, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Organization, User
from apps.ingestion.models import IngestionJob, RawRecord
from apps.emissions.models import EmissionRecord
from apps.emissions.normalizers import _get_or_create_emission_factor


DEMO_SAP_ROWS = [
    {
        'raw': {'MANDT': '100', 'BUKRS': '1000', 'WERKS': 'US01', 'MATNR': 'DIESEL-001',
                'MBLNR': '4900001001', 'ZEILE': '0001', 'BUDAT': '20240115',
                'BWART': '261', 'MENGE': '3500.000', 'MEINS': 'L', 'DMBTR': '4900.00', 'WAERS': 'USD'},
        'scope': '1', 'category': 'Stationary Combustion', 'sub_category': 'Diesel',
        'activity_description': 'Diesel consumption at New York HQ',
        'activity_value': Decimal('3500'), 'activity_unit': 'L',
        'co2e_kg': Decimal('9405.62'), 'period_start': date(2024, 1, 15),
        'period_end': date(2024, 1, 15), 'facility': 'New York HQ',
        'ef_key': 'fuel_diesel', 'is_suspicious': False,
    },
    {
        'raw': {'MANDT': '100', 'BUKRS': '1000', 'WERKS': 'DE01', 'MATNR': 'NATGAS-001',
                'MBLNR': '4900001002', 'ZEILE': '0001', 'BUDAT': '20240201',
                'BWART': '261', 'MENGE': '4200.000', 'MEINS': 'M3', 'DMBTR': '2100.00', 'WAERS': 'EUR'},
        'scope': '1', 'category': 'Stationary Combustion', 'sub_category': 'Natural Gas',
        'activity_description': 'Natural gas consumption at Hamburg Manufacturing Plant',
        'activity_value': Decimal('4200'), 'activity_unit': 'M3',
        'co2e_kg': Decimal('8575.98'), 'period_start': date(2024, 2, 1),
        'period_end': date(2024, 2, 1), 'facility': 'Hamburg Manufacturing Plant',
        'ef_key': 'fuel_natural_gas', 'is_suspicious': False,
    },
    {
        'raw': {'MANDT': '100', 'BUKRS': '1000', 'WERKS': 'UK01', 'MATNR': 'DIESEL-001',
                'MBLNR': '4900001003', 'ZEILE': '0001', 'BUDAT': '20240310',
                'BWART': '261', 'MENGE': '87500.000', 'MEINS': 'L', 'DMBTR': '131250.00', 'WAERS': 'GBP'},
        'scope': '1', 'category': 'Stationary Combustion', 'sub_category': 'Diesel',
        'activity_description': 'Diesel consumption at London Office',
        'activity_value': Decimal('87500'), 'activity_unit': 'L',
        'co2e_kg': Decimal('235140.50'), 'period_start': date(2024, 3, 10),
        'period_end': date(2024, 3, 10), 'facility': 'London Office',
        'ef_key': 'fuel_diesel', 'is_suspicious': True,
        'suspicious_reasons': ['CO2e value 235140 kg exceeds single-record threshold of 50000 kg for sap data'],
    },
    {
        'raw': {'MANDT': '100', 'BUKRS': '1000', 'WERKS': 'US02', 'MATNR': 'LPG-001',
                'MBLNR': '4900001004', 'ZEILE': '0001', 'BUDAT': '20240415',
                'BWART': '201', 'MENGE': '1200.000', 'MEINS': 'L', 'DMBTR': '960.00', 'WAERS': 'USD'},
        'scope': '1', 'category': 'Stationary Combustion', 'sub_category': 'LPG',
        'activity_description': 'LPG consumption at Chicago Distribution',
        'activity_value': Decimal('1200'), 'activity_unit': 'L',
        'co2e_kg': Decimal('1815.36'), 'period_start': date(2024, 4, 15),
        'period_end': date(2024, 4, 15), 'facility': 'Chicago Distribution',
        'ef_key': 'fuel_lpg', 'is_suspicious': False,
    },
]

DEMO_UTILITY_ROWS = [
    {
        'raw': {'ServiceCategory': 'Electricity', 'StartDateTime': '2024-01-01T00:00:00Z',
                'EndDateTime': '2024-01-31T23:59:59Z', 'ReadingType': 'Consumption',
                'Value': '45820', 'Unit': 'kWh', 'Cost': '5498.40', 'Currency': 'USD',
                'MeterID': 'MTR-NYC-001', 'Facility': 'New York HQ'},
        'scope': '2', 'category': 'Purchased Electricity', 'sub_category': 'Grid Electricity',
        'activity_description': 'Grid electricity consumption at New York HQ, meter MTR-NYC-001',
        'activity_value': Decimal('45820'), 'activity_unit': 'kWh',
        'co2e_kg': Decimal('17693.60'), 'period_start': date(2024, 1, 1),
        'period_end': date(2024, 1, 31), 'facility': 'New York HQ',
        'cost_center': 'MTR-NYC-001', 'ef_key': 'electricity_us_avg', 'is_suspicious': False,
    },
    {
        'raw': {'ServiceCategory': 'Electricity', 'StartDateTime': '2024-02-01T00:00:00Z',
                'EndDateTime': '2024-02-29T23:59:59Z', 'ReadingType': 'Consumption',
                'Value': '41200', 'Unit': 'kWh', 'Cost': '4944.00', 'Currency': 'USD',
                'MeterID': 'MTR-NYC-001', 'Facility': 'New York HQ'},
        'scope': '2', 'category': 'Purchased Electricity', 'sub_category': 'Grid Electricity',
        'activity_description': 'Grid electricity consumption at New York HQ, meter MTR-NYC-001',
        'activity_value': Decimal('41200'), 'activity_unit': 'kWh',
        'co2e_kg': Decimal('15903.32'), 'period_start': date(2024, 2, 1),
        'period_end': date(2024, 2, 29), 'facility': 'New York HQ',
        'cost_center': 'MTR-NYC-001', 'ef_key': 'electricity_us_avg', 'is_suspicious': False,
    },
    {
        'raw': {'ServiceCategory': 'Electricity', 'StartDateTime': '2024-03-15T00:00:00Z',
                'EndDateTime': '2024-04-14T23:59:59Z', 'ReadingType': 'Consumption',
                'Value': '28650', 'Unit': 'kWh', 'Cost': '3437.00', 'Currency': 'USD',
                'MeterID': 'MTR-CHI-001', 'Facility': 'Chicago Distribution'},
        'scope': '2', 'category': 'Purchased Electricity', 'sub_category': 'Grid Electricity',
        'activity_description': 'Grid electricity consumption at Chicago Distribution, meter MTR-CHI-001',
        'activity_value': Decimal('28650'), 'activity_unit': 'kWh',
        'co2e_kg': Decimal('11063.17'), 'period_start': date(2024, 3, 15),
        'period_end': date(2024, 4, 14), 'facility': 'Chicago Distribution',
        'cost_center': 'MTR-CHI-001', 'ef_key': 'electricity_us_avg', 'is_suspicious': False,
    },
    {
        'raw': {'ServiceCategory': 'Electricity', 'StartDateTime': '2024-01-01T00:00:00Z',
                'EndDateTime': '2024-01-31T23:59:59Z', 'ReadingType': 'Consumption',
                'Value': '22400', 'Unit': 'kWh', 'Cost': '4635.20', 'Currency': 'GBP',
                'MeterID': 'MTR-LDN-001', 'Facility': 'London Office'},
        'scope': '2', 'category': 'Purchased Electricity', 'sub_category': 'Grid Electricity',
        'activity_description': 'Grid electricity consumption at London Office, meter MTR-LDN-001',
        'activity_value': Decimal('22400'), 'activity_unit': 'kWh',
        'co2e_kg': Decimal('4637.92'), 'period_start': date(2024, 1, 1),
        'period_end': date(2024, 1, 31), 'facility': 'London Office',
        'cost_center': 'MTR-LDN-001', 'ef_key': 'electricity_uk', 'is_suspicious': False,
    },
]

DEMO_TRAVEL_ROWS = [
    {
        'raw': {'Report Name': 'Q1 2024 Travel', 'Report ID': 'EXP-2024-001',
                'Employee Name': 'Sarah Chen', 'Employee ID': 'EMP001', 'Cost Center': 'CORP-001',
                'Expense Type': 'Airfare', 'Transaction Date': '2024-01-22',
                'Amount': '1850.00', 'Currency': 'USD', 'Vendor Name': 'Delta Airlines',
                'City From': 'JFK', 'City To': 'LHR', 'Miles/KM': '5540', 'Class': 'Economy', 'Nights': '0'},
        'scope': '3', 'category': 'Business Travel', 'sub_category': 'Air Travel',
        'activity_description': 'Flight: JFK → LHR (Economy) — Sarah Chen',
        'activity_value': Decimal('5540'), 'activity_unit': 'km',
        'co2e_kg': Decimal('1081.36'), 'period_start': date(2024, 1, 22),
        'period_end': date(2024, 1, 22), 'department': 'Sales',
        'cost_center': 'CORP-001', 'ef_key': 'flight_long_haul_economy', 'is_suspicious': False,
    },
    {
        'raw': {'Report Name': 'Q1 2024 Travel', 'Report ID': 'EXP-2024-001',
                'Employee Name': 'Sarah Chen', 'Employee ID': 'EMP001', 'Cost Center': 'CORP-001',
                'Expense Type': 'Hotel', 'Transaction Date': '2024-01-22',
                'Amount': '1280.00', 'Currency': 'GBP', 'Vendor Name': 'The Savoy London',
                'City From': '', 'City To': 'London', 'Miles/KM': '', 'Class': '', 'Nights': '4'},
        'scope': '3', 'category': 'Business Travel', 'sub_category': 'Hotel Stay',
        'activity_description': 'Hotel stay: 4 night(s) in London — Sarah Chen',
        'activity_value': Decimal('4'), 'activity_unit': 'night',
        'co2e_kg': Decimal('82.40'), 'period_start': date(2024, 1, 22),
        'period_end': date(2024, 1, 26), 'department': 'Sales',
        'cost_center': 'CORP-001', 'ef_key': 'hotel_stay', 'is_suspicious': False,
    },
    {
        'raw': {'Report Name': 'Q1 2024 Travel', 'Report ID': 'EXP-2024-002',
                'Employee Name': 'Marcus Williams', 'Employee ID': 'EMP002', 'Cost Center': 'ENG-001',
                'Expense Type': 'Airfare', 'Transaction Date': '2024-02-08',
                'Amount': '4200.00', 'Currency': 'USD', 'Vendor Name': 'British Airways',
                'City From': 'JFK', 'City To': 'SIN', 'Miles/KM': '15300', 'Class': 'Business Class', 'Nights': '0'},
        'scope': '3', 'category': 'Business Travel', 'sub_category': 'Air Travel',
        'activity_description': 'Flight: JFK → SIN (Business Class) — Marcus Williams',
        'activity_value': Decimal('15300'), 'activity_unit': 'km',
        'co2e_kg': Decimal('8657.46'), 'period_start': date(2024, 2, 8),
        'period_end': date(2024, 2, 8), 'department': 'Engineering',
        'cost_center': 'ENG-001', 'ef_key': 'flight_long_haul_business', 'is_suspicious': False,
    },
    {
        'raw': {'Report Name': 'Q1 2024 Travel', 'Report ID': 'EXP-2024-003',
                'Employee Name': 'Emma Torres', 'Employee ID': 'EMP003', 'Cost Center': 'MKTG-001',
                'Expense Type': 'Car Rental', 'Transaction Date': '2024-03-05',
                'Amount': '340.00', 'Currency': 'USD', 'Vendor Name': 'Hertz',
                'City From': 'Chicago', 'City To': 'Chicago', 'Miles/KM': '580', 'Class': '', 'Nights': '0'},
        'scope': '3', 'category': 'Business Travel', 'sub_category': 'Rental Car',
        'activity_description': 'Car rental: Chicago → Chicago (Hertz) — Emma Torres',
        'activity_value': Decimal('933.42'), 'activity_unit': 'km',
        'co2e_kg': Decimal('179.33'), 'period_start': date(2024, 3, 5),
        'period_end': date(2024, 3, 5), 'department': 'Marketing',
        'cost_center': 'MKTG-001', 'ef_key': 'car_rental_avg', 'is_suspicious': False,
    },
    {
        'raw': {'Report Name': 'Q2 2024 Travel', 'Report ID': 'EXP-2024-004',
                'Employee Name': 'David Park', 'Employee ID': 'EMP004', 'Cost Center': 'FIN-001',
                'Expense Type': 'Airfare', 'Transaction Date': '2024-04-14',
                'Amount': '890.00', 'Currency': 'USD', 'Vendor Name': 'United Airlines',
                'City From': 'ORD', 'City To': 'LAX', 'Miles/KM': '2800', 'Class': 'Economy', 'Nights': '0'},
        'scope': '3', 'category': 'Business Travel', 'sub_category': 'Air Travel',
        'activity_description': 'Flight: ORD → LAX (Economy) — David Park',
        'activity_value': Decimal('2800'), 'activity_unit': 'km',
        'co2e_kg': Decimal('605.81'), 'period_start': date(2024, 4, 14),
        'period_end': date(2024, 4, 14), 'department': 'Finance',
        'cost_center': 'FIN-001', 'ef_key': 'flight_medium_haul_economy', 'is_suspicious': False,
    },
]


class Command(BaseCommand):
    help = 'Seed the database with a demo organization, users, and emission records'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Organization
            org, created = Organization.objects.get_or_create(
                slug='acme-corp',
                defaults={
                    'name': 'Acme Corporation',
                    'country': 'US',
                    'reporting_year': 2024,
                }
            )
            if created:
                self.stdout.write(f'Created organization: {org.name}')
            else:
                self.stdout.write(f'Organization exists: {org.name}')

            # Users
            admin_user, _ = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@acmecorp.com',
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'organization': org,
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            admin_user.set_password('admin123')
            admin_user.save()

            analyst, _ = User.objects.get_or_create(
                username='analyst',
                defaults={
                    'email': 'analyst@acmecorp.com',
                    'first_name': 'Jane',
                    'last_name': 'Analyst',
                    'organization': org,
                    'role': 'analyst',
                }
            )
            analyst.set_password('analyst123')
            analyst.save()

            self.stdout.write('Users: admin (admin123), analyst (analyst123)')

            # Create ingestion jobs and emission records
            sources = [
                ('sap', 'sap_mm_fuel_2024.csv', DEMO_SAP_ROWS),
                ('utility', 'utility_greenbtn_2024.csv', DEMO_UTILITY_ROWS),
                ('travel', 'concur_travel_q1q2_2024.csv', DEMO_TRAVEL_ROWS),
            ]

            for source_type, filename, rows in sources:
                job, _ = IngestionJob.objects.get_or_create(
                    organization=org,
                    source_type=source_type,
                    filename=filename,
                    defaults={
                        'status': 'completed',
                        'total_rows': len(rows),
                        'processed_rows': len(rows),
                        'failed_rows': 0,
                        'flagged_rows': sum(1 for r in rows if r.get('is_suspicious')),
                        'created_by': admin_user,
                        'completed_at': datetime.utcnow(),
                    }
                )

                for i, row_data in enumerate(rows, start=2):
                    if EmissionRecord.objects.filter(
                        organization=org,
                        raw_record__ingestion_job=job,
                        raw_record__row_number=i,
                    ).exists():
                        continue

                    raw = RawRecord.objects.create(
                        ingestion_job=job,
                        row_number=i,
                        raw_data=row_data['raw'],
                        parse_errors=[],
                    )

                    ef = _get_or_create_emission_factor(row_data['ef_key'])

                    EmissionRecord.objects.create(
                        organization=org,
                        source_type=source_type,
                        raw_record=raw,
                        emission_factor=ef,
                        scope=row_data['scope'],
                        category=row_data['category'],
                        sub_category=row_data.get('sub_category', ''),
                        activity_description=row_data['activity_description'],
                        activity_value=row_data['activity_value'],
                        activity_unit=row_data['activity_unit'],
                        co2e_kg=row_data['co2e_kg'],
                        period_start=row_data['period_start'],
                        period_end=row_data['period_end'],
                        facility=row_data.get('facility', ''),
                        cost_center=row_data.get('cost_center', ''),
                        department=row_data.get('department', ''),
                        is_suspicious=row_data.get('is_suspicious', False),
                        suspicious_reasons=row_data.get('suspicious_reasons', []),
                        status='flagged' if row_data.get('is_suspicious') else 'pending',
                    )

                self.stdout.write(f'  Seeded {len(rows)} {source_type} records')

        self.stdout.write(self.style.SUCCESS('\nDemo data seeded successfully!'))
        self.stdout.write('Login at /api/auth/token/ with: admin / admin123')
