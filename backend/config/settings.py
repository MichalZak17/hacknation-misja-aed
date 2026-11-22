"""Settings, all from backend/.env (no Doppler in this project)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return env(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "integrations",
    "devices",
]

MIDDLEWARE = [
    "config.middleware.head_without_body",  # outermost: sees the final (gzipped) response
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "misja_aed"),
        "USER": env("POSTGRES_USER", "misja_aed"),
        "PASSWORD": env("POSTGRES_PASSWORD", "misja_aed"),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "5434"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

REDIS_CACHE_URL = env("REDIS_CACHE_URL", "redis://127.0.0.1:6380/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "KEY_PREFIX": "misja-aed",
        "TIMEOUT": 60 * 60 * 24,
    }
}

AUTH_PASSWORD_VALIDATORS = []  # the one admin login comes from .env
LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Raw source snapshots, operator uploads and prebuilt exports
VAR_DIR = BASE_DIR / "var"
SNAPSHOT_DIR = VAR_DIR / "snapshots"
UPLOAD_DIR = VAR_DIR / "uploads"
EXPORT_DIR = VAR_DIR / "exports"
# Public origin the exports are served from (e.g. https://aed.example.pl), for the absolute resource links in
# /api/export/dataset.json. Defaults to the frontend origin (the first CSRF trusted origin), since Next proxies /api
# and the request host Django sees is its own; empty everywhere = taken from the request.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", CSRF_TRUSTED_ORIGINS[0] if CSRF_TRUSTED_ORIGINS else "").rstrip("/")
# Other origins the same site is reachable at (e.g. a test address without the public site's login gate). A request
# arriving through one of them gets export links on that origin instead of PUBLIC_BASE_URL.
EXTRA_PUBLIC_BASE_URLS = [url.rstrip("/") for url in env_list("EXTRA_PUBLIC_BASE_URLS")]
# Licence of the dataset on dane.gov.pl: "CC0 1.0", "CC BY 4.0" or "CC BY-SA 4.0" (the portal has no ODbL). CC BY-SA
# 4.0 is the closest to the ODbL of the OpenStreetMap part. Empty = none chosen; the harvester XML then omits the
# licence conditions. See docs/task/dane-gov-pl-source-code.md.
DATASET_LICENSE = env("DATASET_LICENSE", "CC BY-SA 4.0")
# "Lokalizacja danych" for each resource in harvester.xml (TERYT codes, max 20): the 16 voivodeships for a nationwide
# dataset. dane.gov.pl checks the codes against its geocoder (Pelias); a portal copy without one fails the import, so
# HARVESTER_REGIONS=off turns them off there.
HARVESTER_REGIONS = [
    code.strip()
    for code in env("HARVESTER_REGIONS", "02,04,06,08,10,12,14,16,18,20,22,24,26,28,30,32").split(",")
    if code.strip().isdigit()
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

ADMIN_EMAIL = env("ADMIN_EMAIL", "admin@admin.com")
ADMIN_PASSWORD = env("ADMIN_PASSWORD", "admin123")

MATCH_DISTANCE_M = float(env("MATCH_DISTANCE_M", "25"))
HTTP_USER_AGENT = env("HTTP_USER_AGENT", "MisjaAED-prototype/0.1 (HackNation 2026)")
READINESS_ATTENTION_DAYS = 30

# Local LLM (vLLM, OpenAI-compatible) that reads structured facts out of source free text during syncs
# (integrations/enrichment). Off unless LLM_ENABLED is set; a missing or failing model never fails a sync.
LLM_ENABLED = env_bool("LLM_ENABLED", False)
LLM_BASE_URL = env("LLM_BASE_URL", "http://100.78.88.117:8000/v1")
LLM_MODEL = env("LLM_MODEL", "qwen")
LLM_CONCURRENCY = int(env("LLM_CONCURRENCY", "16"))
LLM_TIMEOUT = float(env("LLM_TIMEOUT", "120"))

# Celery: broker on Redis /0. Beat runs `dispatch_due_syncs` every minute, which queues each integration's periodic
# sync when its own `next_run_at` passes, so intervals live in the database, per integration.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6380/0")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-syncs": {"task": "integrations.tasks.dispatch_due_syncs", "schedule": 60.0},
    "recompute-readiness": {"task": "devices.tasks.recompute_readiness", "schedule": 60.0 * 60 * 6},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"httpx": {"level": "WARNING"}},
}
