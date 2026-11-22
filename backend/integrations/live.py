"""Live progress of a sync run, for the admin's AI classification view (GET /api/runs/{id}/live).

A run saves itself to the database only when it starts and when it ends. While it runs, the engine reports here: the
pipeline phase, and for the LLM step every answer (input text → cleaned fields) with running tallies. Everything sits
in one cache entry per run (Redis on the server), written by the run's own thread only, so no locking is needed.
Writes are throttled; readers page through the answers with an increasing `seq` cursor. The last answers are also
kept on the run (`details.enrichment.samples`) for when the cache entry has expired.
"""

import contextlib
import time

from django.core.cache import cache
from django.utils import timezone

PHASES = ("fetch", "validate", "diff", "classify", "write", "done")
TTL = 24 * 60 * 60
MAX_EVENTS = 300  # answers kept for readers that poll late
MAX_CACHE_EVENTS = 30  # cached answers shown as cards; the rest only count
SAMPLES = 40  # answers kept on the run after it ends
FLUSH_EVERY = 0.4  # seconds
TEXT_LIMIT = 400


def key(run_id: int) -> str:
    return f"run-live:{run_id}"


def read(run_id: int) -> dict | None:
    return cache.get(key(run_id))


def _short(text_input: dict) -> dict:
    return {
        k: (v[:TEXT_LIMIT] + "…" if isinstance(v, str) and len(v) > TEXT_LIMIT else v)
        for k, v in (text_input or {}).items()
        if v not in (None, "")
    }


class LiveRun:
    def __init__(self, run_id: int):
        self.run_id = run_id
        self._last_flush = 0.0
        self._classify_started = None
        self._cache_events = 0
        self.state = {
            "run": run_id,
            "phase": "fetch",
            "phases": {},  # phase → ISO time it started
            "status": "running",
            "error": "",
            "total": 0,  # distinct inputs to classify
            "records": 0,  # records behind them
            "llm_calls": 0,
            "done": 0,
            "cache_hits": 0,
            "failed": 0,
            "ms_total": 0,
            "elapsed": 0.0,
            "throughput": [],  # [seconds since classify started, answers done]
            "tallies": {"placement": {}, "access_conditions": {}, "opening_hours": 0, "floor": 0, "seasonal": 0},
            "seq": 0,
            "events": [],
        }

    def phase(self, name: str) -> None:
        self.state["phase"] = name
        self.state["phases"][name] = timezone.now().isoformat()
        self.flush(force=True)

    def begin_classify(self, total: int, records: int, llm_calls: int) -> None:
        self._classify_started = time.monotonic()
        self.state.update(total=total, records=records, llm_calls=llm_calls)
        self.phase("classify")

    def result(
        self,
        *,
        output: dict | None,
        error: str | None,
        ms: int,
        cached: bool,
        text_input: dict,
        source_record_id: str,
        records: int,
        source_wins: list[str],
    ) -> None:
        s = self.state
        s["done"] += 1
        if cached:
            s["cache_hits"] += 1
        else:
            s["ms_total"] += ms
        if output is None:
            s["failed"] += 1
        else:
            t = s["tallies"]
            placement = output.get("placement") or "unknown"
            t["placement"][placement] = t["placement"].get(placement, 0) + 1
            for condition in output.get("access_conditions") or []:
                t["access_conditions"][condition] = t["access_conditions"].get(condition, 0) + 1
            for field in ("opening_hours", "floor", "seasonal"):
                t[field] += 1 if output.get(field) is not None else 0
        if cached:
            self._cache_events += 1
            if self._cache_events > MAX_CACHE_EVENTS:
                self.flush()
                return
        s["seq"] += 1
        s["events"].append(
            {
                "seq": s["seq"],
                "kind": "cache" if cached else "failed" if output is None else "ok",
                "source_record_id": source_record_id,
                "records": records,
                "input": _short(text_input),
                "output": output or {},
                "error": (error or "")[:200],
                "ms": ms,
                "source_wins": source_wins,
            }
        )
        del s["events"][:-MAX_EVENTS]
        self.flush()

    def finish(self, status: str, error: str = "") -> None:
        self.state.update(status=status, error=error[:500])
        self.phase("done")

    def samples(self) -> list[dict]:
        return [e for e in self.state["events"] if e["kind"] != "cache"][-SAMPLES:]

    def summary(self) -> dict:
        """What the run keeps in `details.enrichment` besides the extractor's own stats."""
        return {"tallies": self.state["tallies"], "throughput": self.state["throughput"], "samples": self.samples()}

    def flush(self, force=False) -> None:
        now = time.monotonic()
        if not force and now - self._last_flush < FLUSH_EVERY:
            return
        self._last_flush = now
        if self._classify_started is not None:
            elapsed = round(now - self._classify_started, 1)
            self.state["elapsed"] = elapsed
            points = self.state["throughput"]
            if not points or elapsed - points[-1][0] >= 1:
                points.append([elapsed, self.state["done"]])
                if len(points) > 240:  # keep every other point once long runs pile up
                    points[:] = points[::2]
        with contextlib.suppress(Exception):  # progress is a nicety: a cache outage must never fail a sync
            cache.set(key(self.run_id), self.state, TTL)


class NoLive(LiveRun):
    """Stand-in when nobody watches (tests that call engine helpers directly)."""

    def flush(self, force=False) -> None:
        pass
