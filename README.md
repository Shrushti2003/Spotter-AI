
# RouteWise — Weather-Aware Truck Routing

RouteWise is a weather-aware truck-routing application designed to help users compare driving routes using route geometry, forecast conditions, truck-load considerations, and weather-based risk analysis.

Built with React, TypeScript, Django REST Framework, OSRM, Nominatim, Open-Meteo, Leaflet, and OpenStreetMap, RouteWise combines routing and weather information in an interactive interface to support more informed trip planning.

## Features

- **Route planning:** Enter an origin, destination, departure date and time, and truck load.
- **Route alternatives:** Display genuine alternative routes returned by the routing provider when available. Duplicate routes are not presented as alternatives.
- **Interactive map:** Visualize route geometry using Leaflet and OpenStreetMap.
- **Weather-aware analysis:** Retrieve hourly forecasts from Open-Meteo and associate forecast data with route checkpoints.
- **Configurable sampling:** Sample weather along routes at intervals of 10, 25, or 50 miles.
- **Checkpoint analysis:** Inspect checkpoint locations, estimated arrival times, and forecast availability.
- **Risk assessment:** Evaluate available weather conditions using defined risk categories and applicable load-related rules.
- **Route comparison:** Compare route distance, estimated travel time, and risk indicators when sufficient data is available.
- **Forecast timeline:** Explore supported forecast hours using the forecast-time slider.
- **Graceful error handling:** Preserve valid route results when weather services fail, while explicitly identifying unavailable weather information.
- **Input validation:** Validate trip details before performing route analysis.

> **Safety note:** RouteWise is a trip-planning and decision-support tool, not a certified transportation safety system. Forecasts and risk estimates may be incomplete or unavailable. Always verify current road, weather, vehicle, and regulatory conditions before travelling.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript |
| Frontend tooling | Vite |
| Backend | Python, Django, Django REST Framework |
| Routing | OSRM |
| Geocoding | Nominatim |
| Weather forecasts | Open-Meteo |
| Maps | Leaflet, React Leaflet, OpenStreetMap |
| HTTP requests | Python Requests |
| Database | Django-configured database; SQLite for local development |

## Architecture

```text
React + TypeScript + Vite
          |
          | HTTP / JSON
          v
Django REST Framework
          |
          +---- OSRM
          |       Route geometry,
          |       distance and duration
          |
          +---- Nominatim
          |       Location search
          |
          +---- Open-Meteo
                  Hourly forecasts
          |
          v
Checkpoint Generation
          |
          v
Weather and Load Risk Analysis
          |
          v
Route Comparison and Results
          |
          v
Interactive Map and Dashboard
```

The backend coordinates external provider requests and prepares route-analysis results for the frontend. If routing succeeds but weather data is unavailable, the application can preserve valid route information while marking weather-dependent results as incomplete.

## Project Structure

```text
routewise/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── routewise/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── routing/
│       ├── services.py
│       ├── risk.py
│       ├── views.py
│       ├── urls.py
│       └── tests.py
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

Install the following before running the project:

- Python 3.11 or later, using a version supported by the installed dependencies.
- Node.js 18 or later.
- npm.
- Git, if cloning the repository.

The application also needs network access to the configured routing, geocoding, and weather providers for live external data.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Shrushti2003/Spotter-AI.git
cd Spotter-AI
```

If RouteWise is already present in your local workspace, skip cloning and open the directory containing `backend/`, `frontend/`, and `.env.example`.

### 2. Configure environment variables

From the project root, run this in PowerShell:

```powershell
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}
```

This preserves an existing `.env` file.

The example configuration may contain the following settings. Verify the actual names and defaults in `.env.example` before using them:

```dotenv
DJANGO_SECRET_KEY=replace-me
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_ORIGIN=http://localhost:5173

OSRM_BASE_URL=https://router.project-osrm.org
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/forecast

HTTP_TIMEOUT_SECONDS=12
HTTP_CONNECT_TIMEOUT_SECONDS=3
HTTP_READ_TIMEOUT_SECONDS=8
HTTP_MAX_RETRIES=2
```

These are development examples, not production secrets. Use the variable names supported by the actual application.

Before deployment, configure a strong Django secret key, disable debug mode, set the appropriate allowed hosts and frontend origin, and review timeout and retry settings.

**Never commit your actual `.env` file or credentials to GitHub.**

### 3. Set up the Python backend

Open a PowerShell terminal at the project root.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
python -m pip install -r backend\requirements.txt
```

Apply database migrations:

```powershell
python backend\manage.py migrate
```

Run Django's system checks:

```powershell
python backend\manage.py check
```

Start the backend server:

```powershell
python backend\manage.py runserver
```

The backend should be available at:

`http://127.0.0.1:8000/`

Keep this terminal open while using the application.

### 4. Set up the frontend

Open a second VS Code terminal. Keep the backend running.

```powershell
cd frontend
npm install
npm run dev
```

Vite will display the local development URL, normally:

`http://localhost:5173/`

Open the displayed URL in your browser.

### 5. Run the application

1. Start Django in the first terminal.
2. Start Vite in the second terminal.
3. Enter an origin and destination.
4. Select the departure date and time.
5. Enter the truck load in pounds.
6. Choose a weather sampling interval.
7. Click **Analyze routes**.
8. Review the available routes, map, forecast information, and checkpoint analysis.

Results depend on external provider availability, the selected departure time, and the forecast horizon.

## API Endpoints

The backend exposes the following endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health/` | Check API health |
| GET | `/api/geocode/?q=...` | Search for locations |
| POST | `/api/routes/analyze/` | Analyze a trip and return route results |

### Route analysis request

The route-analysis endpoint accepts a JSON request containing trip details expected by the existing backend API.

Example request shape:

```json
{
  "origin": "Denver, Colorado, United States",
  "destination": "Kansas City, Missouri, United States",
  "departure_time": "2026-10-20T09:00:00",
  "load_lbs": 3600,
  "sampling_interval_miles": 25
}
```

This illustrates the intended information; the exact field names must match the current API implementation.

### Example health check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

For detailed API behavior, refer to the backend URL configuration, views, and serializers.

## Routing and Risk Methodology

### Route generation

RouteWise uses OSRM to obtain route geometry, distance, duration, and genuine alternatives supported by the configured service.

The application does not manufacture route alternatives. If the provider returns only one distinct route, the application should report that limitation rather than duplicating a route.

### Weather sampling

Forecast data is associated with checkpoints along the route. The selected sampling interval determines the approximate spacing between checkpoints.

Hourly forecasts are matched to estimated checkpoint arrival times. Forecast coverage depends on the provider, requested departure time, and supported forecast horizon.

### Risk categories

The backend defines the following canonical risk categories:

- `low`
- `moderate`
- `high`
- `severe`
- `no_travel`

Weather risk is calculated using the implemented weather thresholds. Applicable load-related rules may raise checkpoint risk.

Each segment inherits the maximum risk of its two endpoint checkpoints, preventing the same segment from being counted repeatedly in route-level mileage calculations.

Routes are ranked using the configured criteria, including severe-risk miles, high-risk miles, average risk, and travel time. Routes marked no-travel are excluded when a feasible alternative exists.

These calculations are decision-support estimates, not guarantees of actual road safety. The exact thresholds and formulas should be verified against the implementation.

### Missing weather data

Weather availability and route availability are treated separately.

If route generation succeeds but weather retrieval fails:

- Genuine route geometry can remain available.
- Affected weather checkpoints are marked unavailable.
- Weather-dependent risk calculations and recommendations are identified as incomplete.
- Missing forecasts are not silently interpreted as safe conditions.

## Configuration and External Providers

RouteWise uses public provider endpoints by default:

- **OSRM:** `https://router.project-osrm.org`
- **Nominatim:** `https://nominatim.openstreetmap.org`
- **Open-Meteo:** `https://api.open-meteo.com/v1/forecast`

The service URLs and HTTP timeout/retry behavior can be configured through the environment variables documented in `.env.example`.

Public services have usage policies, rate limits, and availability constraints. Use appropriately managed or self-hosted services for production traffic where necessary. Respect each provider's attribution and usage requirements.

The backend implements bounded retries and caching to reduce avoidable requests. Actual live data availability still depends on network connectivity and upstream service health.

## Testing and Build Verification

### Backend tests

From the project root, activate the virtual environment and run:

```powershell
python backend\manage.py test routing
```

### Django system checks

```powershell
python backend\manage.py check
```

### Frontend production build

```powershell
cd frontend
npm run build
```

The production build performs TypeScript compilation and creates optimized frontend assets in `frontend/dist/`.

External-provider tests should use mocked responses so the test suite does not depend on live API availability.

## Troubleshooting

### Python is not recognized

Verify the installation:

```powershell
python --version
python -m pip --version
```

If Windows cannot find Python, install it and enable the PATH option in the installer. Restart VS Code after installation if necessary.

### Virtual environment activation fails

Ensure the virtual environment exists:

```powershell
Test-Path .\.venv\Scripts\Activate.ps1
```

If it does not exist, create it from the project root:

```powershell
python -m venv .venv
```

### Frontend cannot connect to Django

Confirm that the backend is running at `http://127.0.0.1:8000/`, inspect the browser console, and verify the configured frontend origin and API URL.

### Route analysis fails

Inspect the Django terminal for provider errors and verify the configured OSRM endpoint and network connectivity.

### Weather is unavailable

Weather may be unavailable because of a timeout, provider outage, invalid request, rate limit, or a forecast outside the supported horizon.

Check backend logs and retry after confirming connectivity. Valid route results may remain available even when weather data cannot be retrieved. Do not interpret unavailable forecasts as evidence of safe conditions.

### npm reports vulnerabilities

Review the audit details before changing dependencies:

```powershell
npm audit
```

Do not automatically use `npm audit fix --force`, as it can introduce breaking dependency changes.

## Production Deployment Considerations

Before deploying RouteWise publicly:

- Set `DEBUG=false`.
- Use a strong secret key supplied through environment variables.
- Configure `ALLOWED_HOSTS` and CORS for the actual deployment domains.
- Run Django behind a production WSGI or ASGI server.
- Serve the built frontend through appropriate static hosting or a web server.
- Use managed or self-hosted provider infrastructure when required by traffic volume and provider policies.
- Configure appropriate caching, rate limiting, logging, monitoring, and timeouts.
- Keep secrets out of source control.
- Test the deployed application against live routing and weather services.
- Verify forecast freshness and communicate missing or incomplete data to users.

The Django development server and Vite development server are intended for local development, not production hosting.

## Current Verification Status

The following checks were reported during the latest development verification:

- **Backend tests:** 11 tests passed.
- **Django system checks:** Passed.
- **Frontend production build:** Passed.
- **Mocked provider-failure and route-alternative regression tests:** Passed.

Live OSRM, Open-Meteo, and Nominatim connectivity could not be verified in that test environment because external requests failed with connection errors. Consequently, successful live weather retrieval has not been established by those tests.

Re-run the checks after subsequent changes and verify live provider connectivity in the target deployment environment.

## Author

**Shrushti Swarnakar**

GitHub: [@Shrushti2003](https://github.com/Shrushti2003)
