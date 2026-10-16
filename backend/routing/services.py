"""Provider integrations and route/weather analysis."""
import hashlib, json, math, os, random, threading, time
from collections import OrderedDict
from datetime import datetime as DateTime, timedelta, timezone
from email.utils import parsedate_to_datetime
import requests
from .risk import Risk, checkpoint_risk, risk_name

OSRM = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
NOMINATIM = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
METEO = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
_TIMEOUT = (float(os.getenv("HTTP_CONNECT_TIMEOUT_SECONDS", "3")), float(os.getenv("HTTP_READ_TIMEOUT_SECONDS", os.getenv("HTTP_TIMEOUT_SECONDS", "8"))))
_MAX_RETRIES = max(0, min(3, int(os.getenv("HTTP_MAX_RETRIES", "2"))))
_SESSION, _CACHE, _CACHE_LOCK = requests.Session(), OrderedDict(), threading.Lock()
_CACHE_MAX = 256

class ProviderError(Exception):
    def __init__(self, provider, code, message, retryable=False):
        super().__init__(message); self.provider, self.code, self.retryable = provider, code, retryable

def _retry_after(response):
    value = response.headers.get("Retry-After") if getattr(response, "headers", None) else None
    if not value: return None
    try: return max(0.0, min(5.0, float(value)))
    except ValueError:
        try: return max(0.0, min(5.0, (parsedate_to_datetime(value) - DateTime.now(timezone.utc)).total_seconds()))
        except (TypeError, ValueError, OverflowError): return None

def _request_json(provider, url, params=None, headers=None, cache_ttl=0):
    key = hashlib.sha256(json.dumps([url, params or {}], sort_keys=True, default=str).encode()).hexdigest(); now = time.monotonic()
    if cache_ttl:
        with _CACHE_LOCK:
            item = _CACHE.get(key)
            if item and now < item[0]: _CACHE.move_to_end(key); return item[1]
            if item: _CACHE.pop(key, None)
    last_error = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = _SESSION.get(url, params=params, headers=headers, timeout=_TIMEOUT); status = response.status_code
            if status == 429 or status >= 500:
                if attempt < _MAX_RETRIES:
                    delay = _retry_after(response)
                    if delay is None: delay = min(4.0, .35 * (2 ** attempt)) + random.uniform(0, .2)
                    time.sleep(delay); continue
                raise ProviderError(provider, "upstream_unavailable", f"{provider} did not respond successfully.", True)
            if status >= 400: raise ProviderError(provider, "upstream_rejected", f"{provider} rejected the request.")
            try: data = response.json()
            except (ValueError, json.JSONDecodeError) as exc: raise ProviderError(provider, "invalid_upstream_json", f"{provider} returned malformed data.") from exc
            if cache_ttl:
                with _CACHE_LOCK:
                    _CACHE[key] = (time.monotonic() + cache_ttl, data); _CACHE.move_to_end(key)
                    while len(_CACHE) > _CACHE_MAX: _CACHE.popitem(last=False)
            return data
        except ProviderError: raise
        except (requests.Timeout, requests.ConnectionError, requests.exceptions.RequestException) as exc:
            last_error = exc
            if attempt < _MAX_RETRIES: time.sleep(min(4.0, .35 * (2 ** attempt)) + random.uniform(0, .2)); continue
            raise ProviderError(provider, "upstream_unavailable", f"{provider} is temporarily unavailable.", True) from exc
    raise ProviderError(provider, "upstream_unavailable", f"{provider} is temporarily unavailable.", True) from last_error

def _coordinate(value, name):
    try: value = float(value)
    except (TypeError, ValueError): raise ValueError(f"{name} must be a number.")
    if not math.isfinite(value): raise ValueError(f"{name} must be finite.")
    return value

def geocode_place(query):
    data = _request_json("Geocoding", f"{NOMINATIM}/search", {"q": query, "format": "jsonv2", "limit": 5}, {"User-Agent": "RouteWise/1.0"}, 3600)
    if not isinstance(data, list): raise ProviderError("Geocoding", "invalid_upstream_schema", "Geocoding returned an invalid response.")
    results = []
    for item in data:
        if not isinstance(item, dict) or "lat" not in item or "lon" not in item: continue
        lat, lon = _coordinate(item["lat"], "latitude"), _coordinate(item["lon"], "longitude")
        if -90 <= lat <= 90 and -180 <= lon <= 180: results.append({"display_name": str(item.get("display_name") or query), "lat": lat, "lon": lon})
    return results

def haversine(a, b):
    lon1, lat1 = map(math.radians, a); lon2, lat2 = map(math.radians, b); dlat, dlon = lat2-lat1, lon2-lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 3958.7613 * 2 * math.asin(math.sqrt(h))

def cumulative_distances(coords):
    out = [0.0]
    for a, b in zip(coords, coords[1:]): out.append(out[-1] + haversine(a, b))
    return out

def interpolate_checkpoint(coords, distances, target):
    if target <= 0: return coords[0]
    if target >= distances[-1]: return coords[-1]
    for i in range(1, len(distances)):
        if distances[i] >= target:
            span = distances[i]-distances[i-1]; t = (target-distances[i-1])/span if span else 0
            return [coords[i-1][0]+(coords[i][0]-coords[i-1][0])*t, coords[i-1][1]+(coords[i][1]-coords[i-1][1])*t]
    return coords[-1]

def build_checkpoints(coords, route_miles, interval):
    distances = cumulative_distances(coords); targets = [0.0] + [float(x) for x in range(interval, math.ceil(route_miles), interval)] + ([route_miles] if route_miles else []); result = []
    for target in targets:
        point = interpolate_checkpoint(coords, distances, target)
        if not result or haversine(point, result[-1]["coordinates"]) > .01: result.append({"distance_miles": round(target, 2), "coordinates": point})
    return result

def iso_hour(dt): return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")

def _number(values, index):
    if not isinstance(values, list) or index >= len(values) or values[index] is None: return None
    try: value = float(values[index])
    except (TypeError, ValueError): return None
    return value if math.isfinite(value) and value >= 0 else None

def weather_for_checkpoints(checkpoints, depart, speed_mph):
    params = {"latitude": ",".join(str(round(x["coordinates"][1], 5)) for x in checkpoints), "longitude": ",".join(str(round(x["coordinates"][0], 5)) for x in checkpoints), "hourly": "wind_speed_10m,precipitation,rain,snowfall", "forecast_days": 3, "timezone": "UTC"}
    data = _request_json("Weather", METEO, params, cache_ttl=300); rows = data if isinstance(data, list) else [data]
    if not rows or not all(isinstance(row, dict) for row in rows): raise ProviderError("Weather", "invalid_upstream_schema", "Weather returned an invalid response.")
    first = rows[0].get("hourly", {}).get("time", []) if isinstance(rows[0].get("hourly"), dict) else []
    for i, cp in enumerate(checkpoints):
        eta = depart + timedelta(hours=cp["distance_miles"] / max(speed_mph, 1)); hourly = rows[min(i, len(rows)-1)].get("hourly", {}); times = hourly.get("time", []) if isinstance(hourly, dict) else []
        if not times or not all(isinstance(x, str) for x in times): cp["weather"] = {"available": False, "source": "forecast", "reason": "Provider returned no usable hourly data."}; continue
        try:
            wanted = DateTime.fromisoformat(iso_hour(eta).replace("Z", "+00:00")); parsed = [DateTime.fromisoformat(x.replace("Z", "+00:00")) for x in times]; idx = min(range(len(parsed)), key=lambda j: abs(parsed[j]-wanted)); actual = parsed[idx]
        except (ValueError, TypeError): cp["weather"] = {"available": False, "source": "forecast", "reason": "Provider returned invalid forecast timestamps."}; continue
        if abs(actual-wanted).total_seconds() > 7200: cp["weather"] = {"available": False, "source": "forecast", "reason": "Forecast timestamp is outside provider coverage."}; continue
        values = {name: _number(hourly.get(name), idx) for name in ("wind_speed_10m", "rain", "precipitation", "snowfall")}
        if any(value is None for value in values.values()): cp["weather"] = {"available": False, "source": "forecast", "reason": "Provider returned incomplete weather values."}; continue
        cp["weather"] = {"available": True, "source": "forecast", "timestamp": times[idx], "wind_mph": round(values["wind_speed_10m"]*.621371, 3), "rain_inph": round(values["rain"]*.0393701, 3), "precipitation_inph": round(values["precipitation"]*.0393701, 3), "snow_inph": round(values["snowfall"]*.0393701, 3)}; cp["estimated_arrival"] = eta.isoformat()
    for cp in checkpoints: cp.setdefault("estimated_arrival", (depart + timedelta(hours=cp["distance_miles"]/max(speed_mph, 1))).isoformat())
    return checkpoints, first[0] if first else None, first[-1] if first else None

def summarize(route):
    miles = {risk_name(r): 0.0 for r in Risk}; scores = []; unavailable = 0.0
    for a, b in zip(route["checkpoints"], route["checkpoints"][1:]):
        segment = b["distance_miles"]-a["distance_miles"]
        if a.get("risk_value", -1) < 0 or b.get("risk_value", -1) < 0: unavailable += segment; continue
        risk = Risk(max(a["risk_value"], b["risk_value"])); miles[risk_name(risk)] += segment; scores.append(int(risk))
    route["risk_summary"] = {k: round(v, 2) for k, v in miles.items()}; route["weather_unavailable_miles"] = round(unavailable, 2); route["weather_available"] = unavailable == 0 and all(cp["weather"].get("available") for cp in route["checkpoints"]); route["average_risk"] = round(sum(scores)/len(scores), 3) if scores and route["weather_available"] else None; route["has_no_travel"] = miles["no_travel"] > 0; route["risk_score"] = round(route["average_risk"]*25+miles["severe"]*2+miles["no_travel"]*5, 1) if route["average_risk"] is not None else None; return route

def get_routes(origin, destination):
    coords = f"{origin['lon']},{origin['lat']};{destination['lon']},{destination['lat']}"; data = _request_json("Routing", f"{OSRM}/route/v1/driving/{coords}", {"alternatives":"true", "overview":"full", "geometries":"geojson", "steps":"false"}, cache_ttl=180)
    if not isinstance(data, dict) or data.get("code") != "Ok" or not isinstance(data.get("routes"), list) or not data["routes"]: raise ProviderError("Routing", "invalid_upstream_schema", "The routing provider returned no usable driving route.")
    routes = []
    for i, route in enumerate(data["routes"]):
        geometry = route.get("geometry", {}).get("coordinates") if isinstance(route, dict) else None
        try: distance, duration = float(route["distance"]), float(route["duration"])
        except (KeyError, TypeError, ValueError): continue
        if not isinstance(geometry, list) or len(geometry) < 2 or not math.isfinite(distance) or not math.isfinite(duration) or distance <= 0 or duration <= 0: continue
        try:
            geometry = [[_coordinate(point[0], "route longitude"), _coordinate(point[1], "route latitude")] for point in geometry]
        except (IndexError, KeyError, TypeError, ValueError): continue
        if any(not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90) for point in geometry): continue
        routes.append({"id":f"route-{i+1}", "geometry":geometry, "distance_miles":distance/1609.344, "duration_minutes":duration/60})
    if not routes: raise ProviderError("Routing", "invalid_upstream_schema", "The routing provider returned no usable route geometry.")
    return routes

def analyze(origin, destination, depart, load_lb, interval):
    routes = get_routes(origin, destination); weather_outage = False
    for route in routes:
        speed = route["distance_miles"] / max(route["duration_minutes"]/60, .01); cps = build_checkpoints(route["geometry"], route["distance_miles"], interval)
        try: cps, start, end = weather_for_checkpoints(cps, depart, speed)
        except ProviderError:
            weather_outage = True; start = end = None
            for cp in cps: cp["weather"] = {"available":False, "source":"forecast", "reason":"Weather provider is temporarily unavailable."}; cp["estimated_arrival"] = (depart+timedelta(hours=cp["distance_miles"]/max(speed,1))).isoformat()
        for cp in cps:
            w = cp["weather"]
            if w.get("available"): risk, components = checkpoint_risk(w["wind_mph"], w["rain_inph"], w["snow_inph"], load_lb); cp["components"] = {k:risk_name(v) for k,v in components.items()}; cp["risk_value"] = int(risk); cp["risk"] = risk_name(risk)
            else: cp["components"] = {}; cp["risk_value"] = -1; cp["risk"] = "unavailable"; cp["data_unavailable"] = True
            cp["load_lb"] = load_lb
        route["checkpoints"] = cps; route["coverage"] = {"start":start, "end":end, "source":"Open-Meteo forecast"}; summarize(route)
    feasible = [r for r in routes if not r["has_no_travel"]]; ranked = sorted(routes, key=lambda r:(1 if feasible and r["has_no_travel"] else 0, r["risk_summary"]["severe"], r["risk_summary"]["high"], r["average_risk"] if r["average_risk"] is not None else 99, r["duration_minutes"], r["id"]));
    for i, route in enumerate(ranked, 1): route["rank"] = i; route["recommendation"] = "recommended" if feasible and i == 1 and route["weather_available"] and not route["has_no_travel"] else ("unsafe" if route["has_no_travel"] else "alternative")
    rec = next((r for r in ranked if r["weather_available"] and not r["has_no_travel"]), None); explanation = f"{rec['id']} leads on severe miles ({rec['risk_summary']['severe']:.1f}), high miles ({rec['risk_summary']['high']:.1f}), average risk ({rec['average_risk']:.2f}), then travel time." if rec else "Routes are available, but a weather-based recommendation is unavailable until forecast data is available."
    partial = weather_outage or any(not r["weather_available"] for r in routes)
    return {"routes":ranked, "recommended_route_id":rec["id"] if rec else None, "recommendation":{"route_id":rec["id"] if rec else None, "criteria":["fewest severe miles","fewest high miles","lowest average risk","shortest travel time"], "explanation":explanation}, "forecast_hours":48, "route_count":len(routes), "partial":partial, "weather_status":"unavailable" if weather_outage else ("partial" if partial else "available"), "weather_message":"Route geometry is available, but live forecast data is unavailable; weather risk and recommendations are incomplete." if weather_outage else None}
