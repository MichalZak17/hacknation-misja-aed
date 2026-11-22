# dane.gov.pl source code: what the portal checks and how our export meets it

The brief lists the portal's open source code under "Dostępne zasoby": https://dane.gov.pl/source-code/. Checked
2026-11-21 against `backend_latest.zip` (backend 2.63.0). Paths are relative to `mcod/` in that zip (a local copy is
in `~/dane-gov-pl/backend/mcod/`). The knowledge-base rules are in [dane-gov-pl-formats.md](dane-gov-pl-formats.md).

> The portal code is **GPL v3**. Read it as documentation only, never copy it into this repo: the brief requires an
> original solution the team holds all rights to.

## Summary

| Portal rule | Where in mcod | Our export |
|---|---|---|
| Licences: CC0 1.0, CC BY 4.0, CC BY-SA 4.0 (+ NC/ND variants); **no ODbL** | `datasets/models.py` `Dataset.LICENSES` | **CC BY-SA 4.0** (closest to the ODbL of the OSM part), OSM attribution in the licence conditions; `DATASET_LICENSE` overrides |
| `update_frequency` is a code (`daily`, `weekly`, …) | `datasets/models.py` | `daily`, explicit `false` `has_*` flags, automatic data date per resource |
| Supplements only doc, docx, pdf, txt, odt | `settings/base.py` `ALLOWED_SUPPLEMENT_MIMETYPES` | `schema.xlsx` is a resource (2★), `schema.txt` the supplement |
| Address in separate fields (Standard §3; `address_feature` check) | `templates/painless/` | `street_type`, `street`, `house_number` derived from `address` (`backend/devices/address.py`); only ~5% of devices have an address |
| Openness: JSON that parses as RDF = 4★, linked across ≥ 2 domains = 5★ | `resources/score_computation/` | `aeds.jsonld` (schema.org, `sameAs` to OSM): **5★** |
| Automatic import from an XML source (XSD 1.13) | `harvester/` | `/api/export/harvester.xml` + `.md5`, validated with the portal's own code |
| No completely empty CSV column (Standard §4); datetime without offset | `templates/painless/datetime` | `aeds.csv` leaves out columns no record fills (full set in `schema.xlsx`); datetimes in UTC with `Z` |

## Link validation (`resources/link_validation.py`)

- **HTTPS** after redirects, status **200**, a `Content-Type` from `ALLOWED_CONTENT_TYPES` (`text/csv`,
  `application/geo+json`, `application/json` are allowed).
- `application/json` **without `Content-Disposition: attachment`** is classified as an **API**, not a file. Our
  `export_response` sends `attachment; filename=…`, so every export is a file. Keep it that way.
- The status check sends HEAD first and falls back to GET; download timeout 180 s, status check 5 s / 15 s.

## Map and table preview

- GeoJSON is **not** mapped automatically. The map comes from the CSV resource, after the publisher assigns the geo
  columns once in the panel (`resources/forms.py`): `lat` → b, `lon` → l, `id` or `building_name` → label.
- **Table validation** (`resources/type_guess.py`, `resources/indexed_data.py`): the portal infers one type per column
  from the first 5000 rows (75% wins; any 10-character value is tried as a date) and validates the first 1000 rows.
  Only the resource's special signs count as missing values, so an empty cell in a typed column fails. Our CSV
  therefore writes coordinates with 6 decimals (10 characters would be typed as a date), `floor` as a whole number, and
  `.` (XSD: "zupełny brak informacji") in every empty typed cell, declared as the CSV resource's `specialSigns`.

## Data-quality checks (`templates/painless/*.painless`)

`pna` (`\d\d-\d\d\d`), `address_feature` (street prefix in its own column), `date` (`yyyy-mm-dd`), `datetime` (no
`+01:00` offset), `bool`, `phone` (9 digits or `+48` + 9), `regon` / `nip` / `krs` / `uaddress` / `numeric`. Our
export passes all that apply.
