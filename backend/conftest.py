from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.test import Client

# Each integration keeps a saved copy of its real feed in integrations/connectors/<integration>/fixtures/
CONNECTORS = Path(__file__).parent / "integrations" / "connectors"


@pytest.fixture(autouse=True)
def _isolated(settings, tmp_path):
    """Tests use an in-memory cache, eager Celery and a temporary var/ — no Redis or worker needed."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.SNAPSHOT_DIR = tmp_path / "snapshots"
    settings.UPLOAD_DIR = tmp_path / "uploads"
    settings.EXPORT_DIR = tmp_path / "exports"
    from django.core.cache import cache

    from config.celery import app

    cache.clear()
    app.conf.task_always_eager = True
    yield
    cache.clear()


@pytest.fixture
def fixture_bytes():
    def read(name):
        matches = list(CONNECTORS.glob(f"*/fixtures/{name}"))
        assert len(matches) == 1, f"fixture {name!r}: expected one file, found {matches}"
        return matches[0].read_bytes()

    return read


@pytest.fixture
def parse_feed():
    """Parse raw bytes with a connector and its default config, without the database: (records, integration)."""
    from integrations.connectors import REGISTRY

    def parse(key, raw, config=None):
        defaults = REGISTRY[key].default_integration or {}
        config = config if config is not None else defaults.get("config", {})
        integration = SimpleNamespace(config=config, source_url="")
        return list(REGISTRY[key](integration).parse(raw)), integration

    return parse


@pytest.fixture
def admin_client(settings):
    call_command("ensure_admin")
    client = Client(enforce_csrf_checks=True)
    token = client.get("/api/auth/csrf").json()["csrfToken"]
    response = client.post(
        "/api/auth/login",
        {"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    # Django rotates the CSRF token at login: use the new cookie, as the frontend does
    client.token = client.cookies["csrftoken"].value
    return client
