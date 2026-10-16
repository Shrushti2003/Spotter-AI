from django.urls import path
from .views import analyze_routes, geocode, health
urlpatterns = [path("health/", health), path("geocode/", geocode), path("routes/analyze/", analyze_routes)]

