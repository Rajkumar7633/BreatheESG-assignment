# Decision Log

Every ambiguity I resolved, what I chose, why, and what I'd ask the PM.

---

## SAP: Format Selection

**Ambiguity**: SAP exposes data through IDoc, flat-file exports, OData services, and BAPI function modules.

**Decision**: Flat-file CSV/TSV export from transaction MB51 (Material Document List) or SE16N (table viewer).

**Reasoning**:
- IDoc is designed for EDI partner integration, not for periodic ESG reporting. It requires configuration by SAP Basis and produces deeply nested XML that has to be parsed against a message type definition.
- OData via SAP Gateway is the modern approach but requires a Gateway installation and OAuth setup — most enterprise SAP systems don't have this configured for ad-hoc reporting.
- Flat-file export is what sustainability leads actually do: they run MB51, press "Export to Excel", and attach it to an email. It's universal, offline, and doesn't require IT involvement.

**What I'd ask the PM**: Does this client have SAP Gateway deployed? If yes, an OData pull would be more reliable than waiting for someone to email a file.

---

## SAP: Which module / which data

**Decision**: SAP MM (Materials Management) movement data — specifically movement types 261 (goods issue for order) and 201 (goods issue to cost center), which represent actual fuel consumption.

**Reasoning**: Scope 1 emissions come from direct fuel combustion. In SAP, fuel consumption shows up in MM as goods movements from storage locations to production orders or cost centers. Movement type 261 is the canonical "consumed by production" code; 201 is "consumed by cost center" (e.g. a building's generator).

I explicitly filter out returns (551, 502) and exclude adjustment movements. This is a simplification — a real system would need to handle reversal logic.

**What I ignored**: Procurement of non-fuel goods (raw materials, packaging) which would be Scope 3 Category 1. The model supports it (the `upstream_goods` emission factor key exists) but the sample data focuses on fuel.

---

## Utility: Format Selection

**Decision**: Green Button Alliance CSV export.

**Reasoning**: Green Button is a US DOE initiative that became the de facto standard for utility data portability. Most major US utilities (ConEd, PG&E, National Grid, ComEd) offer Green Button downloads from their customer portal. UK utilities (E.ON, EDF) have similar CSV export formats. 

The alternative was PDF bills + OCR. I rejected this because:
1. OCR accuracy on utility bills is 85–95%; errors flow directly into reported emissions
2. Bill formats vary by utility and change without notice
3. Even well-structured PDFs require per-utility parsing rules

**What I ignored**: Green Button also has an XML format (ESPI standard) and an API (Connect My Data). I handle only CSV because that's what a facilities manager will email you.

---

## Utility: Billing period alignment

**Decision**: Store `period_start` and `period_end` as the actual billing dates from the file, even if they don't align with calendar months.

**Reasoning**: Billing periods from 15th to 15th are normal. Forcing alignment to calendar months would require apportioning consumption (e.g. 15/31 of a billing period assigned to month 1) which introduces rounding error and makes the audit trail harder to follow. Auditors want to match the bill to the number, not a calendar aggregate.

**What I'd ask the PM**: Does the client have internal monthly reporting targets? If so, we'd need a separate aggregation view that apportions to calendar months.

---

## Travel: Format Selection

**Decision**: Concur expense report CSV export.

**Reasoning**: Concur (SAP Concur) holds ~50% of the enterprise T&E market. The "Expense Detail" export is well-documented and consistent. Navan/TripActions uses a nearly identical schema. The main alternative was direct API integration (Concur has a REST API), but that requires OAuth and client IT involvement — not achievable in 4 days without real client credentials.

**What I ignored**: 
- Direct booking data from GDS (Global Distribution Systems like Sabre, Amadeus) — more accurate but requires GDS access
- Car rental telematics data — actual km driven vs. estimated
- Rail ticket data in EU (different operator APIs per country)

---

## Travel: Flight distance calculation

**Decision**: Haversine great-circle distance from IATA airport coordinates, with a hardcoded lookup table of ~50 major business travel hubs.

**Reasoning**: Concur sometimes includes mileage, sometimes doesn't. When it does, it's often in miles for US travelers and km for European travelers (determined by the Concur configuration). When it doesn't, we need to derive it.

I chose Haversine over straight crow-fly distance from city names because:
1. Airport-to-airport is more accurate than city-to-city (airports are outside cities)
2. IATA codes are standardized; city names are free text and ambiguous ("London" — which airport?)

The 50-airport table covers the vast majority of corporate travel routes. Unknown airports are flagged as suspicious for analyst review.

**What I'd ask the PM**: Does the client use Concur's travel booking module? If so, we could pull actual trip records (segment-level, with actual aircraft type) from the Concur Travel API, which would be more accurate than the expense report.

---

## Emission Factors: Source selection

**Decision**: DEFRA 2024 for UK records, US EPA eGRID 2023 for US electricity, ICAO methodology for aviation.

**Reasoning**: DEFRA publishes annually updated, GHG-Protocol-aligned conversion factors covering fuels, electricity, and travel. It's the standard used by most UK/EU sustainability consultants and is accepted by KPMG, Deloitte, and the major auditors.

For US electricity, EPA eGRID 2023 gives national and regional subgrid factors. I used the national average; a real system would use the subgrid based on the facility's ZIP code.

For flights, I applied DEFRA's radiative forcing multiplier of 1.891 — this accounts for contrail and cirrus effects at altitude, which roughly double the climate impact of aviation CO2. Some clients don't want this applied (it's debated); I'd make it configurable.

---

## Review workflow: Synchronous processing

**Decision**: File processing is synchronous in the upload request (no Celery/background tasks).

**Reasoning**: For a prototype, simplicity wins. A 1000-row SAP CSV takes <1 second to parse. Background tasks would add Redis + Celery infrastructure complexity.

**What I'd change in production**: Files > 10,000 rows should be queued. The architecture already supports it — the `IngestionJob` model has a `status` field that transitions from `pending → processing → completed`.

---

## Authentication: JWT vs. Session

**Decision**: JWT via django-simplejwt.

**Reasoning**: The frontend is a separate SPA deployed on a different domain. Session auth requires cookie sharing across domains (CORS issues, SameSite restrictions). JWT is simpler to deploy in this setup and works well for a 4-day prototype. In production, we'd add token rotation, shorter lifetimes, and consider OAuth2 for SSO.

---

## What I'd ask the PM before going to production

1. Do you want location-based or market-based Scope 2? (Market-based requires EAC/REC certificate upload)
2. What's the reporting period? Calendar year or fiscal? The data model supports either but the UI assumes calendar.
3. How many concurrent users? The synchronous processing will bottleneck with > 10 simultaneous large uploads.
4. Do we need Scope 3 Category 1 (purchased goods) from SAP procurement data? I have the model for it but no sample data.
5. What's the audit workflow? Who are the auditors — internal team or external firm? Do they need read-only access or will they work in the system?
