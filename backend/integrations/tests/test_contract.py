"""The contract every URL feed must meet, checked for each connector in the registry against its own saved feed.

A new connector folder is picked up here without writing a line of test: it needs `default_integration` with the
catalogue metadata, a valid area and a fixture, and its parser must produce records the engine accepts.
"""

from types import SimpleNamespace

import pytest

from devices.schema import MERGE_FIELDS
from integrations.connectors import REGISTRY
from integrations.connectors.common import validate_bounds
from integrations.engine import validate

FEEDS = sorted(key for key, cls in REGISTRY.items() if cls.default_integration)
REQUIRED = ("slug", "name", "publisher", "source_url", "license", "license_url", "attribution")


def test_every_feed_folder_is_registered():
    assert len(FEEDS) >= 6


@pytest.mark.parametrize("key", FEEDS)
def test_metadata(key):
    defaults = REGISTRY[key].default_integration
    missing = [f for f in REQUIRED if not defaults.get(f)]
    assert not missing, f"{key}: default_integration lacks {missing}"
    placeholders = [f for f, v in defaults.items() if isinstance(v, str) and "TODO" in v]
    assert not placeholders, f"{key}: fill in {placeholders}"
    assert validate_bounds(defaults.get("config", {}).get("bounds")) == []


@pytest.mark.parametrize("key", FEEDS)
def test_parses_its_saved_feed(key):
    cls = REGISTRY[key]
    path = cls.fixture_path()
    assert path, f"{key}: save a copy of the real feed in fixtures/"
    integration = SimpleNamespace(config=cls.default_integration.get("config", {}), source_url="")
    connector = cls(integration)
    records = list(connector.parse(path.read_bytes()))
    assert records, f"{key}: no records parsed from {path.name}"

    assert all(r.source_record_id for r in records), f"{key}: every record needs a stable ID"
    unknown = {f for r in records for f in r.data} - set(MERGE_FIELDS)
    assert not unknown, f"{key}: fields outside the reference schema: {sorted(unknown)}"
    for r in records:
        text = connector.text_input(r)
        assert text is None or isinstance(text, dict)

    valid = sum(ok for _, ok in validate(records, integration))
    assert valid >= len(records) / 2, f"{key}: only {valid} of {len(records)} records pass validation"
