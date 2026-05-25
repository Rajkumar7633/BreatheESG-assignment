# Data Model

## Overview

The model is organized around a core principle: **raw data is sacred, derived data is cheap to recompute**.
Every emission record traces back to an immutable raw row. If we change an emission factor or fix a parsing
bug, we can re-derive the numbers without losing the original evidence.

---

## Entity Relationship

```
Organization
  └── User (many)
  └── IngestionJob (many)
        └── RawRecord (many)                 ← immutable source-of-truth
              └── EmissionRecord (one)        ← derived/normalized
                    └── ReviewDecision (many) ← audit trail
                    └── EmissionFactor (FK)   ← versioned factor table
```

---

## Organizations and Multi-Tenancy

**`Organization`**
- UUID primary key (avoids sequential ID enumeration across tenants)
- Every `IngestionJob`, `EmissionRecord`, and `User` carries an `organization` FK
- All API views filter on `request.user.organization` — a user cannot see another tenant's data
- Superusers (internal staff) can query across orgs via the admin

**`User`** (extends Django `AbstractUser`)
- Roles: `admin`, `analyst`, `viewer`
- All auth is JWT (8h access, 7d refresh); tokens are not stored server-side
- One user → one org (this is a simplification; real multi-client firms would need a many-to-many)

---

## Ingestion Layer

**`IngestionJob`**
- Records each upload: who, when, which file, how many rows succeeded/failed/flagged
- `file_hash` (SHA-256) enables duplicate detection — if the same file is uploaded twice, the API returns a warning (but doesn't block; the user might intentionally reprocess)
- `error_log` stores the first 100 parse errors per job so analysts can understand why rows failed
- Supports three `source_type` values: `sap`, `utility`, `travel`

**`RawRecord`**
- One row per parsed CSV row
- `raw_data` is a JSONField containing the original column→value pairs verbatim
- `parse_errors` is a list of strings describing what went wrong (empty if clean)
- `(ingestion_job, row_number)` is unique — this lets us idempotently reprocess a job
- This is `PROTECT`ed from deletion: you cannot delete a `RawRecord` if it has a derived `EmissionRecord`

---

## Emissions Layer

**`EmissionFactor`**
- Versioned table: same fuel type can have multiple rows (2023, 2024 DEFRA values)
- `source_type` + `source_year` form a natural business key
- Stores CO2, CH4, N2O breakdown so analysts can see gas-level detail (useful for Scope 1 combustion)
- `valid_from`/`valid_to` enable time-aware factor selection (future: auto-select factor for the record's period)

**`EmissionRecord`** — the canonical emission row

| Field | Design reasoning |
|---|---|
| `scope` | GHG Protocol Scope 1/2/3, stored as single char for query efficiency |
| `category` | GHG Protocol category name verbatim (`Stationary Combustion`, `Purchased Electricity`, `Business Travel`) |
| `sub_category` | Drill-down within category (`Diesel`, `Natural Gas`, `Air Travel`) |
| `activity_value` + `activity_unit` | Always stored in a canonical unit after normalization (litres, kWh, km, nights) regardless of source format. A SAP row in US gallons is converted to litres before storage. |
| `co2e_kg` | Computed at ingest time using the emission factor. Stored, not recomputed on read, for query speed. |
| `co2_kg`, `ch4_kg`, `n2o_kg` | Gas-level breakdown for Scope 1 reporting |
| `raw_record` | `OneToOneField` to `RawRecord` — every emission row has exactly one source row |
| `emission_factor` | FK to `EmissionFactor` — which factor version was used, preserving reproducibility |
| `was_edited` + `original_values` | If an analyst corrects a value (e.g. wrong activity quantity), the pre-edit snapshot is stored in `original_values`. This is separate from the audit trail because the audit trail records actions, not values. |
| `is_locked` + `locked_at` | Once locked, no further edits are permitted. Intended to freeze records when they go to the auditor. |
| `is_suspicious` + `suspicious_reasons` | Boolean flag + human-readable list. Set at parse time by heuristic rules (e.g. "value is 4x the monthly average"). Analysts see these as context, not blockers. |

**Scope Classification Logic**
- Scope 1: SAP fuel combustion (diesel, natural gas, LPG, etc.)
- Scope 2: Utility electricity (all grid electricity records)
- Scope 3: Corporate travel (flights, hotels, car rental, rail, ground transport)
- Procurement data from SAP goes to Scope 3 Category 1 (Purchased Goods and Services) using a spend-based factor as a fallback

---

## Review Layer

**`ReviewDecision`**
- Immutable append-only audit trail
- Each approve/reject/flag/edit creates a **new row** — nothing is updated in place
- `changes` JSONField records what changed for `edit` actions: `{"activity_value": {"from": "1000", "to": "1200"}}`
- `bulk_approve` is a distinct action type so auditors can see when something was mass-approved vs. individually reviewed

**Review Status Flow**
```
pending ──approve──► approved ──lock──► [locked]
        ──reject──► rejected
        ──flag────► flagged ──unflag──► pending
                           ──approve──► approved
```

---

## Unit Normalization

All activity values are converted to canonical units at ingest:

| Source | Input units | Canonical unit |
|---|---|---|
| SAP fuel | L, GAL, M3, SCF, KG, TO, MBT | L, M3, KG, kWh |
| Utility electricity | kWh, Wh, MWh, therm, CCF | kWh |
| Travel flights | miles, km | km |
| Travel hotels | nights (or check-in/check-out delta) | night |
| Travel cars | miles, km, or derived from cost | km |

The original value and unit are always preserved in `RawRecord.raw_data`.

---

## Key Indexes

```python
# Fast org+scope+status query (main dashboard filter)
Index(fields=['organization', 'scope', 'status'])

# Time-range queries within an org
Index(fields=['organization', 'period_start', 'period_end'])

# Suspicion queue
Index(fields=['is_suspicious', 'status'])
```

---

## What This Model Does Not Handle (yet)

1. **Market-based Scope 2**: Requires supplier EAC/REC certificate data. Model has `emission_factor` FK which could point to a market-based factor, but no UI for entering certificate data.
2. **Scope 3 Category 11 (Product use)**: Out of scope for this prototype.
3. **Multi-period aggregation locking**: Currently locking is per-record. A real system locks at the reporting period level.
4. **Emission factor overrides per client**: The factor table is global. Real deployments would need per-org factor customization (some clients have PPAs or negotiated grid factors).
