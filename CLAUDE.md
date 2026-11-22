# CLAUDE.md

HackNation 2026 entry for the Ministry of Digital Affairs challenge **„Misja AED — Dane na ratunek”**: collect AED data
from scattered sources, merge it into one nationwide open dataset, and publish it on dane.gov.pl in a reference schema.

## Which system is which (read first)

"My project", "the platform", "the app", "our admin" = **Misja AED, this repository** (Django API + Next.js admin),
locally or on the Dokku deployment. The portal copy below is **mcod**, a separate system: touch it only when the user
names it (mcod, admin.mcod.local, "the dane.gov.pl instance", the harvester).

| | Where | Admin login |
|---|---|---|
| **Misja AED, local dev** | Next.js `http://localhost:3000`, Django `http://127.0.0.1:8000` (`npm run backend` / `npm run frontend`) | `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `backend/.env` (`admin@admin.com` / `admin123`) |
| **Misja AED, deployment** | Dokku apps `misja-aed` (Next.js) and `misja-aed-api` (Django + Celery worker) on hacknation-dev; public URL `https://misja-aed.hackstorm.eu` | `admin@misja-aed.hackstorm.eu` (Dokku `ADMIN_EMAIL`, recreated by `ensure_admin` on every deploy) and `admin@admin.com` (added by hand; strong password since 22.11.2026, ask the user — never write it here) |
| **mcod** (dane.gov.pl portal, test instance) | Public: `https://dane.hackstorm.eu`, `api.` / `admin.` / `cms.dane.hackstorm.eu` (Caddy on hacknation-vpn → `/etc/nginx/conf.d/dane-hackstorm.conf` → mcod-nginx). Also `*.mcod.local` over Tailscale, but logins only work on the public names (cookie domain). Docker compose project `danegovpl` in `~/dane-gov-pl` (containers `mcod-*`); config changes and backups in `~/dane-gov-pl/backup-2026-11-21-dane-hackstorm/` | `admin@mcod.local`, `pelnomocnik@mcod.local` (strong passwords, ask the user) |

## Misja AED deployment

- `~/deploy/misja-aed/deploy.sh [branch] [api|web]` deploys **committed** work only: it takes the branch from this repo,
  cherry-picks its `deploy` commit (Dockerfiles, Procfile, app.json) and force-pushes to Dokku. The predeploy step runs
  `migrate`, `seed_integrations` and `ensure_admin`. Config: `dokku config:show misja-aed-api`.
- `https://misja-aed.hackstorm.eu` is public, with no access code or login gate in front of it: Caddy on another host
  (`hacknation-vpn`, 145.239.78.161) terminates TLS and proxies over Tailscale to Dokku here. That Caddy config cannot
  be changed from hacknation-dev.
- **DNS: you have GoDaddy access for deployments.** The `hackstorm.eu` zone is on GoDaddy and you may add or change
  records for a deployment (e.g. a new `A <name> → 145.239.78.161` for another app behind the same edge) through the
  GoDaddy API: `PUT https://api.godaddy.com/v1/domains/hackstorm.eu/records/A/<name>` with
  `Authorization: Bearer gd_pat_…` and body `[{"data":"<ip>","ttl":600}]`. The personal access token is not stored
  on this VM: ask the user for it, use it only in the command, and never write it to a file or commit it. Existing
  record: `A misja-aed → 145.239.78.161`.
- A second name for the same deployment needs three things: the DNS record, a site block in that Caddy, and
  `dokku domains:add`. Export links use `PUBLIC_BASE_URL`; a request that comes in through an origin listed in
  `EXTRA_PUBLIC_BASE_URLS` gets links on that origin instead (unset today).

## Publishing on dane.gov.pl

- What the portal requires and how our export measures up: [docs/task/dane-gov-pl-formats.md](docs/task/dane-gov-pl-formats.md)
  and [docs/task/dane-gov-pl-source-code.md](docs/task/dane-gov-pl-source-code.md).
- Portal source code (GPL, read as documentation, never copy it into this repo): `~/dane-gov-pl/backend/mcod/`.
  Harvester XSDs: `~/dane-gov-pl/backend/data/harvester/`.
- The portal imports us from `https://misja-aed.hackstorm.eu/api/export/harvester.xml` (and its `.md5`): a data source
  of type XML, frequency daily. In mcod, use the test institution „Misja AED - instytucja testowa” (id 2839). A portal
  institution can have only one XML source, and its XML URL cannot be edited after creation (delete it and add a new
  one). The public URL passes the portal's XML validation, its harvester schema and its periodic link check.
- To check a change against the real portal code, run its own functions in the containers, e.g.
  `docker exec mcod-celery … manage.py shell`: `mcod.harvester.utils.validate_xml_url`, the harvester schema from
  `settings.HARVESTER_IMPORTERS["xml"]`, and `resources.score_computation.calculators.calculate_score_for_json`.

## The task (read before making product decisions)

- Brief: [docs/task/README.md](docs/task/README.md) (summary) · [docs/task/zadanie-konkursowe-misja-aed.pdf](docs/task/zadanie-konkursowe-misja-aed.pdf) (original, Polish).
- What is judged: dane.gov.pl compliance 30%, logo + slogan 25%, creativity 15%, fit 15%, reference data scope (xlsx)
  10%, presentation 5%.
- Hard requirements: machine-readable published data (no pdf/doc), WCAG + responsive UI, deliverables include the
  reference scope as **xlsx**, source code, a working prototype and ≥ 5 slides with screenshots.
- Team research for the slides and pitch (NO/DK/UK registers, AED model catalogue, standards, submission rules, and
  how it compares to our data): [docs/research/README.md](docs/research/README.md).
- The brief's core user question is *where is the nearest AED, is it accessible right now, does it work*: favour
  changes that improve location precision, availability (hours, access conditions) and readiness data.

## Code

Architecture, data model, sync/merge rules and the source table are in [README.md](README.md); API contract in
[docs/api.md](docs/api.md); how each source delivers data in [docs/integrations/](docs/integrations/README.md).

- `backend/`: Django 6 + django-ninja, Python 3.13, `uv`. Connectors live in
  `backend/integrations/connectors/<slug>/` (connector.py, fixtures/, test_connector.py; notes in
  `docs/integrations/sources/<slug>.mdx`). Exports and the
  dane.gov.pl metadata / harvester XML / JSON-LD: `backend/devices/exports.py`.
- `frontend/`: Next.js 16 admin UI (HackNation design system). It proxies `/api/*` to Django.
- Raw source downloads: `backend/var/snapshots/<slug>/` (gitignored). Use these for data analysis instead of
  re-downloading.

```bash
npm run backend                    # Postgres+PostGIS :5434, Redis :6380, Celery, Django :8000 (127.0.0.1)
npm run frontend                   # Next.js :3000
npm run sync -- <slug> --dry-run   # test a connector against the live feed without writing
npm run test                       # backend tests (real Postgres, fixtures instead of feeds)
npm run format:backend             # ruff
npm run lint && npm run typecheck  # frontend
```

## Data notes

- `osm-poland` is the bulk of the data (~18.3k OSM nodes). Most useful detail is in Polish free text
  (`defibrillator:location[:pl]`, `description`, `note`, `fixme`). Findings and the LLM extraction benchmark:
  [docs/llm-extraction/report.mdx](docs/llm-extraction/report.mdx). Only ~5% of devices have an address.
- Per-field merge precedence: operator 90 > city 50–60 > OSM 10. Anything inferred (rules or LLM) must rank below the
  source's own tags and keep provenance.
- `teryt` and `city` that no source states are filled from the coordinates and the PRG boundaries
  (`backend/devices/boundaries.py`, `field_sources` method `geocoded`): only when certain, never street, house number
  or postal code. Needs `manage.py load_boundaries` once per database (`npm run backend` does it if missing; on Dokku
  run `dokku run misja-aed-api python manage.py load_boundaries --if-missing` after the first deploy with it).
- LLM extraction runs inside every sync (`backend/integrations/enrichment/`, `LLM_ENABLED` in `backend/.env`; also on
  for the Dokku API, which reaches the vLLM at its Tailscale IP). Changing the prompt or output schema bumps
  `PROMPT_VERSION` and re-extracts everything (~1 h for OSM): re-run `scripts/llm_bench/` first and keep the backend
  prompt identical to the benchmarked one. Admins watch it live at `/ai` ("Klasyfikuj ponownie" = sync with
  `reextract`; `warszawa-19115` is the quick demo, ~3.5 min).
- The local dev frontend (`npm run frontend`, `http://100.78.88.117:3001`) is not in the default
  `DJANGO_CSRF_TRUSTED_ORIGINS`, so POSTs from it get 403 unless `backend/.env` lists that origin.

## Shared GPU server (hacknation-dev)

- vLLM runs in Docker, compose file `/home/user/vllm/docker-compose.yml` (container `vllm`), OpenAI-compatible API at
  `http://100.78.88.117:8000/v1` (Tailscale IP only), served model name `qwen` = `Qwen/Qwen3.8-27B-FP8`.
  Open WebUI and others use it.
- One A100 40 GB (vGPU/MIG): only ~36.5 GiB is free at start, so only one model fits at a time.
- If you stop it to test other models, restore it afterwards with
  `sudo docker compose -f /home/user/vllm/docker-compose.yml up -d` and check `/v1/models`.
- The host nginx (Dokku's) also serves `*.mcod.local` on `100.78.88.117:443` (`/etc/nginx/conf.d/mcod-local.conf`).
