# Tradeoffs — What I Deliberately Did Not Build

---

## 1. Background job processing (Celery + Redis)

**What I built instead**: Synchronous file processing in the upload request.

**Why I skipped it**: Adding Celery and Redis would require 2 additional services to deploy (or a managed Redis instance), a separate worker process, and significant infrastructure configuration. For a prototype where files are small (<1000 rows) and we have a single analyst, synchronous is fine and observable — you upload, you see the result immediately.

**What breaks without it**: Files larger than ~10,000 rows will time out on the load balancer (typically 30s on Railway/Render). Multiple simultaneous uploads by different users will block each other on a single-worker dyno. Progress feedback is impossible synchronously.

**The right call**: For any production client with SAP exports of 50,000+ rows or multiple concurrent users, this is the first thing to add. The `IngestionJob` model's `status` field is specifically designed to support this transition — the job is created synchronously, processing happens async, status is polled by the frontend.

---

## 2. Market-based Scope 2 accounting

**What I built instead**: Location-based Scope 2 using grid emission factors.

**Why I skipped it**: Market-based Scope 2 requires matching consumption records to Energy Attribute Certificates (EACs, RECs, GOs) or supplier-specific emission factors. This means:
- A certificate upload flow (different from activity data)
- Certificate validity period tracking
- Residual mix factors for uncovered consumption
- Separate location-based and market-based totals in reporting

This is a meaningful piece of work, and getting it wrong (e.g. double-counting RECs) would produce incorrect reported emissions. Location-based is unambiguous and defensible to auditors.

**The right call**: Enterprise clients with renewable energy procurement (PPAs, RECs) will need this. The emission factor table is structured to support market-based factors — you'd add EF records with `source_type='electricity_market_<supplier>'` and link them via a certificate matching service.

---

## 3. Automated anomaly detection using per-client baselines

**What I built instead**: Static heuristic thresholds (e.g. "single record > 500 tCO2e is suspicious").

**Why I skipped it**: Meaningful anomaly detection requires historical data and per-facility baselines. A 500 kL diesel delivery is suspicious for an office but normal for a shipping depot. Building this properly means:
- A training phase (first 6–12 months of data)
- Per-facility, per-category regression models or rolling Z-score baselines
- Configuration to set per-client sensitivity thresholds

**The right call**: Static thresholds are better than nothing for a first ingest. They catch the obvious problems (10x outliers, negative values, unit conversion errors). The `suspicious_reasons` field is a list specifically because we'll add more check types over time.

---

## Honorable mentions (also deliberately excluded)

**Scope 3 Category 1 (purchased goods)**: SAP procurement data can drive spend-based Scope 3 estimates. I have the emission factor key (`upstream_goods`) and the parser could be extended. I excluded it because the spend-based EEIO factors are very approximate and I didn't want to present a number that would mislead analysts about data quality.

**PDF bill parsing**: The utility portal CSV is correct for data quality. PDF → OCR is a different product, not a different feature.

**Scheduled API pulls from Concur/SAP Gateway**: The file upload model is sufficient for a prototype. API pull would require client credentials and a scheduler — that's week 2 work.
