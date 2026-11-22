"""The sync engine: the same pipeline for every source.

    queue_sync()  → SyncRun(queued) → Celery task → execute_run():
        lock → fetch (raw snapshot kept on disk) → parse → validate → diff → LLM extraction from free text
        → write → merge into devices → bump the cache version and rebuild exports

A historical sync is the integration's first full load; it runs once unless forced. A periodic sync runs on the
integration's own interval (dispatch_due_syncs). Both fetch the full feed — these sources publish snapshots, not
change logs — and the diff turns that into created/updated/unchanged/removed. A dry run does everything up to the
diff and writes nothing, which is how a new or changed connector is tested against the live feed.

LLM extraction (integrations/enrichment) runs between the diff and the write, outside the database transaction: only
records whose text input changed since their last extraction (new text, new prompt or model) are sent, identical
inputs share one cached answer, and a failing model leaves those records as they were, to be retried next sync.
"""

import hashlib
import json
import logging
import traceback
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from . import enrichment
from .connectors import ParsedRecord, get_connector
from .live import LiveRun, NoLive
from .models import Integration, SourceRecord, SyncRun

logger = logging.getLogger(__name__)

POLAND = (49.0, 14.07, 54.84, 24.15)  # min_lat, min_lon, max_lat, max_lon
DETAIL_LIMIT = 300
LOCK_TIMEOUT = 6 * 60 * 60  # a first national load with LLM extraction takes about an hour


class SyncRefused(Exception):
    """The sync can't start (one is already running, or a historical sync was done and `force` wasn't given)."""


def lock_key(integration: Integration) -> str:
    return f"sync-lock:{integration.slug}"


def queue_sync(
    integration: Integration, kind: str, trigger: str, dry_run=False, force=False, reextract=False
) -> SyncRun:
    if reextract and dry_run:
        raise SyncRefused("Ponowna klasyfikacja AI zapisuje wyniki, więc nie działa w trybie bez zapisu")
    if kind == SyncRun.Kind.HISTORICAL and integration.historical_completed_at and not (force or dry_run):
        raise SyncRefused(
            f"Synchronizacja historyczna {integration.slug} została już wykonana "
            f"({integration.historical_completed_at:%Y-%m-%d %H:%M}). Użyj force, aby powtórzyć."
        )
    if integration.runs.filter(status__in=[SyncRun.Status.QUEUED, SyncRun.Status.RUNNING]).exists():
        raise SyncRefused(f"Synchronizacja {integration.slug} już trwa")
    run = SyncRun.objects.create(
        integration=integration, kind=kind, trigger=trigger, dry_run=dry_run, force=force, reextract=reextract
    )

    from .tasks import run_sync_task

    transaction.on_commit(lambda: run_sync_task.delay(run.pk))
    return run


def content_hash(record: ParsedRecord, is_valid: bool) -> str:
    payload = json.dumps(
        {
            "lat": record.lat,
            "lon": record.lon,
            "data": record.data,
            "refs": record.refs,
            "valid": is_valid,
            "issues": record.issues,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def in_box(lat, lon, box) -> bool:
    return box[0] <= lat <= box[2] and box[1] <= lon <= box[3]


def validate(records: list[ParsedRecord], integration: Integration) -> list[tuple[ParsedRecord, bool]]:
    """Coordinate presence, order and range (Poland, then the municipality's bounds), and ID uniqueness. Swapped
    lat/lon is fixed and flagged; anything else that fails stays stored, marked invalid, and never reaches a device."""
    bounds = (integration.config or {}).get("bounds")
    seen_ids: set[str] = set()
    seen_points: dict[tuple, str] = {}
    out = []
    for record in records:
        valid = True
        if not record.source_record_id:
            record.source_record_id = f"no-id-{len(out) + 1}"
            record.issues.append("missing_id")
            valid = False
        if record.source_record_id in seen_ids:
            record.source_record_id = f"{record.source_record_id}#dup{len(out) + 1}"
            record.issues.append("duplicate_id")
            valid = False
        seen_ids.add(record.source_record_id)

        if record.lat is None or record.lon is None:
            record.issues.append("missing_coordinates")
            valid = False
        elif not in_box(record.lat, record.lon, POLAND):
            if in_box(record.lon, record.lat, POLAND):
                record.lat, record.lon = record.lon, record.lat
                record.issues.append("coordinates_swapped")
            else:
                record.issues.append("outside_poland")
                valid = False
        if valid and bounds and not in_box(record.lat, record.lon, bounds):
            record.issues.append("outside_municipality")
            valid = False
        if valid:
            point = (round(record.lat, 6), round(record.lon, 6))
            if point in seen_points:
                record.issues.append(f"shared_coordinates:{seen_points[point]}")
            else:
                seen_points[point] = record.source_record_id
        out.append((record, valid))
    return out


def snapshot(run: SyncRun, connector, raw: bytes) -> None:
    folder = settings.SNAPSHOT_DIR / run.integration.slug
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{timezone.now():%Y%m%dT%H%M%S}-run{run.pk}.{connector.snapshot_extension}"
    path.write_bytes(raw)
    run.snapshot_path = str(path.relative_to(settings.BASE_DIR) if path.is_relative_to(settings.BASE_DIR) else path)
    run.snapshot_sha256 = hashlib.sha256(raw).hexdigest()


@dataclass
class Diff:
    create: list
    update: list
    unchanged_ids: list
    remove_ids: list
    changes: list
    issues: list
    # LLM extraction: source_record_id → (key, text input) for records whose input changed since their last
    # extraction; `reinfer` holds unchanged records among them; `inferred` is filled in by extract_text().
    # `stated`: source_record_id → the mergeable fields the record's own data already gives (they beat the LLM).
    to_extract: dict = field(default_factory=dict)
    stated: dict = field(default_factory=dict)
    reinfer: list = field(default_factory=list)
    inferred: dict = field(default_factory=dict)


def diff(integration: Integration, validated, connector=None, reextract=False) -> Diff:
    """`reextract` sends every record with free text to the LLM again, not only those whose input changed."""
    existing = {
        r.source_record_id: r
        for r in SourceRecord.objects.filter(integration=integration).only(
            "id", "source_record_id", "content_hash", "removed_at", "data", "lat", "lon", "inferred", "inferred_key"
        )
    }
    result = Diff([], [], [], [], [], [])
    seen = set()
    llm = connector is not None and enrichment.enabled()
    for record, valid in validated:
        seen.add(record.source_record_id)
        digest = content_hash(record, valid)
        data = {**record.data, **({"refs": record.refs} if record.refs else {})}
        if record.issues:
            result.issues.append({"source_record_id": record.source_record_id, "issues": record.issues})
        current = existing.get(record.source_record_id)
        if llm and valid:
            text = connector.text_input(record)
            key = enrichment.input_key(text)
            if key != (current.inferred_key if current else "") or (reextract and key):
                # '' with a stored key means the text is gone: the old answer is cleared
                result.to_extract[record.source_record_id] = (key, text)
                result.stated[record.source_record_id] = stated_fields(data)
        if current is None:
            result.create.append((record, valid, digest, data))
            result.changes.append({"op": "create", "source_record_id": record.source_record_id})
        elif current.removed_at is not None or current.content_hash != digest:
            changed = sorted(
                {k for k in set(current.data) | set(data) if current.data.get(k) != data.get(k)}
                | ({"lat", "lon"} if (current.lat, current.lon) != (record.lat, record.lon) else set())
            )
            op = "restore" if current.removed_at else "update"
            result.update.append((current, record, valid, digest, data))
            result.changes.append({"op": op, "source_record_id": record.source_record_id, "fields": changed})
        else:
            result.unchanged_ids.append(current.pk)
            if record.source_record_id in result.to_extract:
                result.reinfer.append(current)
    for source_id, current in existing.items():
        if source_id not in seen and current.removed_at is None:
            result.remove_ids.append(current.pk)
            result.changes.append({"op": "remove", "source_record_id": source_id})
    return result


def stated_fields(data: dict) -> list[str]:
    """Mergeable fields the source itself gives, by the merge's own test of "stated" (devices/merge.py)."""
    return [
        f for f in enrichment.MERGEABLE if data.get(f) is not None and data.get(f) != "unknown" and data.get(f) != []
    ]


def extract_text(d: Diff, live: LiveRun | None = None, fresh=False) -> dict:
    """Ask the LLM (or its cache, unless `fresh`) for every record in `d.to_extract`; fills `d.inferred` with
    source_record_id → (key, inferred). Records whose call failed are left out, so they keep their previous answer.
    Every answer is reported to `live` as it comes."""
    live = live or NoLive(0)
    inputs = {key: text for key, text in d.to_extract.values() if key}
    by_key: dict[str, list[str]] = {}
    for source_id, (key, _) in d.to_extract.items():
        if key:
            by_key.setdefault(key, []).append(source_id)

    def on_result(key, output, error, ms, cached):
        first = by_key[key][0]
        live.result(
            output=output,
            error=error,
            ms=ms,
            cached=cached,
            text_input=inputs[key],
            source_record_id=first,
            records=len(by_key[key]),
            source_wins=[f for f in d.stated.get(first, []) if output and f in output],
        )

    result = enrichment.extract(
        inputs,
        on_result=on_result,
        fresh=fresh,
        on_start=lambda cached, todo: live.begin_classify(len(inputs), len(d.to_extract), todo),
    )
    for source_id, (key, _) in d.to_extract.items():
        if not key:
            d.inferred[source_id] = ("", {})
        elif key in result.by_key:
            d.inferred[source_id] = (key, result.by_key[key])
    return {
        **result.stats,
        "records": len(d.to_extract),
        "records_updated": len(d.inferred),
        **({} if isinstance(live, NoLive) else live.summary()),
    }


def write(run: SyncRun, d: Diff) -> list[int]:
    """Apply the diff; returns the SourceRecord ids the merge has to look at."""
    now = timezone.now()
    integration = run.integration
    new = [
        SourceRecord(
            integration=integration,
            source_record_id=r.source_record_id,
            lat=r.lat,
            lon=r.lon,
            is_valid=valid,
            issues=r.issues,
            data=data,
            raw=r.raw,
            content_hash=digest,
            first_seen=now,
            last_seen=now,
            last_run=run,
            **_inferred_fields(d, r.source_record_id),
        )
        for r, valid, digest, data in d.create
    ]
    created = SourceRecord.objects.bulk_create(new, batch_size=1000)
    updated = []
    for current, r, valid, digest, data in d.update:
        current.lat, current.lon, current.is_valid, current.issues = r.lat, r.lon, valid, r.issues
        current.data, current.raw, current.content_hash = data, r.raw, digest
        current.last_seen, current.removed_at, current.last_run = now, None, run
        for name, value in _inferred_fields(d, r.source_record_id).items():
            setattr(current, name, value)
        updated.append(current)
    SourceRecord.objects.bulk_update(
        updated,
        ["lat", "lon", "is_valid", "issues", "data", "raw", "content_hash", "last_seen", "removed_at", "last_run"]
        + ["inferred", "inferred_key"],
        batch_size=1000,
    )
    reinferred = []
    for current in d.reinfer:
        if current.source_record_id in d.inferred:
            current.inferred_key, current.inferred = d.inferred[current.source_record_id]
            reinferred.append(current)
    SourceRecord.objects.bulk_update(reinferred, ["inferred", "inferred_key"], batch_size=1000)
    for start in range(0, len(d.unchanged_ids), 5000):
        SourceRecord.objects.filter(pk__in=d.unchanged_ids[start : start + 5000]).update(last_seen=now, last_run=run)
    SourceRecord.objects.filter(pk__in=d.remove_ids).update(removed_at=now, last_run=run)
    return [r.pk for r in created] + [r.pk for r in updated] + d.remove_ids + [r.pk for r in reinferred]


def _inferred_fields(d: Diff, source_record_id: str) -> dict:
    if source_record_id not in d.inferred:
        return {}
    key, inferred = d.inferred[source_record_id]
    return {"inferred_key": key, "inferred": inferred}


def execute_run(run_id: int) -> SyncRun:
    run = SyncRun.objects.select_related("integration").get(pk=run_id)
    integration = run.integration
    if run.status != SyncRun.Status.QUEUED:
        return run
    if not cache.add(lock_key(integration), run.pk, timeout=LOCK_TIMEOUT):
        run.status, run.error, run.finished_at = (
            SyncRun.Status.FAILED,
            "Inna synchronizacja tego źródła trwa",
            timezone.now(),
        )
        run.save()
        return run
    live = LiveRun(run.pk)
    try:
        run.status, run.started_at = SyncRun.Status.RUNNING, timezone.now()
        run.save(update_fields=["status", "started_at"])

        live.phase("fetch")
        connector = get_connector(integration)
        raw = connector.fetch()
        snapshot(run, connector, raw)
        live.phase("validate")
        validated = validate(list(connector.parse(raw)), integration)
        live.phase("diff")
        d = diff(integration, validated, connector, reextract=run.reextract)

        run.fetched = len(validated)
        run.invalid = sum(1 for _, valid in validated if not valid)
        run.created, run.updated = len(d.create), len(d.update)
        run.unchanged, run.removed = len(d.unchanged_ids), len(d.remove_ids)
        run.details = {
            "changes": d.changes[:DETAIL_LIMIT],
            "issues": d.issues[:DETAIL_LIMIT],
            "truncated": len(d.changes) > DETAIL_LIMIT or len(d.issues) > DETAIL_LIMIT,
        }

        if d.to_extract:
            if run.dry_run:
                run.details["enrichment"] = {"records_to_extract": len(d.to_extract)}
            else:
                run.details["enrichment"] = extract_text(d, live, fresh=run.reextract)

        if not run.dry_run:
            live.phase("write")
            from devices.cache import bump_data_version
            from devices.merge import merge_records

            with transaction.atomic():
                touched = write(run, d)
                merge_stats = merge_records(touched)
            run.details["merge"] = merge_stats
            now = timezone.now()
            integration.last_success_at = now
            if run.kind == SyncRun.Kind.HISTORICAL:
                integration.historical_completed_at = now
            integration.schedule_next(now)
            integration.save(update_fields=["last_success_at", "historical_completed_at", "next_run_at", "updated_at"])
            bump_data_version()

        run.status = SyncRun.Status.SUCCESS
    except Exception as exc:  # a failed sync is logged on the run, never shown as data
        logger.exception("Sync %s failed", run)
        run.status = SyncRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
        run.details = {**(run.details or {}), "traceback": traceback.format_exc()[-4000:]}
        if not run.dry_run and run.kind == SyncRun.Kind.PERIODIC:
            integration.schedule_next()
            integration.save(update_fields=["next_run_at", "updated_at"])
    finally:
        run.finished_at = timezone.now()
        run.save()
        live.finish(run.status, run.error)
        cache.delete(lock_key(integration))

    if run.status == SyncRun.Status.SUCCESS and not run.dry_run:
        from devices.tasks import rebuild_exports

        rebuild_exports.delay()
    return run


def dispatch_due() -> list[int]:
    """Queue a periodic sync for every enabled integration whose `next_run_at` has passed."""
    queued = []
    due = Integration.objects.filter(
        enabled=True, periodic_enabled=True, historical_completed_at__isnull=False, next_run_at__lte=timezone.now()
    )
    for integration in due:
        try:
            queued.append(queue_sync(integration, SyncRun.Kind.PERIODIC, SyncRun.Trigger.SCHEDULE).pk)
        except SyncRefused:
            continue
    return queued
