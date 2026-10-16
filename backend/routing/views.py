import json
import math
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from .services import ProviderError, analyze, geocode_place
@require_GET
def health(request): return JsonResponse({"status":"ok", "service":"routewise-api"})
@require_GET
def geocode(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 3: return JsonResponse({"error":"Search must be at least 3 characters."}, status=400)
    try: return JsonResponse({"results": geocode_place(q)})
    except ProviderError as exc: return JsonResponse({"error": "Geocoding is temporarily unavailable.", "code": exc.code}, status=503 if exc.retryable else 502)
@require_http_methods(["POST"])
def analyze_routes(request):
    try: body = json.loads(request.body)
    except (TypeError, ValueError): return JsonResponse({"error":"Request body must be valid JSON.", "code":"invalid_json"}, status=400)
    if not isinstance(body, dict): return JsonResponse({"error":"Request body must be a JSON object.", "code":"invalid_json"}, status=400)
    required = ["origin", "destination", "departure", "load_lb", "interval_miles"]
    if any(k not in body for k in required): return JsonResponse({"error":"origin, destination, departure, load_lb and interval_miles are required.", "code":"missing_field"}, status=400)
    try: interval = int(body["interval_miles"])
    except (TypeError, ValueError): interval = 0
    if interval not in [10,25,50]: return JsonResponse({"error":"interval_miles must be 10, 25, or 50.", "code":"invalid_interval"}, status=400)
    try:
        load = float(body["load_lb"])
        if not math.isfinite(load) or not 0 <= load <= 100000: raise ValueError("load_lb must be between 0 and 100000.")
        depart = datetime.fromisoformat(str(body["departure"]).replace("Z", "+00:00"))
        if depart.tzinfo is None: raise ValueError("departure must include a timezone.")
        origin, destination = body["origin"], body["destination"]
        if not isinstance(origin, dict) or not isinstance(destination, dict): raise ValueError("origin and destination must include coordinates.")
        for p in (origin, destination):
            lat, lon = float(p["lat"]), float(p["lon"])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError("Invalid coordinate.")
        return JsonResponse(analyze(origin, destination, depart, load, interval))
    except (KeyError, TypeError, ValueError): return JsonResponse({"error":"Provide valid departure, load, and origin/destination coordinates.", "code":"invalid_input"}, status=400)
    except ProviderError as exc: return JsonResponse({"error": "The routing provider is temporarily unavailable. Please retry shortly." if exc.retryable else "The routing provider returned invalid route data.", "code": exc.code}, status=503 if exc.retryable else 502)
    except Exception: return JsonResponse({"error":"Route analysis failed unexpectedly. Please retry.", "code":"internal_error"}, status=500)

