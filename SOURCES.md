# Source Research Notes

---

## 1. SAP Fuel & Procurement Data

### What I researched
SAP's Materials Management (MM) module tracks goods movements. The key transactions for fuel:
- **MB51**: Material Document List — shows all goods movements by material/plant/date
- **MB52**: Warehouse stocks of material
- **SE16N**: Generic table viewer — used by power users to export raw MSEG/MKPF table data

The relevant tables are:
- `MSEG`: Material document segment (each movement line)
- `MKPF`: Material document header
- `MBEW`: Material valuation (for cost data)
- `T001W`: Plant table (to look up plant names from WERKS codes)

### What I learned
1. **German column names**: When a SAP system is configured with German locale, the SE16N export uses German field labels. My parser handles both via `COLUMN_ALIASES`.
2. **Date format**: SAP stores dates internally as `YYYYMMDD` with no separator. This is universal regardless of locale.
3. **Decimal format**: German SAP installations use comma as decimal separator (`1.234,56`). My parser handles both.
4. **SAP unit codes**: The unit of measure in `MEINS` is SAP's internal code, not SI. `TO` = metric ton, `SCF` = standard cubic foot, `MBT` = thousand BTU. These are not obvious.
5. **Movement type meanings**: 261 = goods issue to production order (consumption), 201 = goods issue to cost center. Returns are 262 and 202. 551 is scrapping. Filtering to consumption movements only is essential.
6. **Plant codes are meaningless**: `WERKS` is a 4-character code like `DE01`. Without the `T001W` lookup table, you don't know it's Hamburg. In production, the client provides this mapping.

### My sample data
`sample_data/sap_mm_fuel.csv` uses tab-separated format (common from SAP export tools), contains 18 rows spanning Jan–Apr 2024, includes:
- Multiple plant codes (US01, DE01, UK01, US02, SG01)
- Multiple fuels (diesel, natural gas, LPG, gas oil)
- Movement types 261 and 201 (both consumption), plus one 551 (return — parser should skip or handle)
- One intentionally large diesel transaction at DE01 in March (87,500 litres = 235 tCO2e) to trigger the suspicion flag
- One negative-quantity row to test return handling

### What would break in production
1. Client's SAP uses a custom movement type for fuel issued to vehicles (e.g. 901). Not in our whitelist; would be silently skipped.
2. Material numbers don't follow the `DIESEL-001` pattern — they use numeric codes like `000000000020000101`. Need client-provided material-to-fuel mapping table.
3. Plant `T001W` lookup not automated — requires a one-time export and configuration step.
4. Multi-currency: amounts are in local currency (EUR in Germany, GBP in UK). We ignore cost; we only use quantity. But if a client only has cost data (no quantity), we'd need to handle this.

---

## 2. Utility Electricity Data

### What I researched
The **Green Button Alliance** (greenbuttonalliance.org) is a US DOE initiative that standardized utility customer data. It has two formats:
- **Green Button Download My Data**: CSV or XML, downloaded manually from utility portal
- **Green Button Connect My Data**: OAuth2 API, pulls data automatically

Most utilities that support Green Button offer both. The CSV format follows the ESPI (Energy Services Provider Interface) standard from ANSI/IEEE.

UK utilities don't use "Green Button" branding but export CSV in essentially the same structure (start date, end date, kWh, cost).

Key fields in a Green Button export:
- `ServiceCategory`: Electricity, Gas, Water
- `StartDateTime` / `EndDateTime`: ISO 8601 with timezone
- `ReadingType`: Consumption, Demand, Net Metered Usage
- `Value`: the reading
- `Unit`: kWh, kW (demand), Wh, MWh
- `Cost` / `Currency`: billing amount (informational)

### What I learned
1. **Demand vs. consumption**: Utility exports include both energy (kWh) and demand (kW peak) readings. ESG systems only care about energy consumption — demand is for capacity planning. My parser skips demand rows.
2. **Billing periods**: The period from a utility bill is almost never a calendar month. A January bill might run Dec 18 – Jan 17. Forcing alignment to calendar months requires apportionment; I chose to preserve the billing period as-is.
3. **Interval data**: Some utilities export 15-minute or hourly interval data. These would need aggregation by billing period before computing emissions. My parser doesn't aggregate — it treats each row as a single billing period. An analyst uploading interval data would see many rows, which is expected.
4. **Multi-meter**: A large facility may have many meters. Green Button exports can include all meters from an account, or one per meter. The `MeterID` field identifies which meter.

### My sample data
`sample_data/utility_greenbtn.csv` contains:
- 5 facilities across US, UK, Germany, Singapore
- Mix of calendar-month and mid-month billing periods (Chicago distribution uses 15th-to-15th)
- One demand row (MTR-NYC-001) that the parser should skip
- Amounts in USD, GBP, EUR, SGD (costs are ignored; only kWh matters)
- Different emission factors for US vs. UK (US: 0.386 kg/kWh, UK: 0.207 kg/kWh)

### What would break in production
1. UK utilities don't all use `ServiceCategory`, `StartDateTime` column naming — some use `Period Start`, `Consumption (kWh)`. The parser's `COLUMN_ALIASES` helps but wouldn't cover every utility.
2. Onsite solar: If the meter is net-metered, the `Net Metered Usage` reading may be negative (export to grid). This would produce a negative emission record — correct GHG-Protocol behavior but confusing in the UI.
3. Sub-metering: Tenant-level sub-meters for Scope 3 reporting are a different data model entirely.
4. Half-hourly settlement data (UK): UK grid billing sometimes exports half-hourly AMR data (48 rows per day per meter). 18 months × 48 × 100 meters = 2.6M rows per upload. Background processing is essential.

---

## 3. Corporate Travel (Concur)

### What I researched
**SAP Concur** is the dominant enterprise T&E platform (~50M users, ~60% of Fortune 500). The relevant export is:
- **Analytics > Standard Reports > Expense > Expense Detail**: Produces a per-expense-line CSV

I read the Concur API documentation (developer.concur.com), the Expense Report v3.0 endpoints, and the standard CSV export format.

Alternative I considered: **Navan (TripActions)** — their export schema is similar. Fields are: Traveler Name, Employee ID, Department, Trip Type, Booking Date, Travel Date, Origin, Destination, Class of Service, Ticket Number, Base Fare, Total Fare, Distance (miles).

Key Concur expense types for ESG:
- `Airfare`: Flights booked through travel management company
- `Hotel`: Lodging
- `Car Rental`: Rental vehicles
- `Mileage`: Personal vehicle reimbursement
- `Rail`: Train travel
- `Taxi` / `Uber` / `Rideshare`: Ground transport

### What I learned
1. **Distances not always provided**: When booking is made through Concur Travel (not just expenses), route data is available. For expense reports only (out-of-policy bookings, cash expenses), you often only have origin/destination city names. My parser falls back to Haversine on IATA codes.
2. **Cabin class affects emissions significantly**: Long-haul business class is 2.9× economy per DEFRA. Concur stores class in a subfield; it's often blank for budget travelers. I default to Economy when missing.
3. **Hotel night count**: Concur stores check-in/check-out dates. Some exports also have a `Nights` field. I prioritize the explicit `Nights` field if present, fall back to check-in/check-out delta.
4. **Multi-currency**: Expense amounts are in the traveler's local currency. For ESG purposes, amounts are irrelevant — we derive emissions from distance/nights, not cost. The exception is when distance is unknown, where I use cost as a rough proxy.
5. **Radiative forcing (RF) multiplier**: DEFRA 2024 includes an RF multiplier of 1.891 for aviation, which accounts for contrail and cirrus cloud effects at altitude. Some clients reject this (it's not in the EU ETS standard); others require it. I applied it; it roughly doubles aviation emissions.

### My sample data
`sample_data/concur_travel_export.csv` contains:
- 18 expense rows across 7 employees, Q1–Q2 2024
- Flights with IATA codes (JFK→LHR, JFK→SIN, ORD→LAX, JFK→NRT)
- Hotel stays with check-in/check-out dates and night counts
- A car rental with distance in miles
- A German train (Frankfurt→Munich, 400km)
- A personal vehicle mileage claim
- A long-haul business class flight (JFK→SIN) to test cabin class multiplier
- A hotel with amount in JPY to test currency handling

### What would break in production
1. Expense type taxonomy is client-specific. Concur allows custom expense types — a client might use "EMEA Air" instead of "Airfare". The `EXPENSE_TYPE_MAP` would need to be extended per client.
2. IATA code lookup table covers ~50 airports. Unknown codes are flagged for manual review — but at scale, a full 8000-airport database (available from OurAirports.com, MIT license) is needed.
3. Hotel emission factors are a single global average. The Cornell Hotel Sustainability Benchmarking study has per-country, per-star-rating factors; a real system would use those.
4. Concur doesn't distinguish between personal car (owned) and rental car in all configurations — they both appear as "Car Rental" in some setups. Emission factors differ (rental cars average newer fleet).
