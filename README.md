# RouteWise

Weather-aware truck routing built with React + TypeScript/Vite, Django REST Framework, OSRM, Nominatim, Open-Meteo, Leaflet and OpenStreetMap.

## Run locally

Prerequisites: Node 18+, npm, Python 3.11+ and pip.

```powershell
cd routewise
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\manage.py migrate
python backend\manage.py runserver
```

In another terminal: `cd routewise\frontend; npm install; npm run dev` and open http://localhost:5173. Backend tests: `python backend/manage.py test routing`. Frontend production check: `cd frontend; npm run build`.

## Provider and algorithm notes

`GET /api/health/`, `GET /api/geocode/?q=...`, and `POST /api/routes/analyze/` are the public endpoints. OSRM returns genuinely available alternatives and the UI never duplicates a route. Open-Meteo hourly data is requested in one batched call per route. Respect public provider policies; use managed or self-hosted endpoints for production volume.

Canonical risk categories are `low`, `moderate`, `high`, `severe`, and `no_travel`. Boundary values use inclusive lower bounds at 25/35/45/55 mph, 0.10/0.25/0.50/1.00 in/h rain, and 0.5/1.0/2.0/3.0 in/h snow. Checkpoint risk is the maximum weather component, then load rules may raise it. Each segment inherits the maximum risk of its two endpoint checkpoints, so miles are counted once between checkpoints.

Routes rank by fewest severe miles, fewest high miles, lowest average risk, then shortest travel time. No-travel routes are excluded whenever a feasible route exists. The slider uses actual Open-Meteo timestamps. The corridor heatmap is a data-driven series of checkpoint circles, not a fabricated raster.

Provider calls use separate connect/read timeouts, bounded retries with jitter, `Retry-After` support, and a bounded in-process cache. If routing succeeds while Open-Meteo is unavailable, the API returns genuine route geometry as a partial result and marks weather/risk/recommendations unavailable; it never treats missing weather as safe. Configure `HTTP_CONNECT_TIMEOUT_SECONDS`, `HTTP_READ_TIMEOUT_SECONDS`, and `HTTP_MAX_RETRIES` for deployment. Serve `frontend/dist` statically and run Django behind Gunicorn/Uvicorn with a strong secret, allowed hosts, a shared cache, rate limiting, and provider monitoring.

