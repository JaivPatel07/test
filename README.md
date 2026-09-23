# Aegis Terrain

AI-powered hyper-local landslide and flash-flood early warning platform for hilly regions of India.

This repository is organized as two applications:

```text
frontend/   React + Vite command-center interface
backend/    Django + Django REST Framework API
```

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

The API is available at `http://localhost:8000/api/`. JWT endpoints are available at `/api/token/` and `/api/token/refresh/`.

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The React app is available at `http://localhost:5173/`. Vite proxies `/api` requests to Django on port 8000.

Demo officer account:

```text
Email: riya@aegisterrain.in
Password: demo123
```

## API surface

- `/api/health/`
- `/api/locations/`
- `/api/locations/{id}/risk/`
- `/api/alerts/`
- `/api/incidents/`
- `/api/shelters/`
- `/api/data-health/`
- `/api/models/`
- `/api/sensors/`
- `/api/sensors/data/`
- `/api/token/`

The seeded data is intentionally simulated for the prototype. Replace SQLite with PostgreSQL/PostGIS, connect approved weather/rainfall/terrain providers, and add the validated ML inference service before production deployment. See `ARCHITECTURE.md` for the production boundary and safety requirements.
