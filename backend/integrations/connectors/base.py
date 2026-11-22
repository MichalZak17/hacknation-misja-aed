"""The connector contract. A connector knows one source's format: `fetch()` returns the raw bytes exactly as
published, `parse()` turns them into ParsedRecords in the Device vocabulary (devices/schema.py) through `record()`.
Validation, diffing, storage, merging and logging are the sync engine's job (integrations/engine.py), identical for
every source.

Merge priority and sync interval are declared here, per connector class, and nowhere else: `Integration.save()` and
`manage.py seed_integrations` (run on every deploy) copy them onto the row. Changing them means changing code and
redeploying.
"""

import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import httpx
from django.conf import settings

from .common import ConnectorError, clean, compact, is_opening_hours, to_float, with_floor

__all__ = ["Connector", "ConnectorError", "ParsedRecord"]


@dataclass
class ParsedRecord:
    source_record_id: str
    lat: float | None
    lon: float | None
    data: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    # Stable IDs this record states for other sources' records, e.g. {"warszawa-19115": "622"}
    refs: dict[str, str] = field(default_factory=dict)


class Connector:
    key: ClassVar[str]
    label: ClassVar[str]
    format: ClassVar[str] = "json"
    accepts_upload: ClassVar[bool] = False
    # Higher wins when merged sources disagree on a field: operator 90 > city 50–60 > mapped 40 > OSM 10
    priority: ClassVar[int] = 50
    sync_interval_hours: ClassVar[int] = 24
    # Whether new rows sync on a schedule; an admin can still switch it per integration
    periodic: ClassVar[bool] = True
    # Fields for the Integration row `manage.py seed_integrations` creates (slug, name, source_url, licence, config)
    default_integration: ClassVar[dict | None] = None
    default_config: ClassVar[dict] = {}
    # Public page of one record at its source, `{id}` = source_record_id; the JSON-LD export links it as `sameAs`
    record_url_template: ClassVar[str | None] = None

    @classmethod
    def record_url(cls, source_record_id: str) -> str | None:
        return cls.record_url_template.format(id=source_record_id) if cls.record_url_template else None

    @classmethod
    def fixture_path(cls) -> Path | None:
        """The saved copy of the real feed in the connector's own folder (`fixtures/`, one file), which the tests parse
        instead of downloading. A connector shipped as a pip package keeps it next to its module the same way."""
        folder = Path(sys.modules[cls.__module__].__file__).parent / "fixtures"
        files = sorted(p for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []
        return files[0] if files else None

    def __init__(self, integration):
        self.integration = integration
        self.config = {**self.default_config, **(integration.config or {})}

    @property
    def snapshot_extension(self) -> str:
        return self.format

    @property
    def url(self) -> str:
        return self.config.get("url") or self.integration.source_url

    def fetch(self) -> bytes:
        if not self.url:
            raise ConnectorError("No source URL configured")
        try:
            with httpx.Client(
                timeout=httpx.Timeout(120, connect=20),
                follow_redirects=True,
                headers={"User-Agent": settings.HTTP_USER_AGENT},
            ) as client:
                response = client.get(self.url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Download failed: {exc}") from exc

    def parse(self, raw: bytes) -> Iterable[ParsedRecord]:
        raise NotImplementedError

    def text_input(self, record: ParsedRecord) -> dict | None:
        """What the LLM reads for this record (integrations/enrichment), or None when there is no free text to read.
        The prompt speaks OSM tags, so the default maps the normalised fields onto them; a connector whose raw payload
        has richer text overrides this (osm_poland)."""
        data = record.data
        hours = data.get("opening_hours_raw")
        if not data.get("location_detail") and not (hours and not is_opening_hours(hours)):
            return None
        indoor = {True: "yes", False: "no"}.get(data.get("indoor"))
        tags = {
            "defibrillator:location": data.get("location_detail"),
            "opening_hours": hours,
            "level": data.get("floor"),
            "indoor": indoor,
            "access": data.get("access"),
        }
        return {k: v for k, v in tags.items() if v}

    def record(self, source_record_id, lat, lon, data: dict, raw: dict, issues=None, refs=None) -> ParsedRecord:
        """A ParsedRecord with what every source shares: the municipality's `teryt` from config, coordinates "as
        published" (`coordinate_method: source`), numeric coordinates, and no empty fields. `data` overrides both
        defaults, e.g. a TERYT the source states itself."""
        return ParsedRecord(
            clean(source_record_id) or "",
            to_float(lat),
            to_float(lon),
            data=compact(with_floor({"teryt": self.config.get("teryt"), "coordinate_method": "source", **data})),
            raw=raw,
            issues=list(issues or []),
            refs=dict(refs or {}),
        )
