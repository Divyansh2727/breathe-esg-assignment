# Breathe ESG — Data Ingestion Prototype

Django REST + React app for ingesting SAP fuel/procurement, utility electricity, and corporate travel data; normalizing to activity records; and analyst review before audit lock.

## Live demo

Deploy to [Render](https://render.com) using the included `render.yaml` (Docker + PostgreSQL). After deploy:

- **URL:** your Render service URL (e.g. `https://breathe-esg.onrender.com`)
- **Login:** `analyst` / `demo-analyst-2025`

Set `DJANGO_SECRET_KEY` and link the Postgres database in the Render dashboard.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Frontend (dev with proxy)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API proxied to :8000.

### Docker

```powershell
cd "c:\Users\Anirudh Babbar\Desktop\project"
docker compose build --no-cache
docker compose up
```

App on http://localhost:8000 (UI is pre-built in `frontend/dist/` — **no npm inside Docker**).

If your school/corporate network blocks `registry.npmjs.org`, Docker cannot run `npm install`. See [docker/SSL.md](./docker/SSL.md).

To edit the React UI with hot reload: `docker compose -f docker-compose.fast.yml up --build` plus `npm run dev` in `frontend/` (on a network where npm works).

## Sample files

Upload from `sample_data/`:

- `sap_fuel_procurement.csv`
- `utility_electricity.csv`
- `concur_travel.json`

## Documentation (submission)

| File | Contents |
|------|----------|
| [MODEL.md](./MODEL.md) | Data model, tenancy, scope, audit |
| [DECISIONS.md](./DECISIONS.md) | Ambiguities and choices |
| [TRADEOFFS.md](./TRADEOFFS.md) | What we did not build |
| [SOURCES.md](./SOURCES.md) | Research and sample data rationale |

## API (authenticated)

- `POST /api/auth/token/` — JWT login
- `GET /api/me/` — user + organizations
- `POST /api/organizations/{id}/ingest/` — multipart file upload
- `GET /api/organizations/{id}/activities/?status=pending`
- `POST /api/organizations/{id}/activities/{id}/approve/`
- `POST /api/organizations/{id}/activities/{id}/lock/`

## Tech stack

- Django 5, DRF, SimpleJWT, PostgreSQL (SQLite locally)
- React 18, Vite
- Gunicorn + Whitenoise for production
