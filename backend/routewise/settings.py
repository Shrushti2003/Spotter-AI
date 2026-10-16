import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-routewise-key")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [x for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x]
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "rest_framework", "corsheaders", "routing"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "routewise.urls"
TEMPLATES = []
WSGI_APPLICATION = "routewise.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
CORS_ALLOWED_ORIGINS = [x for x in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if x]
REST_FRAMEWORK = {"DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}

