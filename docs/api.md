# API contract

Django (django-ninja) at `http://127.0.0.1:8000/api`. The frontend (Next on `:3000`) proxies `/api/*` to it, so the
browser only ever talks to one origin. Interactive OpenAPI docs: `/api/docs`.

Timestamps are ISO 8601 with timezone, dates are `YYYY-MM-DD`, coordinates WGS84 (EPSG:4326). `null` means unknown —
never guessed.

## Auth

Session cookie (Django). Unsafe methods (POST/PATCH/DELETE) need the `X-CSRFToken` header with the value of the
`csrftoken` cookie; `GET /api/auth/csrf` sets that cookie.

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/auth/csrf` | | `{csrfToken}` and the cookie |
| POST | `/api/auth/login` | `{email, password}` | 200 `{email}` · 401 `{detail}` |
| POST | `/api/auth/logout` | | 204 |
| GET | `/api/auth/me` | | 200 `{email}` · 401 |

Endpoints marked 🔒 return 401 without a session.

## Enums

- `readiness`: `ready` · `attention` (pads, battery or inspection due within 30 days) · `expired` · `unknown` (no maintenance data)
- `access`: `public` · `limited` · `private` · `unknown`
- `operational_status`: `operational` · `out_of_service` · `missing` · `decommissioned` · `unknown`
- `coordinate_method`: `gps` · `survey` · `geocoded` · `source` · `unknown`
- `cabinet`: `alarm` · `open` · `locked` · `none` · `unknown`
- `pads_type`: `adult` · `pediatric` · `universal` · `unknown`
- `battery_status`: `ok` · `low` · `replace` · `unknown`
- SyncRun `kind`: `historical` · `periodic`; `trigger`: `seed` · `schedule` · `manual`; `status`: `queued` · `running` · `success` · `failed`
- MaintenanceEvent `kind`: `pads_replaced` · `battery_replaced` · `inspection` · `self_test` · `used_in_rescue` · `repair` · `decommissioned`
- Match `status`: `pending` · `accepted` · `rejected`
- `placement`: `inside_building` · `outside_on_building` · `freestanding_outdoor` · `vehicle` · `unknown`
- `availability.state`: `open` · `closed` · `unknown`; `availability.reason` (only when `unknown`): `none` (no opening
  hours) · `unparsed` (syntax outside the supported subset) · `uncertain` (depends on school holidays, a rule that is
  only a comment, or an open end such as `08:00+`)
- Changes feed `change`: `updated` · `removed` (no source lists it any more) · `merged` (a duplicate, see `merged_into`)

## Public (open data)

| Method | Path | Response |
|---|---|---|
| GET | `/api/stats` | `Stats` |
| GET | `/api/stats/regions?level=voivodeship&voivodeship=` | `Regions` — AED coverage per unit: `level` `voivodeship` (16 rows) or `municipality` (gmina, ~2,480 rows); `voivodeship` (two-digit TERYT code) keeps only units in it. Units come from the PRG boundaries and are listed even with no AED (`devices: 0`), so the gaps show; `area_km2` is the PRG area and `per_100_km2` the density. Devices are counted by `teryt`; `unlocated` counts active devices with none. Cached per data version. 400 unknown `level` or `voivodeship` |
| GET | `/api/sources` | `Source[]` |
| GET | `/api/devices?q=&readiness=&access=&source=&bbox=minLon,minLat,maxLon,maxLat&teryt=&city=&placement=&operational_status=&open_24_7=&updated_since=&limit=50&offset=0` | `{count, items: DeviceListItem[]}`. `teryt`: a prefix of 2 (voivodeship), 4 (county), 6 or 7 digits (municipality), e.g. `1465011` = Warszawa. `city`: exact, ignoring case. `open_24_7=true`: only `opening_hours` `24/7` (`false`: all others). `updated_since`: ISO 8601, devices changed after it (no offset = Polish time). `limit` ≤ 500. 400 unknown `readiness` / `access` / `placement` / `operational_status` or a malformed `teryt` |
| GET | `/api/devices/points?bbox=` | GeoJSON FeatureCollection, properties `{id, readiness, access, sources}` (compact, for the map). Prebuilt bytes per data version, gzipped when accepted; `ETag` + `Cache-Control: no-cache`, so a repeat request gets a 304 |
| GET | `/api/devices/nearest?lat=&lon=&limit=5` | `(DeviceListItem & {distance_m})[]` |
| GET | `/api/aed/nearest?lat=&lon=&access=&max_distance_m=&open_now=false&at=&demo=false` | `NearestAed` — the single nearest AED a rescuer can use (skips `is_mobile`, `placement: vehicle` and `operational_status` out_of_service / missing / decommissioned), with its `availability`. `access`: comma-separated filter. `open_now=true`: only AEDs whose opening hours cover the moment (AEDs with no or undecidable hours are skipped; the nearest 4,000 candidates are checked). `at`: ISO 8601 moment to evaluate instead of now (no offset = Polish time), e.g. "what is open at 23:00". 400 unknown `access` · 404 none within `max_distance_m` (or none open) · 422 missing or out-of-range `lat`/`lon`. `demo=true` answers with `AED-PL-DEMO`, a made-up device with every field filled (never stored or exported). Reference with a live "try it" and cURL: `/developers` |
| GET | `/api/aed/nearby?lat=&lon=&limit=5&access=&max_distance_m=&open_now=false&at=` | `{query: {lat, lon}, items: {distance_m, aed, availability, links}[]}` — the nearest usable AEDs (same skipping rules and filters as `/api/aed/nearest`), nearest first, each with the full public record (`aed`, as in `NearestAed`), availability and links. `limit` 1–20. Backs the public map at `/`. 400 unknown `access` · 422 bad `lat`/`lon`/`limit`. Not cached (every position is a different key) |
| GET | `/api/aed/{id}?at=` | `AedRecord` — one AED as the reference record (the same fields as the exports), with availability and links. A device merged into another answers **301** to `/api/aed/{merged_into}`; one no source lists any more answers **410** `{detail}`; unknown id 404. `AED-PL-DEMO` answers with the demo device. Use this, not `/api/devices/{id}`, to link to an AED from another app |
| GET | `/api/changes?since=&limit=500&offset=0` | `Changes` — devices changed after `since` (ISO 8601, required), oldest first: `updated` (with the current `aed` record), `removed` or `merged` (with `merged_into`). Keep a copy in sync: load `aeds.json` once, then poll with the previous answer's `as_of` as `since`. `limit` 1–1000; page with `offset` until `offset + items.length >= count`. 422 without `since` |
| GET | `/api/devices/{id}` | `DeviceDetail` |
| GET | `/api/schema` | `SchemaField[]` — the reference record (wzorcowy zakres danych), each field also with `description`, `format`, `required` and `allowed_values` (`{value, meaning}[]`) |
| GET | `/api/export/aeds.geojson` · `aeds.csv` · `aeds.json` | the merged dataset (active devices), with ETag, without the one-line `address` (the address is published only in parts: `street_type`, `street`, `house_number`, `postal_code`, `city`, `teryt`). The CSV has one elementary value per cell: `access_conditions` becomes one `true`/`false` column per allowed value (`access_conditions_key_holder`, …), `sources` is left out (see `aeds-sources.csv`), and every empty cell holds the declared special sign `.`. It leaves out columns no record fills yet (Standard techniczny §4: no completely empty column) and keeps the schema order of the rest; datetimes are UTC (`2026-11-20T02:00:00Z`). The CSV response links its CSVW metadata (`Link: …; rel="describedby"`). JSON and GeoJSON keep lists as lists |
| GET | `/api/export/aeds-sources.csv` | which source records each AED merges, one row per pair: `aed_id`, `source`, `source_record_id`, `source_record_url` (e.g. the OpenStreetMap object) |
| GET | `/api/export/aeds.csv-metadata.json` | W3C CSVW metadata for `aeds.csv` (`application/csvm+json`): columns in file order with Polish titles, datatypes, `null: ["."]`, `primaryKey: id` (4★ CSV per Standard techniczny §4.3) |
| GET | `/api/export/archiwum` · `/api/export/archiwum/{YYYY-MM-DD}/{file}` | daily versions: every data date's `aeds.csv`, `aeds-sources.csv`, `aeds.geojson`, `aeds.json`, `aeds.jsonld`, `wykaz-chronionych-danych.xlsx` at an address that never changes (Standard techniczny: version resources instead of overwriting them). `harvester.xml` registers the dated URLs; the stable `/api/export/…` URLs always serve the newest data |
| GET | `/api/export/notes.txt` | „Informacje o zbiorze”: how the dataset meets the portal's standards and why it departs from two recommendations (licence, API host); a TXT supplement |
| GET | `/api/export/aeds.jsonld` | the same devices as schema.org linked data (`Place` with an `@id` under `/api/devices/{id}`, `GeoCoordinates`, `PostalAddress`, `sameAs` to the OpenStreetMap object); scored 5★ by the portal's own calculator |
| GET | `/api/export/schema.xlsx` · `schema-template.xlsx` · `schema-template.csv` · `schema.txt` | the reference scope. `schema-template.xlsx` (the portal resource): one sheet „Wzorcowy zakres danych” as an Excel table (Polish headers, three fictional example rows `PRZYKLAD-…`, codes as text, document properties set). `schema.xlsx` (our download and the hackathon deliverable): the same sheet, then „Słownik pól”, „Dozwolone wartości”, „Instrukcja”. The CSV is the template sheet (UTF-8 with BOM, RFC 4180). TXT is the dictionary (the supplement: dane.gov.pl takes supplements only as doc/docx/pdf/txt/odt). `manage.py write_reference_scope <dir>` writes the deliverables |
| GET | `/api/export/wykaz-chronionych-danych.xlsx` | our list of protected data (DGA): data we hold but do not publish (form reports, full operator files, raw source downloads), one row each, sizes counted from the database. Exactly the portal's five columns (`Lp.`, `Zasób chronionych danych`, `Format danych`, `Rozmiar danych`, `Warunki ponownego wykorzystywania`), Content-Type without parameters. The second dataset in `harvester.xml` (`misja-aed-dga`, `containsProtectedData=true`); dane.gov.pl copies it into its nationwide table every night. Archived daily like the data files |
| GET | `/api/export/dataset.json` | `DatasetExport` — dane.gov.pl-shaped metadata with the portal's codes: dataset (title, notes, keywords, categories, licence, `update_frequency: "daily"`, `has_*` flags, `license_chosen` from `DATASET_LICENSE`), resources with absolute `link`, size, ETag, openness score and automatic data date, the TXT supplement, the sources, and `dga` (the protected-data list dataset and its resource). Links use `PUBLIC_BASE_URL`, else the request host |
| GET | `/api/export/harvester.xml` · `harvester.md5` | our two datasets in the dane.gov.pl harvester schema (`urn:otwarte-dane:harvester:1.13`) and its MD5: the AED dataset and the list of protected data. Register the `.xml` URL once on the portal as a data source of type XML; it re-imports metadata and resources on its schedule. Needs an `https://` `PUBLIC_BASE_URL` (the XSD rejects other resource links). `dbOrCopyrighted` licence conditions follow `DATASET_LICENSE` (default `CC BY-SA 4.0`; empty = none). A request arriving through an origin in `EXTRA_PUBLIC_BASE_URLS` gets links on that origin |

```ts
type Stats = {
  devices: number; active_devices: number;
  by_readiness: Record<Readiness, number>; by_access: Record<Access, number>;
  with_maintenance_data: number; multi_source: number; pending_matches: number;
  sources: { slug: string; name: string; records: number; valid_records: number; last_success_at: string | null }[];
  data_version: number; generated_at: string;
};
type Source = {
  slug: string; name: string; publisher: string; source_url: string; homepage_url: string;
  attribution: string; records: number; last_success_at: string | null;
};
type DeviceListItem = {
  id: string; lat: number; lon: number; name: string | null; address: string | null; city: string | null;
  access: Access; readiness: Readiness; operational_status: OperationalStatus; active: boolean;
  source_count: number; sources: string[]; verified_on: string | null;
};
type DeviceDetail = DeviceListItem & {
  serial_number, manufacturer, model, inventory_number, manufactured_on, installed_on,
  coordinate_method, coordinate_accuracy_m, postal_code, teryt, simc, building_name, location_detail, floor, indoor,
  opening_hours,                 // OSM opening_hours syntax; shown as text by frontend/src/lib/opening-hours.ts
  opening_hours_raw, cabinet, is_mobile, photo_url,
  pads_type, pads_replaced_on, pads_expiry_date, pediatric_pads_available, pediatric_mode,
  battery_installed_on, battery_expiry_date, battery_status,
  last_self_test_at, last_self_test_result, last_inspection_on, next_inspection_due, last_used_on,
  verification_method, operator_name, operator_regon, operator_contact,
  municipality: string | null;   // display name of the `teryt` municipality ("gmina wiejska Zawoja"), from PRG
  // which source each value came from; method "inferred" = LLM read it from the source's free text,
  // "geocoded" (source "prg") = teryt / city from the coordinates and the PRG boundaries
  field_sources: Record<string, { source: string; seen: string; method?: "inferred" | "geocoded" }>;
  records: { integration: string; integration_name: string; source_record_id: string; first_seen: string;
             last_seen: string; removed_at: string | null; data: Record<string, unknown> }[];
  events: MaintenanceEvent[];
  created_at: string; updated_at: string;
};
type NearestAed = {
  demo: boolean; query: { lat: number; lon: number }; distance_m: number;
  aed: Record<string, unknown>;  // every /api/schema field (as in the exports), plus municipality and updated_at
  availability: Availability;
  links: Links;
};
type AedRecord = { demo: boolean; aed: NearestAed["aed"]; availability: Availability; links: Links };
type Links = {
  self: string | null;           // /api/devices/{id}: provenance of every field (null for the demo device)
  record: string;                // /api/aed/{id}: the reference record
  map: string;                   // OpenStreetMap
  directions: string;            // Google Maps, walking; from the query point, or from the user's position on /api/aed/{id}
};
// Do the AED's opening_hours cover this moment? Evaluated in Europe/Warsaw time by devices/availability.py, the same
// rules as the public page (frontend/src/lib/opening-hours.ts): weekdays, months and dates, PH = Polish public
// holidays, spans past midnight, 24/7, off, ";" "," "||" rules. Whether the public may use the AED at all is `access`.
type Availability = {
  state: "open" | "closed" | "unknown";
  open_24_7: boolean;            // open with no end within a week
  until: string | null;          // when "open" ends (ISO datetime, +01:00/+02:00); null when open_24_7
  next_open: string | null;      // when "closed" ends, within a week
  reason: "none" | "unparsed" | "uncertain" | null;  // why "unknown"
  checked_at: string;            // the moment evaluated (now, or `at`), to the minute
};
type Regions = {
  level: "voivodeship" | "municipality"; voivodeship: string | null;
  items: {
    teryt: string;               // 2 digits (voivodeship) or 7 (municipality)
    name: string | null;         // "mazowieckie", "gmina miejska Kraków"
    devices: number;             // active AEDs
    by_access: Record<Access, number>;
    open_24_7: number; public_24_7: number;  // opening_hours 24/7; and also access public
    verified: number;            // with verified_on
    area_km2: number | null; per_100_km2: number | null;
  }[];
  unlocated: number; data_version: number; generated_at: string;
};
type Changes = {
  since: string; as_of: string;  // pass as_of as the next since
  count: number;
  items: { id: string; change: "updated" | "removed" | "merged"; merged_into: string | null; updated_at: string;
           aed: NearestAed["aed"] | null }[];  // aed only for "updated"
};
type MaintenanceEvent = { id: number; kind: string; date: string; details: string; next_due: string | null;
                          source: string; reported_by: string; created_at: string };
type SchemaField = { field: string; label: string; type: string; level: 1 | 2 | 3; example: string; note: string };
```

## Open-data API v1 (Standard API)

A versioned, read-only API that follows the Polish **Standard API** (annex 3 to Program otwierania danych 2021–2027;
rules in [task/dane-gov-pl-standards-research.md](task/dane-gov-pl-standards-research.md)). Code:
`backend/devices/api_v1.py`. The unversioned endpoints above stay as they are (the frontend uses them). Public, HTTPS
on the deployment, no key, no registration, no rate limits; GET and HEAD only. OpenAPI 3: `/api/v1/openapi.json`,
Swagger UI: `/api/v1/docs`.

| Method | Path | Response |
|---|---|---|
| GET, HEAD | `/api/v1` | entry point: links to every resource and the docs, `meta.limits: "none"` |
| GET, HEAD | `/api/v1/aeds` | collection of `aeds` (active devices of the merged dataset) |
| GET, HEAD | `/api/v1/aeds/{id}` | one AED; a duplicate merged into another answers **301** to it, one no source lists any more **410** |
| GET, HEAD | `/api/v1/sources` | collection of `sources` (id = integration slug), each with `links.aeds` to its AEDs |
| GET, HEAD | `/api/v1/version` | `{"api-version": {major, minor, patch, date-mod}}` as annex 7 shows |
| GET, HEAD | `/api/v1/errors` · `/api/v1/errors/{code}` | every `error-code` with its status and meaning (the `error-help` target) |

**Documents (JSON:API 1.0).** `data` holds resource objects `{type, id, attributes, links: {self}}`; the attributes of
an `aeds` resource are the reference record (`/api/schema`, without `id`) with the export values (datetimes in UTC `Z`),
plus `municipality` and `updated_at`. Top-level `links` has absolute `self`, `first`, `prev`, `next`, `last` (`null`
when there is none) built on `PUBLIC_BASE_URL`; `meta` has `count` (total), `page`, `limit`, `pages`, `data-version`,
`date-mod` (last successful sync) and `api-version`. `Content-Type: application/json; charset=utf-8`, never
`Content-Disposition` (so dane.gov.pl classifies it as an API). Each answer is built once per data version and query and
served from Redis with an `ETag` (`If-None-Match` → 304) and `Cache-Control: public, max-age=60`.

**Query syntax (`/api/v1/aeds`).**

- `filter[teryt]=` TERYT prefix (2 voivodeship, 4 county, 6/7 municipality) · `filter[city]=` exact, ignoring case ·
  `filter[access]=` / `filter[readiness]=` / `filter[operational_status]=` / `filter[placement]=` one or more values,
  comma-separated · `filter[source]=` integration slug(s) · `filter[updated_since]=` ISO 8601 date or moment (no offset =
  Warsaw time) · `filter[bbox]=minLon,minLat,maxLon,maxLat`. Several filters are joined with `&` (AND).
- `sort=-updated_at,id` (`-` = descending) on `id`, `lat`, `lon`, `city`, `teryt`, `postal_code`, `building_name`,
  `access`, `readiness`, `operational_status`, `placement`, `verified_on`, `last_inspection_on`, `updated_at`. Default
  `id`; `id` is always the last tie-breaker.
- `fields=city,lat,lon` (sparse fieldset; also on `/aeds/{id}`). `fields[aeds]=` is accepted as well.
- `page=1&limit=50` (annex 4; `limit` 1–500). `page[number]` / `page[size]` are accepted as well. A page past the last
  one answers 200 with empty `data`.

Example: `/api/v1/aeds?filter[teryt]=12&filter[access]=public&sort=-updated_at&fields=city,lat,lon&page=2&limit=100`.

**Errors** (annex 8), for every 4xx/5xx under `/api/v1`, including unknown paths (404) and other methods (405, with
`Allow`):

```json
{"errors": [{"error-result": "Nieznany filtr", "error-reason": "Nie można filtrować po „colour”.",
  "error-solution": "Dostępne filtry: teryt, city, …", "error-code": 40002,
  "error-help": "https://misja-aed.hackstorm.eu/api/v1/errors/40002", "status": "400"}]}
```

Codes: 40001 unknown query parameter · 40002 unknown filter · 40003 bad filter value · 40004 unsupported sort ·
40005 unknown field · 40006 bad `page`/`limit` · 40007 malformed parameter · 40401 no such resource (also a trailing
slash) · 40402 no such AED · 40403 no such error code · 40501 method not allowed · 41001 AED no longer listed ·
42901 too many requests (not emitted today: there are no limits) · 50001 server error. Messages are in Polish.

**Semantic context (§6.4).** Every `/api/v1` response sends `Link: <…/api/v1/context>;
rel="http://www.w3.org/ns/json-ld#context"`: the context maps attributes to schema.org where a term matches
(`lat` → `schema:latitude`, `opening_hours` → `schema:openingHours`, …) and to the field dictionary otherwise.

**Deviations from the Standard API, and why.**

- **No `api.` subdomain (§4.1).** The API is served at `https://misja-aed.hackstorm.eu/api/v1`, on the same origin as
  the app. The deployment has one public host: TLS ends at a Caddy proxy on another machine that we cannot configure,
  and a second name would need a DNS record, a Caddy site block and a Dokku domain. Same origin also needs no CORS for
  our own pages. Moving to `api.<domain>/v1` needs no code change (links follow `PUBLIC_BASE_URL`).
- **No `dev.` portal (§4.2, optional).** The `/api/v1` entry point, Swagger UI at `/api/v1/docs` and this file carry
  the usage information; there are no limits and no keys to describe.
- **No per-response metadata set of annex 5** beyond `date-mod`, `data-version` and `api-version` in `meta`; the full
  dataset metadata is `/api/export/dataset.json`.
- **JSON only**, no XML variant (optional), and no version selection by `v=`, `api-version` header or `Accept`
  (optional; the path is the mandatory way).
- `/api/v1` (the entry point) also answers with a trailing slash; other paths do not (404 explains it).

## Admin 🔒

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/integrations` | | `Integration[]` |
| POST | `/api/integrations` | `{name, slug?, connector: "operator_file", description?, publisher?, homepage_url?, attribution?, config?: {bounds?}}` (other connectors → 400: fetched feeds are defined in code; unknown fields such as `priority` → 422) | `Integration` · 400 `{detail}` (field problems, `; `-separated) |
| GET | `/api/integrations/{slug}` | | `Integration` |
| PATCH | `/api/integrations/{slug}` | `{name?, description?, publisher?, source_url?, homepage_url?, attribution?, enabled?, periodic_enabled?, config?}` (`config`: only `bounds` may change; send the stored config back with new or no `bounds`. A changed connector option → 400. `priority`, `sync_interval_hours` and other unknown fields → 422: they are declared on the connector class) | `Integration` · 400 `{detail}` |
| POST | `/api/integrations/{slug}/sync` | `{kind, dry_run?: false, force?: false, reextract?: false}` (`reextract`: ask the LLM again for every record with free text, ignoring cached answers; not with `dry_run`) | 202 `SyncRun` (queued) · 409 `{detail}` (already running, historical already done without `force`, or `reextract` with `dry_run`) |
| POST | `/api/integrations/{slug}/upload` | multipart `file` (CSV/XLSX in the reference schema) | `Integration` — then call `/sync` |
| GET | `/api/integrations/{slug}/runs?limit=20` | | `SyncRun[]` |
| GET | `/api/integrations/{slug}/records?valid=&q=&limit=50&offset=0` | | `{count, items: SourceRecord[]}` |
| GET | `/api/runs?limit=50` | | `SyncRun[]` (all integrations, newest first) |
| GET | `/api/runs/{id}` | | `SyncRun` |
| GET | `/api/runs/{id}/live?after=0` | | `RunLive`: pipeline phase, LLM answers with `seq > after`, running tallies. Live while the run works (Redis, 24 h), rebuilt from `details.enrichment` afterwards. Polled about once a second by `/ai` |
| GET | `/api/enrichment` | | `{enabled, model, prompt_version, concurrency, problem, sources: {slug, name, with_text}[]}` (`problem` is `""` when the model server serves `model`; checked at most every 30 s) |
| GET | `/api/matches?status=pending&limit=50&offset=0` | | `{count, items: Match[]}` |
| POST | `/api/matches/{id}/accept` | | `Match` (device_b merged into device_a) |
| POST | `/api/matches/{id}/reject` | | `Match` |
| POST | `/api/devices/{id}/events` | `{kind, date, details?, next_due?}` | `MaintenanceEvent` |

```ts
type Integration = {
  slug: string; name: string; connector: string; description: string; publisher: string;
  source_url: string; homepage_url: string; attribution: string; format: string;
  enabled: boolean; periodic_enabled: boolean; sync_interval_hours: number; priority: number;
  config: Record<string, unknown>; accepts_upload: boolean;
  historical_completed_at: string | null; next_run_at: string | null; last_success_at: string | null;
  last_run: SyncRun | null; running: boolean;
  records: number; valid_records: number; invalid_records: number; removed_records: number; devices: number;
};
type SyncRun = {
  id: number; integration: string; integration_name: string; kind: string; trigger: string; status: string;
  dry_run: boolean; reextract: boolean; created_at: string; started_at: string | null; finished_at: string | null; duration_ms: number | null;
  fetched: number; created: number; updated: number; unchanged: number; removed: number; invalid: number;
  error: string; snapshot_sha256: string;
  details: { changes?: { op: "create" | "update" | "remove" | "restore"; source_record_id: string; fields?: string[] }[];
             issues?: { source_record_id: string; issues: string[] }[]; truncated?: boolean;
             enrichment?: { model: string; prompt_version: string; inputs: number; cache_hits: number;
                            llm_calls: number; failed: number; skipped: number; problem: string; seconds: number;
                            fresh: boolean; records: number; records_updated: number;
                            tallies?: Tallies; throughput?: [number, number][]; samples?: LiveEvent[] };
             merge?: Record<string, number> };
};
type RunLive = {
  run: SyncRun;  // without details
  live: { phase: "queued" | "fetch" | "validate" | "diff" | "classify" | "write" | "done";
          phases: Record<string, string>;  // phase → ISO start time
          status: string; error: string;
          total: number;      // distinct text inputs (identical texts share one answer)
          records: number;    // source records behind them
          llm_calls: number; done: number; cache_hits: number; failed: number;
          ms_total: number; elapsed: number; throughput: [number, number][]; tallies: Tallies; seq: number };
  events: LiveEvent[];
  summary: { enrichment: object; merge: object | null } | null;  // once the run has finished
};
type LiveEvent = {
  seq: number; kind: "ok" | "failed" | "cache"; source_record_id: string; records: number;
  input: Record<string, string>;   // what the model read
  output: Record<string, unknown>; // cleaned answer in Device vocabulary (placement, floor, opening_hours, …)
  error: string; ms: number;
  source_wins: string[];           // answered fields the record's own data already states (the source wins)
};
type Tallies = { placement: Record<string, number>; access_conditions: Record<string, number>;
                 opening_hours: number; floor: number; seasonal: number };
type SourceRecord = {
  id: number; source_record_id: string; lat: number | null; lon: number | null; is_valid: boolean; issues: string[];
  data: Record<string, unknown>; raw: Record<string, unknown>;
  first_seen: string; last_seen: string; removed_at: string | null; device_id: string | null;
};
type Match = { id: number; distance_m: number; status: string; reason: string; created_at: string;
               device_a: DeviceListItem; device_b: DeviceListItem };
```
