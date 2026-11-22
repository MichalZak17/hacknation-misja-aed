"""Structured facts from free text, by a local LLM (vLLM, OpenAI-compatible API).

Sources describe where an AED hangs and how to get it in prose ("w portierni, klucz u sołtysa", "Samochód
ratowniczo-gaśniczy", "Dostępny pon-pt 7:30-15:30"). For every record that has free text, the sync engine asks the model
for a fixed set of fields (prompt.py), cleans the answer, and stores it on the SourceRecord as `inferred`. The merge uses
an inferred value only when no source states that field (devices/merge.py), and records `method: "inferred"` in the
device's `field_sources`.

Cost control: the input is the record's text tags only, so identical texts share one answer; answers are cached in
TextExtraction by sha256(prompt version, model, input); the engine sends only records whose key changed. A failed or
disabled model never fails a sync: those records keep their previous `inferred` and are retried next time.
"""

import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import httpx
from django.conf import settings

from ..connectors.common import is_opening_hours
from .prompt import ACCESS_CONDITIONS, ENCLOSURES, OUTPUT_SCHEMA, PLACEMENTS, PROMPT_VERSION, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Fields the merge may fill from `inferred` (Device vocabulary). The rest of `inferred` (enclosure, device_count,
# position_hint, placement detail) is shown with the record but not merged.
MERGEABLE = ("placement", "is_mobile", "indoor", "floor", "opening_hours", "access_conditions", "seasonal")


def enabled() -> bool:
    return bool(settings.LLM_ENABLED and settings.LLM_BASE_URL)


def input_key(text_input: dict | None) -> str:
    """Cache key for one input; '' when there is nothing to extract (no free text) or the LLM is off."""
    if not text_input or not enabled():
        return ""
    payload = json.dumps([PROMPT_VERSION, settings.LLM_MODEL, text_input], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def clean_output(out: dict) -> dict:
    """Validate the model's answer and map it onto Device fields. Anything out of range is dropped, never guessed."""
    placement = out.get("placement") if out.get("placement") in PLACEMENTS else "unknown"
    floor = out.get("floor")
    floor = floor if isinstance(floor, int) and not isinstance(floor, bool) and -5 <= floor <= 100 else None
    hours = out.get("opening_hours")
    hours = hours.strip() if isinstance(hours, str) and is_opening_hours(hours) else None
    conditions = [c for c in dict.fromkeys(out.get("access_conditions") or []) if c in ACCESS_CONDITIONS]
    count = out.get("device_count")
    count = count if isinstance(count, int) and not isinstance(count, bool) and 2 <= count <= 50 else None
    enclosure = out.get("enclosure") if out.get("enclosure") in ENCLOSURES else "unknown"
    hint = out.get("position_hint")
    hint = hint.strip()[:200] if isinstance(hint, str) and hint.strip() else None
    inferred = {
        "placement": None if placement == "unknown" else placement,
        "is_mobile": True if placement == "vehicle" else None,
        "indoor": {"inside_building": True, "outside_on_building": False, "freestanding_outdoor": False}.get(placement),
        "floor": None if floor is None else str(floor),
        "opening_hours": hours,
        "access_conditions": conditions or None,
        "seasonal": True if out.get("seasonal") is True else None,
        "device_count": count,
        "enclosure": None if enclosure == "unknown" else enclosure,
        "position_hint": hint,
    }
    return {k: v for k, v in inferred.items() if v is not None}


def call_model(client: httpx.Client, text_input: dict) -> dict:
    body = {
        "model": settings.LLM_MODEL,
        "temperature": 0,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(text_input, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "aed", "schema": OUTPUT_SCHEMA, "strict": True},
        },
        "chat_template_kwargs": {"enable_thinking": False},
    }
    response = client.post(f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions", json=body)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


@dataclass
class Result:
    by_key: dict[str, dict] = field(default_factory=dict)  # key → cleaned `inferred`
    stats: dict = field(default_factory=dict)


def extract(inputs: dict[str, dict], progress=None, on_result=None, fresh=False, on_start=None) -> Result:
    """Answers for every key in `inputs` (key → text input): from the cache, else from the model. Keys whose call
    failed are missing from the result.

    `fresh` ignores the cache and asks the model again (an admin's re-classification). `on_start(cached, todo)` is
    called once the cache was read, and `on_result(key, output, error, ms, cached)` for every answer, from this thread,
    with the cleaned output (None when the call failed): the live view (integrations/live.py) listens to both."""
    from ..models import TextExtraction

    started = time.monotonic()
    result = Result()
    if not fresh:
        cached = TextExtraction.objects.filter(key__in=list(inputs), output__isnull=False).values_list("key", "output")
        for key, output in cached.iterator(chunk_size=2000):
            result.by_key[key] = clean_output(output)
    todo = [k for k in inputs if k not in result.by_key]
    hits = len(result.by_key)
    failed = skipped = 0
    problem = ""
    if todo:
        problem = health_problem()
        if problem:
            logger.warning("LLM extraction skipped: %s", problem)
            skipped, todo = len(todo), []
    if on_start:
        on_start(len(result.by_key), len(todo))
    if on_result:
        for key, inferred in list(result.by_key.items()):
            on_result(key, inferred, None, 0, True)
    if todo:
        logger.info(
            "LLM extraction: %d cached, %d to extract with %s", len(result.by_key), len(todo), settings.LLM_MODEL
        )
        pending = []
        stop = threading.Event()

        def one(key):
            if stop.is_set():
                return key, None, None, 0
            t = time.monotonic()
            last_error = None
            for _ in range(2):  # one retry: a rare generation loops until max_tokens and returns broken JSON
                try:
                    return key, call_model(client, inputs[key]), None, int((time.monotonic() - t) * 1000)
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"[:500]
            return key, None, last_error, int((time.monotonic() - t) * 1000)

        def flush():
            TextExtraction.objects.bulk_create(
                pending,
                update_conflicts=True,
                unique_fields=["key"],
                update_fields=["output", "error", "duration_ms", "created_at"],
            )
            pending.clear()

        with (
            httpx.Client(timeout=httpx.Timeout(settings.LLM_TIMEOUT, connect=10)) as client,
            ThreadPoolExecutor(settings.LLM_CONCURRENCY) as pool,
        ):
            futures = [pool.submit(one, key) for key in todo]
            for done, future in enumerate(as_completed(futures), 1):
                key, output, error, ms = future.result()
                if output is None and error is None:  # not attempted: the run was stopped
                    skipped += 1
                    continue
                pending.append(
                    TextExtraction(
                        key=key,
                        model=settings.LLM_MODEL,
                        prompt_version=PROMPT_VERSION,
                        input=inputs[key],
                        output=output,
                        error=error or "",
                        duration_ms=ms,
                    )
                )
                if output is None:
                    failed += 1
                    if failed >= 50 and failed > done / 2 and not stop.is_set():
                        problem = f"stopped after {failed} of {done} calls failed (last: {error})"
                        logger.warning("LLM extraction %s", problem)
                        stop.set()
                else:
                    result.by_key[key] = clean_output(output)
                if on_result:
                    on_result(key, result.by_key.get(key) if output is not None else None, error, ms, False)
                if len(pending) >= 200:
                    flush()  # keep finished work if the sync dies half-way
                if done % 500 == 0 or done == len(todo):
                    rate = done / max(time.monotonic() - started, 1e-6)
                    logger.info("LLM extraction: %d/%d (%.1f/s, %d failed)", done, len(todo), rate, failed)
                    if progress:
                        progress(done, len(todo))
        if pending:
            flush()
    result.stats = {
        "model": settings.LLM_MODEL,
        "prompt_version": PROMPT_VERSION,
        "inputs": len(inputs),
        "cache_hits": hits,
        "fresh": fresh,
        "llm_calls": len(todo),
        "failed": failed,
        "skipped": skipped,
        "problem": problem,
        "seconds": round(time.monotonic() - started, 1),
    }
    return result


def health_problem() -> str:
    """'' when the model server answers and serves LLM_MODEL, else why not. Checked once per sync, so a server that is
    down costs one short request instead of a timeout per record."""
    try:
        response = httpx.get(f"{settings.LLM_BASE_URL.rstrip('/')}/models", timeout=10)
        response.raise_for_status()
        served = {m.get("id") for m in response.json().get("data", [])}
    except (httpx.HTTPError, ValueError) as exc:
        return f"model server unreachable: {type(exc).__name__}: {exc}"[:300]
    if settings.LLM_MODEL not in served:
        return f"model {settings.LLM_MODEL!r} not served (serves: {', '.join(sorted(map(str, served)))})"[:300]
    return ""
