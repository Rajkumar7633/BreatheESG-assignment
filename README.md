# BreatheESG — Emissions Data Ingestion Platform

A Django REST + React application for ingesting emissions and activity data from SAP, utility portals, and corporate travel platforms, normalizing it to GHG Protocol standards, and surfacing a review dashboard where analysts can approve, reject, or flag records before audit lock.

## Live Demo

- **Frontend**: https://breathe-esg-assignment-ruby.vercel.app
- **Backend API**: https://breatheesg-assignment-1.onrender.com
- **Credentials**: `admin / admin123` or `analyst / analyst123`

## Architecture

```
backend/         Django 4.2 + DRF + PostgreSQL
  apps/core/     Organization, User models
  apps/ingestion/ IngestionJob, RawRecord + SAP/Utility/Travel parsers
  apps/emissions/ EmissionRecord, EmissionFactor, normalizers
  apps/review/   ReviewDecision, bulk approve/reject API

frontend/        React 18 + TypeScript + Vite + Tailwind CSS
  pages/Dashboard    Scope 1/2/3 charts, review status
  pages/Ingestion    File upload with drag-and-drop
  pages/Review       Analyst review queue with bulk actions
  pages/Records      Filterable/sortable full record table
  pages/AuditTrail   Immutable decision history

sample_data/     Realistic SAP, Green Button, and Concur CSV files
```

## Running Locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables (or create .env)
export DATABASE_URL=sqlite:///db.sqlite3
export SECRET_KEY=local-dev-secret
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173

python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
# If backend is not on localhost:8000, create .env.local:
# VITE_API_URL=http://localhost:8000/api
npm run dev
```

Open http://localhost:5173

## Deployment (Render + Vercel)

### Backend on Render

1. Create a new Render Web Service, root directory: `backend/`
2. Add a Render PostgreSQL database and link it (use the **internal** URL)
3. Add environment variables:
   ```
   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
   DATABASE_URL=<internal PostgreSQL URL from Render>
   ALLOWED_HOSTS=your-service.onrender.com,localhost
   CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
   DJANGO_SETTINGS_MODULE=config.settings.production
   DEBUG=False
   ```
4. Render uses the `Procfile`: `release` runs `collectstatic`, migrations, and seed data; `web` starts Gunicorn.

### Frontend on Vercel

1. Connect your GitHub repo, set root directory to `frontend/`
2. Add the environment variable:
   ```
   VITE_API_URL=https://your-backend.onrender.com/api
   ```
3. Build command: `npm run build`
4. Output directory: `dist`

## Sample Data

Upload these files to test the system:

| File | Source type | What it tests |
| ---- | ----------- | ------------- |
| `sample_data/sap_mm_fuel.csv` | SAP | Fuel combustion, German plant codes, movement types, large outlier |
| `sample_data/utility_greenbtn.csv` | Utility | Multi-facility, mid-month billing periods, demand row (should skip) |
| `sample_data/concur_travel_export.csv` | Travel | Flights with IATA codes, hotels, car rental, multi-currency |

## Documentation

- [MODEL.md](MODEL.md) — Data model design and reasoning
- [DECISIONS.md](DECISIONS.md) — Every ambiguity resolved
- [TRADEOFFS.md](TRADEOFFS.md) — What was deliberately not built
- [SOURCES.md](SOURCES.md) — Source format research and sample data rationale
