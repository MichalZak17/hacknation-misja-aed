"""Admin API for integrations: list, configure, trigger syncs, inspect runs and records, upload operator files."""

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from ninja import File, Router, Schema
from ninja.files import UploadedFile
from ninja.security import django_auth
from pydantic import ConfigDict

from . import enrichment
from . import live as live_state
from .connectors import REGISTRY
from .connectors.common import validate_bounds
from .engine import SyncRefused, queue_sync
from .models import Integration, SourceRecord, SyncRun

router = Router(tags=["integrations (admin)"], auth=django_auth)


def _iso(value):
    return value.isoformat() if value else None


def run_dict(run: SyncRun, with_details=True) -> dict:
    return {
        "id": run.pk,
        "integration": run.integration.slug,
        "integration_name": run.integration.name,
        "kind": run.kind,
        "trigger": run.trigger,
        "status": run.status,
        "dry_run": run.dry_run,
        "reextract": run.reextract,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "duration_ms": run.duration_ms,
        "fetched": run.fetched,
        "created": run.created,
        "updated": run.updated,
        "unchanged": run.unchanged,
        "removed": run.removed,
        "invalid": run.invalid,
        "error": run.error,
        "snapshot_sha256": run.snapshot_sha256,
        "details": {k: v for k, v in (run.details or {}).items() if k != "traceback"} if with_details else {},
    }


def annotated():
    live = Q(records__removed_at__isnull=True)
    return Integration.objects.annotate(
        n_records=Count("records", filter=live),
        n_valid=Count("records", filter=live & Q(records__is_valid=True)),
        n_invalid=Count("records", filter=live & Q(records__is_valid=False)),
        n_removed=Count("records", filter=Q(records__removed_at__isnull=False)),
        n_devices=Count("records__device", filter=live & Q(records__is_valid=True), distinct=True),
    ).order_by(*Integration._meta.ordering)  # aggregate queries drop Meta.ordering


# How many runs the list shows per source (the health strip in the UI)
RECENT_RUNS = 12
ACTIVE = (SyncRun.Status.QUEUED, SyncRun.Status.RUNNING)


def recent_runs(integrations) -> dict[int, list[SyncRun]]:
    """The latest RECENT_RUNS runs of each integration, newest first, in one query."""
    ranked = (
        SyncRun.objects.filter(integration__in=integrations)
        .select_related("integration")
        .annotate(rank=Window(RowNumber(), partition_by=F("integration_id"), order_by=F("created_at").desc()))
        .filter(rank__lte=RECENT_RUNS)
        .order_by("integration_id", "rank")
    )
    by_integration: dict[int, list[SyncRun]] = {}
    for run in ranked:
        by_integration.setdefault(run.integration_id, []).append(run)
    return by_integration


def run_brief(run: SyncRun) -> dict:
    return {
        "id": run.pk,
        "kind": run.kind,
        "status": run.status,
        "dry_run": run.dry_run,
        "created_at": _iso(run.created_at),
        "error": run.error[:200],
    }


def integration_dict(i: Integration, runs: list[SyncRun] | None = None) -> dict:
    if runs is None:
        runs = recent_runs([i]).get(i.pk, [])
    last = runs[0] if runs else None
    connector = REGISTRY.get(i.connector)
    return {
        "slug": i.slug,
        "name": i.name,
        "connector": i.connector,
        "description": i.description,
        "publisher": i.publisher,
        "source_url": i.source_url,
        "homepage_url": i.homepage_url,
        "attribution": i.attribution,
        "format": i.format or (connector.format if connector else ""),
        "enabled": i.enabled,
        "periodic_enabled": i.periodic_enabled,
        "sync_interval_hours": i.sync_interval_hours,
        "priority": i.priority,
        "config": {k: v for k, v in i.config.items() if k != "file_path"}
        | ({"uploaded_file": i.config["file_name"]} if i.config.get("file_name") else {}),
        "accepts_upload": bool(connector and connector.accepts_upload),
        "historical_completed_at": _iso(i.historical_completed_at),
        "next_run_at": _iso(i.next_run_at),
        "last_success_at": _iso(i.last_success_at),
        "last_run": run_dict(last, with_details=False) if last else None,
        "recent_runs": [run_brief(r) for r in runs],
        # Only one sync per source runs at a time, so an active run is always among the latest ones
        "running": any(r.status in ACTIVE for r in runs),
        "records": getattr(i, "n_records", 0),
        "valid_records": getattr(i, "n_valid", 0),
        "invalid_records": getattr(i, "n_invalid", 0),
        "removed_records": getattr(i, "n_removed", 0),
        "devices": getattr(i, "n_devices", 0),
    }


class Detail(Schema):
    detail: str


class IntegrationIn(Schema):
    """Only operator integrations are created here: their format is the fixed reference schema, so they need no
    configuration. Fetched feeds are connector classes in code (integrations/connectors/), seeded by
    `manage.py seed_integrations`. Priority and interval are declared on the connector class, so they aren't accepted."""

    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str | None = None
    connector: str = "operator_file"
    description: str = ""
    publisher: str = ""
    homepage_url: str = ""
    attribution: str = ""
    config: dict = {}


class IntegrationPatch(Schema):
    """What an admin may change. Priority, interval and connector options are code: unknown fields are refused (422)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    publisher: str | None = None
    source_url: str | None = None
    homepage_url: str | None = None
    attribution: str | None = None
    enabled: bool | None = None
    periodic_enabled: bool | None = None
    config: dict | None = None


URL_FIELDS = ("source_url", "homepage_url")
is_url = URLValidator(schemes=["http", "https"])
# Connector options live in code (`default_integration`); the area is the one option an admin tunes in the UI
EDITABLE_CONFIG = {"bounds"}
# Kept by the API itself: the uploaded operator file, and what integration_dict() adds for display
SERVER_CONFIG = {"file_path", "file_name", "uploaded_file"}


def check_fields(values: dict) -> list[str]:
    """Field checks shared by create and update: what the UI shows next to the form instead of saving bad data."""
    errors = []
    if "name" in values and not (values["name"] or "").strip():
        errors.append("name: nazwa nie może być pusta")
    for field in URL_FIELDS:
        if values.get(field):
            try:
                is_url(values[field])
            except ValidationError:
                errors.append(f"{field}: podaj pełny adres http(s)://")
    if values.get("config") is not None:
        errors.extend(validate_bounds(values["config"].get("bounds")))
    return errors


def config_with_bounds(current: dict, sent: dict) -> tuple[dict, list[str]]:
    """Apply a config PATCH: only `bounds` may change. Everything else must come back as stored (the UI sends the whole
    object) or be left out; a changed connector option is refused, because it belongs in the connector's code."""
    locked = sorted(k for k in sent if k not in EDITABLE_CONFIG | SERVER_CONFIG and sent[k] != current.get(k))
    if locked:
        return current, [
            f"config: w panelu można zmienić tylko obszar (bounds); {', '.join(locked)} ustawia się w kodzie konektora"
        ]
    config = {k: v for k, v in current.items() if k not in EDITABLE_CONFIG}
    config |= {k: sent[k] for k in EDITABLE_CONFIG if sent.get(k) is not None}
    return config, []


class SyncIn(Schema):
    kind: SyncRun.Kind = SyncRun.Kind.PERIODIC
    dry_run: bool = False
    force: bool = False
    reextract: bool = False  # ask the LLM again for every record with free text, ignoring cached answers


@router.get("/integrations")
def list_integrations(request):
    integrations = list(annotated())
    runs = recent_runs(integrations)
    return [integration_dict(i, runs.get(i.pk, [])) for i in integrations]


@router.post("/integrations", response={200: dict, 400: Detail})
def create_integration(request, payload: IntegrationIn):
    connector = REGISTRY.get(payload.connector)
    # The panel creates only sources that take an uploaded file; anything fetched from a URL is a connector in code
    if not (connector and connector.accepts_upload):
        return 400, {
            "detail": "connector: w panelu dodaje się tylko źródła z wgrywanym plikiem (np. operator_file); źródła "
            "pobierane z adresu URL definiuje się w kodzie (integrations/connectors/)"
        }
    slug = slugify(payload.slug or payload.name)[:64]
    if not slug or Integration.objects.filter(slug=slug).exists():
        return 400, {"detail": f"Źródło {slug!r} już istnieje lub nazwa jest pusta"}
    values = {k: v.strip() if isinstance(v, str) else v for k, v in payload.dict().items()}
    errors = check_fields(values)
    config, config_errors = config_with_bounds({}, payload.config)
    errors += config_errors
    if errors:
        return 400, {"detail": "; ".join(errors)}
    # Priority and interval come from the connector class (Integration.save())
    integration = Integration.objects.create(
        slug=slug,
        connector=payload.connector,
        format=connector.format,
        periodic_enabled=connector.periodic,
        **{f: values[f] for f in ("name", "description", "publisher", "homepage_url", "attribution")},
        config=config,
    )
    return 200, integration_dict(annotated().get(pk=integration.pk))


@router.get("/integrations/{slug}")
def get_integration(request, slug: str):
    return integration_dict(get_object_or_404(annotated(), slug=slug))


@router.patch("/integrations/{slug}", response={200: dict, 400: Detail})
def patch_integration(request, slug: str, payload: IntegrationPatch):
    integration = get_object_or_404(Integration, slug=slug)
    changes = payload.dict(exclude_none=True)
    errors = check_fields(changes)
    connector = REGISTRY.get(integration.connector)
    clears_url = "source_url" in changes and not changes["source_url"].strip()
    if clears_url and connector and not connector.accepts_upload and not integration.config.get("url"):
        errors.append("source_url: źródło pobierane wymaga adresu danych")
    if "config" in changes:
        changes["config"], config_errors = config_with_bounds(integration.config, changes["config"])
        errors += config_errors
    if errors:
        return 400, {"detail": "; ".join(errors)}
    for field in ("name", "description", "publisher", "source_url", "homepage_url", "attribution"):
        if field in changes:
            changes[field] = changes[field].strip()
    for field, value in changes.items():
        setattr(integration, field, value)
    if "periodic_enabled" in changes and integration.historical_completed_at:
        integration.schedule_next(integration.last_success_at or timezone.now())
    integration.save()
    return 200, integration_dict(annotated().get(pk=integration.pk))


@router.post("/integrations/{slug}/sync", response={202: dict, 409: Detail})
def sync(request, slug: str, payload: SyncIn):
    integration = get_object_or_404(Integration, slug=slug)
    try:
        run = queue_sync(
            integration,
            payload.kind,
            SyncRun.Trigger.MANUAL,
            dry_run=payload.dry_run,
            force=payload.force,
            reextract=payload.reextract,
        )
    except SyncRefused as exc:
        return 409, {"detail": str(exc)}
    return 202, run_dict(run)


@router.post("/integrations/{slug}/upload", response={200: dict, 400: Detail})
def upload(request, slug: str, file: File[UploadedFile]):
    integration = get_object_or_404(Integration, slug=slug)
    connector = REGISTRY.get(integration.connector)
    if not (connector and connector.accepts_upload):
        return 400, {"detail": "To źródło nie przyjmuje plików"}
    name = file.name or "upload"
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suffix not in {"csv", "xlsx"}:
        return 400, {"detail": "Dozwolone formaty: CSV, XLSX"}
    folder = settings.UPLOAD_DIR / integration.slug
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{timezone.now():%Y%m%dT%H%M%S}.{suffix}"
    with path.open("wb") as out:
        for chunk in file.chunks():
            out.write(chunk)
    integration.config = {**integration.config, "file_path": str(path), "file_name": name}
    integration.save(update_fields=["config", "updated_at"])
    return 200, integration_dict(annotated().get(pk=integration.pk))


@router.get("/integrations/{slug}/runs")
def integration_runs(request, slug: str, limit: int = 20, offset: int = 0):
    """A page of the source's runs, newest first, without per-record details (GET /runs/{id} has them)."""
    integration = get_object_or_404(Integration, slug=slug)
    qs = integration.runs.select_related("integration").order_by("-created_at")
    items = [run_dict(r, with_details=False) for r in qs[offset : offset + min(limit, 200)]]
    return {"count": qs.count(), "items": items}


@router.get("/integrations/{slug}/records")
def integration_records(
    request,
    slug: str,
    valid: bool | None = None,
    q: str | None = None,
    removed: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    integration = get_object_or_404(Integration, slug=slug)
    qs = SourceRecord.objects.filter(integration=integration, removed_at__isnull=not removed)
    if valid is not None:
        qs = qs.filter(is_valid=valid)
    if q:
        qs = qs.filter(Q(source_record_id__icontains=q) | Q(data__icontains=q))
    qs = qs.order_by("is_valid", "source_record_id")
    items = [
        {
            "id": r.pk,
            "source_record_id": r.source_record_id,
            "lat": r.lat,
            "lon": r.lon,
            "is_valid": r.is_valid,
            "issues": r.issues,
            "data": r.data,
            "raw": r.raw,
            "inferred": r.inferred,
            "first_seen": _iso(r.first_seen),
            "last_seen": _iso(r.last_seen),
            "removed_at": _iso(r.removed_at),
            "device_id": r.device_id,
        }
        for r in qs[offset : offset + min(limit, 500)]
    ]
    return {"count": qs.count(), "items": items}


@router.get("/runs")
def runs(request, limit: int = 50):
    return [run_dict(r, with_details=False) for r in SyncRun.objects.select_related("integration")[: min(limit, 200)]]


@router.get("/runs/{run_id}")
def run_detail(request, run_id: int):
    return run_dict(get_object_or_404(SyncRun.objects.select_related("integration"), pk=run_id))


def _live_from_details(run: SyncRun) -> dict:
    """The live state rebuilt from what the run kept, for runs whose cache entry is gone (or never existed)."""
    e = (run.details or {}).get("enrichment") or {}
    samples = e.get("samples") or []
    finished = run.finished_at is not None
    phase = "done" if finished else "queued" if run.status == SyncRun.Status.QUEUED else "fetch"
    return {
        "run": run.pk,
        "phase": phase,
        "phases": {},
        "status": run.status,
        "error": run.error,
        "total": e.get("inputs", 0),
        "records": e.get("records", 0),
        "llm_calls": e.get("llm_calls", 0),
        "done": e.get("inputs", 0) - e.get("skipped", 0),
        "cache_hits": e.get("cache_hits", 0),
        "failed": e.get("failed", 0),
        "ms_total": 0,
        "elapsed": e.get("seconds", 0),
        "throughput": e.get("throughput") or [],
        "tallies": e.get("tallies")
        or {"placement": {}, "access_conditions": {}, "opening_hours": 0, "floor": 0, "seasonal": 0},
        "seq": max((s["seq"] for s in samples), default=0),
        "events": samples,
    }


@router.get("/runs/{run_id}/live")
def run_live(request, run_id: int, after: int = 0):
    """Progress of a run while it happens: pipeline phase, LLM answers after the `after` cursor, running tallies.
    Polled about once a second by the AI classification view; works for finished runs too (from the run's details)."""
    run = get_object_or_404(SyncRun.objects.select_related("integration"), pk=run_id)
    state = live_state.read(run_id) or _live_from_details(run)
    events = [e for e in state["events"] if e["seq"] > after]
    details = run.details or {}
    summary = None
    if run.finished_at:
        summary = {
            "enrichment": {
                k: v for k, v in (details.get("enrichment") or {}).items() if k not in ("samples", "throughput")
            },
            "merge": details.get("merge"),
        }
    return {
        "run": run_dict(run, with_details=False),
        "live": {k: v for k, v in state.items() if k != "events"},
        "events": events,
        "summary": summary,
    }


@router.get("/enrichment")
def enrichment_status(request):
    """The LLM's configuration and health, and how many records of each source have free text it reads."""
    problem = ""
    if enrichment.enabled():
        problem = cache.get("llm-health")
        if problem is None:
            problem = enrichment.health_problem()
            cache.set("llm-health", problem, 30)
    live = Q(records__removed_at__isnull=True, records__is_valid=True)
    sources = (
        Integration.objects.annotate(with_text=Count("records", filter=live & ~Q(records__inferred_key="")))
        .filter(enabled=True)
        .order_by("-with_text", "priority")
    )
    return {
        "enabled": enrichment.enabled(),
        "model": settings.LLM_MODEL,
        "prompt_version": enrichment.PROMPT_VERSION,
        "concurrency": settings.LLM_CONCURRENCY,
        "problem": problem,
        "sources": [{"slug": i.slug, "name": i.name, "with_text": i.with_text} for i in sources],
    }
