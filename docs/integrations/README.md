# Integrations: how AED data reaches the platform

An **integration** is one source of AED data: a row in the `Integration` table and one row on the **Integracje** page
of the admin UI. **Code defines integrations; the UI operates them.**

## Two kinds, no webhooks

| Kind | Who moves the data | Defined | Integrations |
|---|---|---|---|
| **URL feed (pull)** | **We download** the whole file the publisher keeps at a fixed URL | In code: a folder under `backend/integrations/connectors/` | `osm-poland`, `warszawa-19115`, `przemysl`, `krosno`, `marki`, `legionowo` |
| **Operator file (upload)** | **The operator sends** a CSV/XLSX in the reference schema and **an admin uploads it** | In the UI: **Nowy dysponent** | any `operator_file` integration |

No source publishes change events, so every sync downloads a full snapshot and diffs it against the stored records.
Operators cannot push data to us: there is no webhook or inbound API (a per-integration token endpoint would be the
next step if that becomes a requirement).

## What happens on every sync

Both kinds go through the same pipeline (`backend/integrations/engine.py`):

1. **Lock**: one sync per integration at a time.
2. **Fetch** from `source_url` (one `GET`, 120 s timeout) or read the last uploaded file.
3. **Snapshot** the raw bytes to `backend/var/snapshots/<slug>/`.
4. **Parse** the source's format into the reference fields (`backend/devices/schema.py`).
5. **Validate**: coordinates present, inside Poland and inside the municipality's bounds. Swapped lat/lon is fixed and
   flagged, duplicate IDs are flagged. Invalid records are stored but never reach a device.
6. **Diff** against what is stored: *created*, *updated*, *unchanged*, *removed*.
7. **LLM extraction** of free text, where enabled ([report](../llm-extraction/report.mdx)).
8. **Write and merge**: records join devices; per field the higher `priority` wins.
9. **Publish**: the cache version is bumped and the exports are rebuilt.

A failed download is logged on the run as **Błąd** and never changes stored data.

## Triggers

| Trigger | How |
|---|---|
| Schedule | Celery beat runs `dispatch_due_syncs` every minute and queues a periodic sync for each enabled integration whose historical load is done and whose `sync_interval_hours` has passed. Off by default for operator files. |
| UI | **Synchronizacja historyczna** (first full load; a second one needs confirmation), **Synchronizuj teraz**, **Test (dry run)**: fetch, parse, validate and diff without saving |
| API | `POST /api/integrations/{slug}/sync` with `{"kind": "historical" \| "periodic", "dry_run": false, "force": false}` |
| CLI | `npm run sync -- <slug> [--historical] [--dry-run] [--force]` |

## Adding a URL feed

1. Create `backend/integrations/connectors/<slug>/` with an empty `__init__.py`, `connector.py` (fetch, parse,
   `priority`, `sync_interval_hours` if not 24, and `default_integration`: URL, licence, bounds, TERYT),
   `fixtures/<sample>` and `test_connector.py`. Copy the closest existing folder; the registry finds it by itself.
   A feed whose columns map one-to-one can subclass the `mapped` connector instead ([mapped feeds](mapped-feeds.mdx)).
   If every record has a public page at the source, set `record_url_template` (e.g. OSM's
   `https://www.openstreetmap.org/{id}`) and the JSON-LD export links it as `sameAs`. Nothing outside the folder
   names a source: the engine, merge, exports and admin UI read only what the class declares.
2. Write the source's notes in `docs/integrations/sources/<slug>.mdx`.
3. `npm run test`, then `npm run seed` (or redeploy) to create the row. Besides the folder's own test,
   `integrations/tests/test_contract.py` checks every feed by itself: catalogue metadata, a valid area, a fixture, stable
   IDs, only reference-schema fields, and at least half of the saved feed passing validation.
4. In the UI: **Test (dry run)**, then **Synchronizacja historyczna**.

The UI cannot define feeds because every real source needs code: Marki wraps CSV in CSV, Legionowo has no ID, Krosno
packs the address into one column, Warsaw needs value maps and OSM joins Warsaw's IDs.

## What the UI can change

On/off, periodic sync on/off, name, description, publisher, data URL, homepage, attribution and the area (bounds).
**Priority and interval** are class attributes: shown read-only, applied to every row by `seed_integrations` on each
start and deploy, so they change only with a redeploy. The rest of `default_integration` only seeds new rows; to change
it on an existing row, use Django admin (`/admin/`). Integrations cannot be deleted, only disabled.

## Documents

- [operator-files.mdx](operator-files.mdx): operator uploads, the only integrations created in the UI
- [mapped-feeds.mdx](mapped-feeds.mdx): plain feeds mapped column by column, in code
- Per-source notes, with an example raw record:
  [osm-poland](sources/osm-poland.mdx) ·
  [warszawa-19115](sources/warszawa-19115.mdx) ·
  [przemysl](sources/przemysl.mdx) ·
  [krosno](sources/krosno.mdx) ·
  [marki](sources/marki.mdx) ·
  [legionowo](sources/legionowo.mdx)
