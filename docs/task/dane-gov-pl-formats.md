# dane.gov.pl — required formats and publishing rules

What the brief's "Dostępne zasoby" (the dane.gov.pl knowledge base) require of published data, checked 2026-11-21.
The brief itself names only: machine-readable data (no pdf/doc), the reference scope as **xlsx**, logo as
jpg/png/pdf + an open format, brand book as pdf. Everything else below comes from these sources:

- **Standard techniczny 2020**: https://dane.gov.pl/media/ckeditor/2020/06/16/standard-techniczny.pdf (formats,
  openness levels, CSV/JSON rules, data and address formatting)
- **Przewodnik dla dostawców danych 1.23**: https://cms.dane.gov.pl/documents/283/Przewodnik_dla_dostawc%C3%B3w_danych_1.23.pdf
- **Harvester XSD** (automatic XML import): https://www.dane.gov.pl/static/xml/otwarte_dane_latest.xsd
  (`urn:otwarte-dane:harvester:1.13`)
- Precedents where the ministry defined a reference scope itself:
  [rzeczy znalezione](https://dane.gov.pl/pl/knowledgebase/useful-materials/udostepnianie-danych-dotyczacych-rzeczy-znalezionych-informacje-dla-starostow),
  [ceny mieszkań](https://dane.gov.pl/pl/knowledgebase/useful-materials/udostepnianie-danych-dotyczacych-cen-mieszkan-informacje-dla-deweloperow)
- **Portal source code** (what the portal actually validates and scores, and how our export meets it):
  [dane-gov-pl-source-code.md](dane-gov-pl-source-code.md)

## Formats and openness (Standard techniczny §2)

| Stars | Formats |
|---|---|
| 1 | PDF, TXT, JPG/PNG |
| 2 | XLS, XLSX, DOCX (XLSX "not recommended above level 2") |
| 3 | **CSV**, **JSON**, XML, ODS, DBF; vector spatial **GeoJSON**, GML, SHP, KML, GPX; GeoTIFF |
| 4–5 | JSON-LD, RDF/XML, Turtle, N3, N-Triples, RDFa; CSV with W3C *Tabular Data on the Web* (CSVW) metadata |

The portal converts XLS/XLSX → CSV + JSON-LD and CSV → JSON-LD itself (**only the first sheet** of a workbook).

## Data formatting (§3) — required regardless of format

- Booleans `true` / `false`; decimal point, no thousands separators; dates `yyyy-mm-dd`, datetimes
  `yyyy-mm-ddThh:mm` (ISO 8601).
- One value per field ("nie łączyć kilku danych w jednym polu").
- **Address as separate fields**: street (with its prefix, e.g. `ul.`), building number, flat number, postal code,
  town — never one free-text address field. Names literally as in TERYT (ULIC / SIMC). The *adres uniwersalny*
  (`PNA|TERC|SIMC|SIMC|ULIC|x|y|nr`) is recommended.
- REGON 9 or 14 digits, NIP/KRS 10 digits, phone 9 digits (or `+48…`), no spaces or dashes.

## CSV (§4)

- RFC 4180: CRLF line ends, comma separator, quotes around special characters, UTF-8.
- Exactly one header row, every column named, no duplicate names, equal cell count in every row.
- **No completely empty columns or rows.** Every row stands alone (no blanks meaning "same as above").
- 4 stars: CSVW metadata.

## JSON (§5)

RFC 8259. For APIs: JSON API structure. 4 stars: JSON-LD with full semantic context.

## Publishing (Przewodnik)

- A resource can be a file, an API or a link. Links must be **HTTPS**.
- Link + **"automatyczna aktualizacja"**: the portal re-downloads the file on a schedule (daily / weekly / monthly)
  and updates "dane na dzień"; without it the file is fetched once.
- Licence: the portal recommends **CC0 1.0**; the selectable database licences are only **CC0 1.0, CC BY 4.0,
  CC BY-SA 4.0** (XSD `dbOrCopyrightedLicenseChosen`). ODbL is not on the list.
- After upload the portal validates the file and builds a table view; columns holding TERYT, postal codes, phone
  numbers or REGON should be set to text ("Zmiana typu"), otherwise leading zeros are dropped. House numbers like
  `5a` need "dowolny typ".
- Quality checks on the portal: numeric field, REGON, NIP, KRS, adres uniwersalny, kod PNA, cecha adresu, phone
  number, boolean.
- Categories (XSD): AGRI, EDUC, ENVI, ENER, TRAN, TECH, ECON, SOCI, HEAL, GOVE, REGI, JUST, INTR. Special signs:
  `-`, `.`, `X`, `:`, `#`.

## How the ministry ships a reference scope (precedents)

- **xlsx + csv (UTF-8)**: one sheet named "wzorcowy zakres danych", a single row of readable Polish column headers,
  then example rows. The data template is the first sheet, not a field dictionary.
- **XML import template** in the harvester schema: the provider hosts one XML file describing its datasets and
  resources (title/description in Polish and English, `updateFrequency`, categories, tags, resource `url`,
  `availability` local/remote, `dataDate`, licence conditions). The portal pulls it automatically.

## List of protected data (DGA)

Every public body publishes a list of the protected data it holds (Data Governance Act art. 8). dane.gov.pl turns
those lists into one nationwide table, „Wykaz chronionych danych” (`/pl/dga/list-protected-data/table`, the same path
on the test portal: https://dane.hackstorm.eu/pl/dga/list-protected-data/table). From the portal source (`mcod/resources/dga_utils.py`,
`mcod/harvester/serializers.py`, `mcod/celeryapp.py`):

- The table is a resource the portal **rebuilds every night** (`create_main_dga_resource_task`, 03:30 UTC; harvester
  imports run at 03:00 UTC). It takes every published resource with `contains_protected_data=True` whose data, file
  and link checks succeeded, adds „Nazwa dysponenta zasobu” (the institution's name), renumbers „Lp.” and replaces
  „Warunki ponownego wykorzystywania” with „określone w ofercie”. `GET api.…/1.4/dga-aggregated` names the current one.
- An XML provider flags one resource with `<containsProtectedData>true</containsProtectedData>` (XSD 1.12+). The
  harvester then checks: institution type `local` or `state`; the four `has*` flags false; the URL answers 200 with a
  Content-Type that `mimetypes.guess_extension` maps to xlsx/xls/csv (**`text/csv; charset=utf-8` maps to nothing**,
  so we serve xlsx); the header is exactly `Lp. | Zasób chronionych danych | Format danych | Rozmiar danych | Warunki
  ponownego wykorzystywania`; at most one such resource per XML; no DGA resource of the institution added by hand.
  **A failed check rejects the whole XML import**, the AED dataset included.
- A row with an empty „Zasób chronionych danych”, „Format danych” or „Rozmiar danych” drops the whole resource from
  the nightly table.

Ours: `backend/devices/dga.py` builds `/api/export/wykaz-chronionych-danych.xlsx` from the database on every export
rebuild (form reports, one row per operator file, the raw source archive), and `harvester.xml` carries it as a second
dataset `misja-aed-dga`. So our rows reach the national table the night after any change, with no manual step.
