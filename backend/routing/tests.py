from datetime import datetime, timezone
from unittest.mock import Mock, patch
from django.test import Client, SimpleTestCase
from . import services
from .risk import Risk, checkpoint_risk, rain_risk, snow_risk, wind_risk
from .services import build_checkpoints, cumulative_distances
class RiskTests(SimpleTestCase):
    def test_wind_boundaries(self):
        self.assertEqual(wind_risk(24.99),Risk.LOW); self.assertEqual(wind_risk(25),Risk.MODERATE); self.assertEqual(wind_risk(35),Risk.HIGH); self.assertEqual(wind_risk(45),Risk.SEVERE); self.assertEqual(wind_risk(55),Risk.NO_TRAVEL)
    def test_rain_and_snow_boundaries(self):
        self.assertEqual(rain_risk(.099),Risk.LOW); self.assertEqual(rain_risk(.1),Risk.MODERATE); self.assertEqual(rain_risk(.25),Risk.MODERATE); self.assertEqual(rain_risk(.251),Risk.HIGH); self.assertEqual(rain_risk(.5),Risk.HIGH); self.assertEqual(rain_risk(.501),Risk.SEVERE); self.assertEqual(rain_risk(1),Risk.SEVERE); self.assertEqual(rain_risk(1.001),Risk.NO_TRAVEL)
        self.assertEqual(snow_risk(.499),Risk.LOW); self.assertEqual(snow_risk(.5),Risk.MODERATE); self.assertEqual(snow_risk(1),Risk.MODERATE); self.assertEqual(snow_risk(1.001),Risk.HIGH); self.assertEqual(snow_risk(2),Risk.HIGH); self.assertEqual(snow_risk(2.001),Risk.SEVERE); self.assertEqual(snow_risk(3),Risk.SEVERE); self.assertEqual(snow_risk(3.001),Risk.NO_TRAVEL)
    def test_load_rules_strict(self):
        self.assertNotEqual(checkpoint_risk(50,0,0,30000)[0],Risk.NO_TRAVEL); self.assertEqual(checkpoint_risk(50,0,0,30001)[0],Risk.NO_TRAVEL); self.assertEqual(checkpoint_risk(40,0,0,40001)[0],Risk.SEVERE); self.assertEqual(checkpoint_risk(55,0,0,1)[0],Risk.NO_TRAVEL)
    def test_geometry(self):
        coords=[[0,0],[1,0],[2,0]]; self.assertAlmostEqual(cumulative_distances(coords)[-1],138.2,delta=2); self.assertEqual(len(build_checkpoints(coords,138,50)),4)


class ProviderAndApiTests(SimpleTestCase):
    def setUp(self):
        services._CACHE.clear()
        self.client = Client()
        self.origin = {"display_name": "Origin", "lat": 40, "lon": -100}
        self.destination = {"display_name": "Destination", "lat": 40, "lon": -99}
        self.payload = {"origin": self.origin, "destination": self.destination, "departure": "2026-01-01T00:00:00Z", "load_lb": 3600, "interval_miles": 25}
        self.route_data = {"code": "Ok", "routes": [{"distance": 160934.4, "duration": 7200, "geometry": {"coordinates": [[-100, 40], [-99, 40]]}}]}
        times = [f"2026-01-01T0{i}:00Z" for i in range(10)]
        self.weather_data = [{"hourly": {"time": times, "wind_speed_10m": [10] * 10, "precipitation": [0] * 10, "rain": [0] * 10, "snowfall": [0] * 10}}]

    def response(self, data, status=200):
        return Mock(status_code=status, headers={}, json=Mock(return_value=data))

    def test_success_with_mocked_routing_and_weather(self):
        with patch.object(services._SESSION, "get", side_effect=[self.response(self.route_data), self.response(self.weather_data)]):
            response = self.client.post("/api/routes/analyze/", data=self.payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["weather_status"], "available")
        self.assertEqual(result["routes"][0]["checkpoints"][0]["risk"], "low")

    def test_distinct_osrm_alternatives_are_preserved(self):
        alternatives = {"code": "Ok", "routes": [
            self.route_data["routes"][0],
            {"distance": 180000, "duration": 8000, "geometry": {"coordinates": [[-100, 40], [-99.5, 40.2], [-99, 40]]}},
        ]}
        with patch.object(services._SESSION, "get", return_value=self.response(alternatives)):
            routes = services.get_routes(self.origin, self.destination)
        self.assertEqual([route["id"] for route in routes], ["route-1", "route-2"])
        self.assertNotEqual(routes[0]["geometry"], routes[1]["geometry"])

    def test_weather_timeout_returns_route_only_partial_result(self):
        with patch.object(services._SESSION, "get", side_effect=[self.response(self.route_data), services.requests.Timeout(), services.requests.Timeout(), services.requests.Timeout()]):
            with patch.object(services.time, "sleep"):
                response = self.client.post("/api/routes/analyze/", data=self.payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["partial"])
        self.assertIsNone(result["recommended_route_id"])
        self.assertEqual(result["routes"][0]["checkpoints"][0]["risk"], "unavailable")
        self.assertIsNone(result["routes"][0]["risk_score"])

    def test_retryable_429_and_5xx_are_bounded(self):
        with patch.object(services._SESSION, "get", side_effect=[self.response({}, 429), self.response({}, 503), self.response({}, 503)]):
            with patch.object(services.time, "sleep") as sleeper:
                with self.assertRaises(services.ProviderError) as error:
                    services._request_json("Weather", "https://example.test", {})
        self.assertEqual(error.exception.code, "upstream_unavailable")
        self.assertEqual(sleeper.call_count, 2)

    def test_malformed_upstream_json_is_safe_error(self):
        malformed = Mock(status_code=200, headers={}, json=Mock(side_effect=ValueError()))
        with patch.object(services._SESSION, "get", return_value=malformed):
            with self.assertRaises(services.ProviderError) as error: services._request_json("Routing", "https://example.test", {})
        self.assertEqual(error.exception.code, "invalid_upstream_json")

    def test_routing_failure_is_structured_and_not_502_timeout_text(self):
        with patch.object(services._SESSION, "get", return_value=self.response({}, 503)):
            with patch.object(services.time, "sleep"):
                response = self.client.post("/api/routes/analyze/", data=self.payload, content_type="application/json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "upstream_unavailable")
        self.assertNotIn("Traceback", response.content.decode())

    def test_invalid_input(self):
        payload = dict(self.payload, load_lb=-1)
        response = self.client.post("/api/routes/analyze/", data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_input")

