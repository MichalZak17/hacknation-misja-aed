# dane.gov.pl publishing standards: complete inventory (checked 2026-11-22)

What the dane.gov.pl knowledge base and the law it cites require from a data provider, document by document, with a
checklist at the end. Short summaries of the most important points are in
[dane-gov-pl-formats.md](dane-gov-pl-formats.md); what the portal code actually validates is in
[dane-gov-pl-source-code.md](dane-gov-pl-source-code.md).

**Method.** The knowledge base pages (`/pl/knowledgebase/...`) are rendered by JavaScript, so they were read through the
portal's Wagtail CMS API (`https://cms.dane.gov.pl/api/pages/knowledgebase/...?format=json`). The full document
register was listed through `https://cms.dane.gov.pl/api/documents/` (233 documents, highest id 292). Each PDF was
downloaded and its text extracted. Rules marked *(code)* come from the portal source code (mcod 2.63.0), not from a
published document.

**How the rules are labelled.** The Standard techniczny defines its own terms (POD annex 2, §1), and this file follows
them:

| Polish term | Label here | Meaning given by the standard |
|---|---|---|
| *wymaga się* | **MUST** | "trzeba bezwarunkowo spełnić" (must be met without exception) |
| *nie dopuszcza się* | **MUST NOT** | "nie wolno postąpić w opisany sposób" (not allowed) |
| *zaleca się* | **SHOULD** | may be skipped only "pod warunkiem że opisująca zasoby dokumentacja (np. dokumentacja API…) zawiera uzasadnienie decyzji o odstępstwie" (if the documentation explains why) |
| *nie zaleca się* | **SHOULD NOT** | allowed only in exceptional cases, also explained in the documentation |
| *dopuszcza się* | **MAY** | optional, no explanation needed |

So a SHOULD is weaker than a MUST but still has a cost: **every deviation from a "zaleca się" rule must be explained
in the dataset's or API's documentation.**

---

## 0. Document map: what is current

| # | Document | Version / date | Status |
|---|---|---|---|
| 1 | **Program otwierania danych na lata 2021-2027** (Uchwała nr 28 RM, M.P. 2021 poz. 290), **annex 2 "Standard techniczny"** and **annex 3 "Standard API"**: https://cms.dane.gov.pl/documents/29/POD_M.P._290.pdf | 18.02.2021 | **The binding, current standards.** The FAQ, Przewodnik 1.23 and both "Wskazówki" PDFs point here ("Standardy techniczne dotyczące przygotowania danych znajdują się w załączniku nr 2 do Programu otwierania danych na lata 2021-2027… strona 122"). |
| 2 | Standard techniczny 2020 (standalone): https://dane.gov.pl/media/ckeditor/2020/06/16/standard-techniczny.pdf | 2020-06 | Still linked on "Standardy otwartości danych" (page last edited 2020-11-12). **Superseded in practice by POD annex 2**, which repeats it and adds §3.1 (spreadsheet rules) and §3.2 (REGON/NIP/KRS/phone). The 2020 edition additionally has a DCAT-AP JSON-LD example (annex 1). |
| 3 | Standard API 2020: https://dane.gov.pl/media/ckeditor/2020/05/29/standard-api.pdf | 2020-05 | Same content as POD annex 3, which is the version to cite. |
| 4 | Standard prawny 2020 / Standard bezpieczeństwa 2020 (same page) | 2020 | Background (licensing barriers, anonymisation, GDPR impact assessment). No format rules. Written before the 2021 act. |
| 5 | **Przewodnik dla dostawców danych 1.23**: https://cms.dane.gov.pl/documents/283/Przewodnik_dla_dostawc%C3%B3w_danych_1.23.pdf | **1.23, 2026-07-16** | **Current. No newer version exists**: the document register holds 1.7 … 1.22 and 1.23 (id 283), nothing later. |
| 6 | **Harvester XSD**: https://www.dane.gov.pl/static/xml/otwarte_dane_latest.xsd | **namespace `urn:otwarte-dane:harvester:1.13`** | **Current, still 1.13.** The 2025–2026 XML templates are labelled "v.1.14" (`Szablon_budowy_pliku_xml_v.1.14_…`), but that is the template's version: their namespace is still `…harvester:1.13`, and the portal code ships XSDs only up to `xml_import_otwarte_dane_1_13.xsd`. |
| 7 | **Wskazówki dotyczące przygotowania danych do publikacji w portalu v1.0.1**: https://cms.dane.gov.pl/documents/234/… | 1.0.1, 10.07.2025 | Current. A short version of the spreadsheet rules, **plus a newer "X in every empty cell" rule**. |
| 8 | Wskazówki … dane o rzeczach znalezionych v1.0: https://cms.dane.gov.pl/documents/278/… | 1.0, 15.05.2026 | Current; same rules (dates, X), without REGON/NIP/phone. |
| 9 | **Przewodnik automatycznego dodawania danych xml, v1.02** (general XML import guide): https://cms.dane.gov.pl/documents/225/Przewodnik_automatycznego_zasilania_danych_xml.PDF | 1.02 (page "stan na 20.06.2025") | Current. Checks the XML source must pass. |
| 10 | Instrukcja przygotowania pliku XML (deweloperzy) 1.0.6: https://cms.dane.gov.pl/documents/256/… | 1.0.6, 18.11.2025 | Specific to developers, but the most detailed field table for XSD 1.13 (types, cardinalities, notes on `extIdent`, `url`, `specialSigns`). |
| 11 | Rekomendacje dot. maksymalnej liczby zasobów (XML source): https://cms.dane.gov.pl/documents/268/… | 2025/2026 | Current: ≤ 1000 `<resource>` per XML file. |
| 12 | **Rozporządzenie RM z 21.11.2022 w sprawie portalu danych** (Dz.U. 2022 poz. 2415): https://cms.dane.gov.pl/documents/116/… | in force since 08.12.2022 | **Binding.** Defines the required metadata set and what the portal checks. |
| 13 | **Ustawa z 11.08.2021 o otwartych danych i ponownym wykorzystywaniu ISP** (Dz.U. 2021 poz. 1641, later amended): https://cms.dane.gov.pl/documents/65/D2021000164101.pdf | 2021 text (the portal's own copy) | **Binding.** Articles used here: 2, 10, 11, 13–15, 24–26, 32, 34. |
| 14 | Licence page "Warunki ponownego wykorzystywania ISP oraz standardowe otwarte licencje w portalu": https://dane.gov.pl/pl/page/opis-warunkow-i-licencji-dla-dostawcow-sektora-publicznego | 2022-05-11 | Current. Which licence to pick and when. |
| 15 | LOD report: sposoby udostępniania danych przez API na portalu: https://cms.dane.gov.pl/documents/26/… | November 2020 | The only document that says **how to register an API on the portal** (what the dataset must contain). |
| 16 | LOD report: dostępne cyfrowo treści w portalu: https://cms.dane.gov.pl/documents/92/… | ~2021 | Accessibility rules for descriptions, xlsx and docx supplements. |
| 17 | LOD report: znaki umowne: https://cms.dane.gov.pl/documents/21/raport-znaki-umowne-me.pdf | ~2020 | Background on special signs (not read in full). |
| 18 | Ekspertyza DCAT-AP + model_metadanych.xlsx: https://dane.gov.pl/media/ckeditor/2019/07/05/ekspertyza-dcat-ap.docx | 2019 | How the **portal itself** exposes DCAT-AP. Imposes nothing on providers. |
| 19 | KB pages "Dane dynamiczne", "Dane o wysokiej wartości", "Dane o wysokiej wartości (HVD)", "Dane o wysokiej wartości z wykazu KE", "Dane badawcze", "Udostępnianie… zasobów zawierających dane osobowe", "Prawo", FAQ | 2022–2025 | Current. They explain the metadata flags and the law. |
| 20 | Reference-scope precedents: [rzeczy znalezione](https://dane.gov.pl/pl/knowledgebase/useful-materials/udostepnianie-danych-dotyczacych-rzeczy-znalezionych-informacje-dla-starostow) (edited 2026-05-21) and [ceny mieszkań](https://dane.gov.pl/pl/knowledgebase/useful-materials/udostepnianie-danych-dotyczacych-cen-mieszkan-informacje-dla-deweloperow) (**edited 2026-11-10**), plus the new [wzorcowe dokumenty elektroniczne 11.11.2026](https://dane.gov.pl/pl/knowledgebase/useful-materials/wzorcowe-dokumenty-elektroniczne-suzace-do-realizacji-obowiazkow-deweloperow-mieszkaniowych-11112026) | 2025–2026 | Current. **New since our last check**: the ceny mieszkań page now follows the Minister's regulation of 10.11.2026 (Dz.U. 2026 poz. 1489), with templates in xlsx, csv, xml **and json**; the previous version is archived as a separate page (id 476, "STRONA ARCHIWALNA"). |
| 21 | Ustawa z 4.04.2019 o dostępności cyfrowej (consolidated text Dz.U. 2023 poz. 82, amended by Dz.U. 2023 poz. 511) | – | Binding for public bodies' own websites. Cited in Przewodnik ch. 14. |
| 22 | Commission Implementing Regulation (EU) 2023/138 (HVD): https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX%3A32023R0138 | applies since 09.06.2024 | Binding, **only for datasets on the Commission's list**. AEDs are not on it (see §9). |

**Not found anywhere in the knowledge base:** a CSVW how-to beyond "use the W3C tabular data model", a GeoJSON or CRS
rule beyond "coordinates in WGS84" (the map feature) and "follow Spatial Data on the Web Best Practices", a DCAT-AP-PL
profile for providers, any rule on file size (only the code limit: 1 GB), any public "raport jakości" (quality report)
document, and any API registration procedure other than the 2020 LOD report.

Other knowledge base pages read and found to set **no** provider rules: Harmonogramy udostępniania danych (half-yearly
schedules), Kalendarium (events), Badania rynku, Program otwierania danych 2016-2020, the API descriptions of
specific systems (CEIWT, Trezor, DBW, Otwarte Dane Plus), and the Szkolenia multimedialne section (videos).

---

## 1. POD 2021-2027, annex 2: Standard techniczny (binding version)

Source: M.P. 2021 poz. 290, pp. 118–133 of the PDF. Purpose (§1): "zestaw minimalnych wymagań technicznych, które
muszą spełniać dane, w szczególności udostępniane w portalu Dane.gov.pl".

### 1.1 Openness levels and formats (§1, §2, table 9)

- SHOULD NOT publish at level 1 ("Nie zaleca się publikowania danych na pierwszym poziomie otwartości").
- SHOULD publish level-3+ data through an API ("Dane na poziomach otwartości 3 (***) i wyższych zaleca się udostępniać przez API").
- JPEG/PNG: level 1 only, unless the images themselves are the data. PDF: level 1 only. **TXT**: level 1; data with a structure "powinny być udostępniane z oznaczeniem innego, właściwego typu pliku (np. CSV)".
- Archives: ZIP (without proprietary extensions), 7z, Gzip, Bzip2 allowed at every level; RAR and extended ZIP up to level 2 only.
- XLS/DOC: proprietary, up to level 2. An XLS data sheet MUST follow the CSV rules of §4.1–4.2.
- **XLSX/DOCX: "nie są zalecane jako formaty udostępniania otwartych danych powyżej 2. (**) poziomu"** (not recommended above level 2). Table 9 lists Office Open XML as "dopuszczalne" (allowed) at level 2 and "niedopuszczalne" (not allowed) at levels 3, 4 and 5.
- DBF up to level 3. HTML: allowed up to level 3 for structured data, not recommended above. ODS: allowed up to level 3.
- **CSV and JSON: "zalecany" (recommended) at level 3.** XML: allowed at level 3; "Dopuszcza się stosowanie formatu XML, jednocześnie zalecając stosowanie formatów JSON lub CSV".
- RDF/XML, Turtle, N3, JSON-LD, N-Triples, RDFa: recommended at levels 4 and 5.
- **Spatial data (§2.14):** raster without georeference = level 1; GeoTIFF = level 3; **vector "GML, SHP, KML, GeoJSON, GPX" = level 3**; spatial data with RDF context allowed at every level. "Udostępniając takie dane, należy zachować dobre praktyki opisane w dokumencie *Spatial Data on the Web Best Practices*" (W3C SDW-BP). Spatial data services (WMS, WMTS, WFS, WCS, ATOM) and INSPIRE metadata apply to INSPIRE datasets. **There is no CRS/EPSG rule in the standard.**
- Table 9 also says: XML Schema data types "zalecane" (recommended) at levels 2–3; **XML Namespaces "wymagane" (required) at levels 4–5**.

### 1.2 Value formatting (§3), whatever the format

- MUST: "Niezależnie od wyboru formatu pliku danych wymaga się stosowania właściwego formatowania, w szczególności dla danych typu: liczba, data, godzina, wartość logiczna." (Correct formatting of numbers, dates, times and booleans is required whatever the format.)
- At levels 4–5, every property's type MUST be defined by a URI (e.g. `schema:datePublished` → ISO 8601).
- At levels ≤ 3, SHOULD ("zaleca się") use ISO 8601 and XML Schema basic types, i.e.:
  - booleans as the literals `true` / `false`;
  - a decimal **point**, with no thousands separators (scientific notation allowed);
  - dates `yyyy-mm-dd`; date and time `yyyy-mm-ddThh:mm` **or** `yyyy-mm-dd hh:mm:ss` (with a space).
- Examples of wrong values (table 5): `1/1/1970`, `1.1.1970`, `1 I 1970`, `45,01`, `1,234.56`, `1 234,5`, `T`, `0`, `NIE`.
- SHOULD publish at the finest granularity: "nie należy łączyć kilku danych w jednym polu" (do not put several values in one field).

### 1.3 Spreadsheets (xls/xlsx), §3.1 (new in 2021)

1. MUST have exactly one header row describing every column. MUST NOT: (a) merge cells, in rows or in columns; (b) spread one record over several rows; (c) put titles, descriptions, footnotes or comments outside the data table; (d) use aggregating formulas (SUM) or filters; (e) use formulas that pull data from outside the file.
2. MUST: each column holds one kind of data (number, text, or a coded string such as a phone number or postal code).
3. SHOULD: each column holds one elementary value (a code, not "code + town").
4. MUST: every cell matches the column's format or mask.
5. Do not use text formatting, or punctuation that can look like an arithmetic operator; for example a leading hyphen can turn a value into a formula error or a negative number.
6. If these rules cannot be met, split the table.
7. SHOULD publish single sheets, not workbooks.

### 1.4 Identifiers and phone numbers (§3.2)

- REGON MUST be 9 or 14 digits, NIP 10 digits, KRS 10 digits, with no spaces or hyphens.
- Phone numbers SHOULD be 9 digits, with no area-code markup, spaces or hyphens; a `+` international prefix is allowed.

### 1.5 Addresses (§3.3)

- MUST: "adres pocztowy był udostępniany jako szereg danych opisowych: nazwa ulicy, numer budynku, kod pocztowy, miejscowość – umieszczonych w odrębnych polach" (street, building number, postal code and town, each in its own field). Table 6 shows the column layout: `Kod PNA | Miejscowość | Cecha | Nazwa ulicy | Nr budynku | Nr lokalu`, so the street prefix (`ul.`, `al.`, `pl.`) is a separate column ("cecha").
- MUST: address text "literalnie zgodne z ich zapisem w źródle ich wytworzenia" (literally as written at the source); in practice the TERYT ULIC/SIMC names, unchanged in transit.
- SHOULD use the *adres uniwersalny*: `PNA (5 digits, no hyphen) | TERC (6) | SIMC of the main town (7) | SIMC (7) | ULIC (5, "00000" if there are no streets) | x | y | building number`, separated by `|`. Example: `00184|146501|0918123|0918123|04337|489147.9218|636045.6562|5A|`. The x/y in the example are PUWG 1992 metres, the coordinates of the GUGiK address point; the standard does not name the CRS.
- Correct address points come from GUGiK (`integracja.gugik.gov.pl/daneadresowe`); the portal has an address-checking application.

### 1.6 CSV (§4)

- §4.1, RFC 4180: **SHOULD at level 3, MUST at level 4** ("Na 3. (***) poziomie otwartości zaleca się stosowanie formatu CSV określonego w RFC 4180, a na 4. (****) poziomie – wymaga się tego ściśle"). That means CRLF line ends, comma separator, quotes around special characters (commas, newlines inside fields), and UTF-8 by default, or another encoding declared correctly in the `Content-Type` header.
- §4.2 (level 3), all MUST:
  - exactly one header row;
  - the header row holds only headers and every other row only records; no "legenda" (legend) block;
  - no column without a header or with a blank header; no repeated headers;
  - every row, including the header, has the same number of cells;
  - **"Niedopuszczalna jest obecność całkowicie pustych kolumn bądź wierszy"** (no completely empty columns or rows);
  - every row stands alone: no blanks meaning "same as above".
- §4.3 (levels 4–5): MUST use the W3C *Model for Tabular Data and Metadata on the Web* (CSVW), so that the CSV can be turned into RDF/JSON-LD (csv2json, csv2rdf).

### 1.7 JSON (§5)

- Level 3: MUST be valid RFC 8259 JSON. For APIs: "W tym celu należy przyjąć standard JSON API" (adopt JSON:API). SHOULD shape the data so semantic context can be added later. "W celu osiągnięcia kolejnych poziomów otwartości należy stworzyć dane kontekstowe przekazywane w nagłówku HTTP" (context data passed in the HTTP header).
- Level 4: MUST use JSON-LD "i opatrzenie danych pełnym kontekstem semantycznym", with **every** property mapped to an RDF URI. JSON-LD "nie może kolidować z organizacją danych wynikającą ze standardu JSON API" (must not conflict with the JSON:API structure). "Dane kontekstowe należy przekazywać w nagłówku http." Level 5: MUST add links to other data.

### 1.8 XML (§6)

- MAY use XML, but JSON or CSV is recommended.
- Level 3: any valid XML in which object properties are elements.
- Levels 4–5: MUST define semantics (URIs) for all elements through XML Namespaces and dedicated schemas.

### 1.9 RDF, linked data, DCAT-AP (§7–8)

- §7: RDF serialisations are equivalent. SHOULD carry out a cost-benefit analysis before building linked data.
- §8 DCAT-AP: "Zaleca się stosowanie specyfikacji do opisywania zbiorów danych sektora publicznego" (SHOULD describe datasets with DCAT-AP), to exchange descriptions between dane.gov.pl and other portals. In practice the portal generates the DCAT-AP record from its own metadata (ekspertyza and model_metadanych.xlsx); providers have **no separate DCAT-AP-PL obligation**.

### 1.10 Where data lives (§9) and the publishing procedure (§10)

- Data can be published on the portal as (a) a file stored in the portal, or (b) a URL of the provider's repository.
- Providers that link to external locations SHOULD ensure every published resource stays available permanently.
- Recommendations: (1) each resource in a separate file; (2) **"Stosowanie wersjonowania zasobów, zamiast zastępowania/nadpisywania (każdy nowy plik pod nowym adresem URL)"** (version resources instead of overwriting them: each new file at a new URL); (3) keep each file's URL unchanged; (4) keep every published resource available; (5) use repositories that survive organisational change.
- Procedure: check rights; split complex resources into simple ones (workbook → single sheets); remove formulas and external references; clean the data. The description must precisely characterise the content and its bounds ("data/okres, obszar, sektor"). Choose keywords from a vocabulary where possible. Monitor update, permanence and availability.

---

## 2. POD 2021-2027, annex 3: Standard API (binding version)

Source: M.P. 2021 poz. 290, pp. 134–156 of the PDF. The standard calls itself "minimalne, rekomendowane zalecenia"
(minimal recommendations), but many items say "musi" (must), "obowiązkowe" (mandatory) or "nie wolno" (must not).
They are labelled that way here.

**Architecture (§2)**
- REST, JSON (RFC 7159). JSON Schema for notation; **JSON:API** for request and response messages; JSON-LD for context.
- Resource-based; supports caching, **including the HEAD method**; uniform interface; self-describing messages; provides information about the data structure.
- MUST serve JSON. MAY also serve XML, selected through the `Accept` header or a `&format=` parameter.
- Level 3: plain JSON. Level 4: a JSON-LD context covering all attributes. Level 5: links between resources.
- **"Interakcja z API jest możliwa wyłącznie przy użyciu szyfrowanego połączenia HTTPS"** (HTTPS only).

**Resource naming (§3)**
- Simple names; nouns; **plural** ("czujniki", not "czujnik"); MUST NOT use verbs ("pobierz-formularze").
- Specific names ("przeglady-rejestracyjne", not "przeglady").
- MUST NOT use Polish diacritics in resource identifiers or URIs.
- **Lowercase**; join words with hyphens `-`; MUST NOT join with underscores `_` or other special characters.

**URI syntax (§4)**
- The domain MUST identify the API's owner and "musi udostępniać funkcjonalność API przez subdomenę „api”, chyba że nie jest to możliwe z uzasadnionego powodu" (must serve the API from an `api.` subdomain unless there is a good reason not to).
- MAY have a developer portal on a `dev.` subdomain. Without one, the API's main page MUST give the basic usage information, including limits and how to get a key (if keys exist).
- `/` marks hierarchy; a trailing slash is not recommended; paths are lowercase.
- **"W URI nie stosuje się rozszerzeń plików oraz nazw formatów danych"** (no file extensions or format names in URIs); the format goes in HTTP headers or metadata.

**Hypermedia (§5)**
- "API musi używać techniki HATEOAS": links in the body or headers pointing to related resources.

**Filtering, sorting, paging (§6, annex 4)**
- Requests and responses follow JSON:API 1.0 or later. SHOULD add JSON-LD context to responses.
- Simple paging, filtering and sorting go through the URI. MAY also accept richer queries in the request body.
- Asynchronous requests: `202 Accepted` + `Location: /queue/{id}`, then `303`, and `410` once the result has expired.
- **"Obsługa kwerend SQL jest zabroniona"** (SQL queries are forbidden).
- Conventions from annex 4: `filter[<attribute>]=<value>`; several conditions joined with `&`; `fields=a,b,c`; `sort=-x,y` (minus means descending, ascending by default; return an error for an unsupported sort); paging with `page` and `limit`.
- **Deviations from JSON:API that are mandatory (§14):** the API MUST support sparse fieldsets (field selection), sorting where it makes sense, filtering, and detailed error objects.

**Metadata (§7, annex 5)**
- Resources carry a minimal metadata set: `dc:title`, `schema:url`, `schema:provider`, `schema:datePublished` and `schema:dateModified` (ISO 8601, to the second), `schema:expires` (if any), `dc:description`, `schema:keywords`, `schema:temporalCoverage`, `dc:language`, `sy:updatePeriod` / `sy:updateFrequency` / `sy:updateBase`, `schema:contentType`, `dc:rights`, `schema:isPartOf`, `sp:checksum` (a checksum, to check completeness).
- Leave out metadata that does not apply.
- Use standard vocabularies (schema.org, DCMI). Non-standard metadata MUST come with a vocabulary that defines it.

**Navigation links (§8, annex 6)**
- JSON:API `links` with `prev`, `self`, `next`, `first`, `last`.

**Versioning (§9, annex 7)**
- SemVer; only MAJOR selects the version.
- **"Obowiązkowe jest odwołanie się do wersji przez element URL (/api/vXX/)"** (the version MUST be in the URL path).
- MAY also accept `v=XX`, an `api-version` header or `Accept`. Without a version, serve the current stable one.
- **Version information is served at a `/version` resource.**
- Mark a version "deprecated" before replacing it; do not retire a version less than 2 years after notice; after retirement answer `406` or `410`.

**HTTP (§10, annex 8)**
- Mainly GET; no methods that modify resources.
- Minimal set of status codes: 200, 201, 202, 204, 301, 303, 304, 400, 401, 403, 404, 405, 406, 409, 410, 422, 429, 500, 502, 503, 504.
- 4xx error bodies carry `error-result`, `error-reason`, `error-solution` (optional), `error-code`, `error-help` (a link to the documentation). Messages MUST be specific and actionable; useless messages are not acceptable.

**Authentication (§11)**
- **"Nie jest dopuszczalne zamknięcie API dla użytkowników nieuwierzytelnionych"** (the API MUST NOT be closed to anonymous users); extra limits for them are allowed.
- OpenID Connect recommended; OAuth 2.0 only combined with other measures; **SSL encryption mandatory**; authentication not mandatory.

**Limits (§12)**
- Per-IP or per-key limits are allowed under load. Keys follow JWT rules and are read-only.
- If limits exist, there MUST be a usage policy with plans and a priority whitelist (public systems first).
- Exceeding a limit returns **`429` with information about the limit policy and how to get whitelisted**.
- Blacklisted IPs are reviewed at least every 6 months.

**Documentation (§13)**
- MUST include at least: a description of each resource and endpoint; supported methods; parameters (HTTP method, headers, URI path, query parameters, body); example requests; example responses.
- SHOULD be machine-readable, dynamic and interactive, and generate client code samples. SHOULD use **OpenAPI 3.0 or later** (Swagger Editor or Swagger UI).

**Users (§1)**
- Anonymous, occasional use without registration; a simple web query builder (filter, sort, search on more than one condition) that works without authentication; low entry barrier; a contact for questions and bug reports; quick key issuing if keys are used; a cost-benefit analysis before building the API.

---

## 3. Przewodnik dla dostawców danych 1.23 (2026-07-16)

The current user manual for the admin panel. Rules that can be checked:

**Account (§3)**
- Editors use an **official e-mail**; password ≥ 8 characters with an uppercase letter, a lowercase letter and a special character.
- Editor rights are requested at `kontakt@dane.gov.pl` (institution, work phone, account e-mail). Name and work phone are required before the editor role works.

**Dataset metadata (§4.1)**
- Fill every field marked "pole wymagane" (required).
- **"Każdy zbiór danych powinien zawierać co najmniej jeden plik z danymi lub link do danych"** (every dataset should contain at least one file or link).
- Do not create a new dataset for a new year; keep one dataset and **"umieszczanie daty w tytule zbioru nie jest konieczne"** (no date in the dataset title); put the date in the description or the resource title.
- **Description at least 20 characters** ("Opis musi składać się z minimum 20 znaków"). It should expand the title and cite the act that requires the data.
- "Źródło" (source) = the provider's web page for the data.
- Flags: dane dynamiczne (dynamic data), dane o wysokiej wartości (high-value data), HVD z wykazu KE (HVD on the Commission's list), dane badawcze (research data). A flag set on the dataset becomes the default for new resources.
- Update frequency; category (one or more). Status "Szkic" (draft) or "Opublikowany" (published): setting a dataset back to draft also sets its resources to draft, and republishing the dataset does **not** republish them.
- Slug: words joined with `-`.
- **Keywords: at least one is mandatory**. Reuse existing tags; English tags are optional.
- Logo: jpg, gif or png (png with a transparent background recommended); **alt text required** ("Tekst zastępczy").
- **Licence (§4.1.15): "Zalecamy udostępniać dane bez określania warunków (licencja CC0 1.0)"** (CC0 recommended). Conditions are set on the "Warunki" tab (see §8 of this file).
- English title and description (Tytuł (EN), Opis (EN)) are optional. **English text inside a Polish description must be marked with "Ustaw język"** (set language), for screen readers.

**Supplementary documents (§4.4, §5.5)**
- **At most 10 per dataset**, each with a name and a language (pl or en), e.g. API documentation.
- *(code)* Allowed supplement types: doc, docx, pdf, txt, odt (`ALLOWED_SUPPLEMENT_MIMETYPES`).

**Resources (§5.1)**
- A file stored in the portal, or a URL. For a URL the portal **downloads the data and serves its own copy**; the CSV and JSON-LD buttons point to that copy, not to the provider's URL.
- **Links must be HTTPS**: "Adres URL linku publikowanego w portalu powinien zaczynać się więc od prefiksu „https” a nie „http”".
- **No xls/xlsx files with macros** ("Pliki zawierające makra nie są obsługiwane przez portal").

**Resource metadata (§5.2)**
- Language of the data (default Polish).
- Title: do not repeat the dataset title; describe what sets this resource apart; for periodic data name the period; **dates in titles written as `yyyy-mm-dd`** so titles sort correctly.
- **Description at least 20 characters.**
- **"Dane na dzień"** (data as of): the date the data is valid for; defaults to today.
- **"Automatyczna aktualizacja"** (automatic update), for API, web page and remote-file resources: the portal re-downloads the source and moves "dane na dzień" forward daily, weekly or monthly, from a start date to an end date or with no end. Without it the URL is fetched **once**. The option appears only when **editing** a saved resource, not when adding one. For remote files each update also re-runs validation. Updates run once a day at a time the administrator sets. If the link breaks, the portal keeps serving the last copy.
- Dynamic / HVD / research flags.
- "Wykaz chronionych danych" (list of protected data, DGA) cannot be combined with the dynamic, research or HVD flags.
- **Znaki umowne (special signs)**: if the data contains special signs, they MUST be declared in the panel ("dostawca danych powinien oznaczyć je"). The XSD list: `-` "zjawisko nie wystąpiło" (did not occur), `.` "zupełny brak informacji albo brak informacji wiarygodnych" (no information or none reliable), `X` "wypełnienie pozycji jest niemożliwe lub niecelowe" (not possible or not applicable), `:` (Eurostat: no information), `#` (statistical confidentiality). Charts treat special signs as missing values.
- **"Lokalizacja danych"** (location of the data): one or more territorial units (TERYT); it drives search by area and the map of results.
- Powiązane dane (related data): links a Polish resource with its English version (one link, set in both directions).

**Validation (§5.6)**
- Three steps: link (downloadable or reachable), file (format detected), data (a table view can be built: no merged cells, valid date formats, etc.).
- Formats the validator recognises (list on pp. 47–50): csv, tsv, json, json-ld, jsonld, xml, xls, xlsx, ods, dbf, shp, geotiff, rdf, ttl, n3, nt, nquads, trig, trix, txt, pdf, doc(x), etc. **`.geojson` is not on the list**; a GeoJSON file is recognised as JSON *(the code allows `application/geo+json`)*.
- "Ponowna walidacja" re-runs validation; an API resource wrongly detected as a web page can be marked "Oznacz zasób jako API".

**Automatic conversion (§5.7)**
- xls/xlsx → csv + json-ld, and csv → json-ld, **only** for files stored in the portal (not remote) that got a table view, and **only the first sheet** of a workbook.
- (The ceny mieszkań page says this was switched off for developers' files on 25.09.2025.)

**Column types (§7)**
- integer, float, string, boolean, date, time, datetime, "dowolny typ" (any type).
- **TERYT codes, postal codes, phone numbers and REGON/NIP/KRS: change the type to text** (otherwise leading zeros disappear). House numbers like `5a` → "dowolny typ".

**Quality check (§8, "Weryfikacja jakości")**
- Available for files uploaded in the panel (xlsx, xls, csv, tsv, ods) that have a table view.
- Rules, one per column: pole numeryczne (numeric), REGON, NIP, KRS, adres uniwersalny, kod PNA, cecha adresu (street prefix), numer telefonu, pole wartości logicznych (boolean).
- Shows at most 5 errors per rule, row numbers counted without the header. This is the portal's only "jakość danych" (data quality) feature; there is no published quality score or report.

**Charts (§9)**
- Need a table view, at least 2 columns, at least one numeric. Defining a default chart is recommended.

**Map (§10)**
- SHP files are mapped automatically. Other files get a map from the "Mapy i wykresy" tab, which needs a table view, using (1) an adres uniwersalny column + a label, or (2) **longitude + latitude + label: "Współrzędne geograficzne są przetwarzane zgodnie z układem odniesienia WGS84. Kolumny zawierające współrzędne geograficzne muszą być typu numerycznego"** (WGS84, numeric columns), or (3) town + postal code + label (street and number optional).

**Common errors (§12, §13)**
- A header of more than one row; merged cells; **line breaks inside a cell (Alt+Enter)**; titles or notes outside the table; aggregating formulas or filters. Merged or blank header cells are the most frequent cause of a failed table view. The panel lists only the first 10 errors.

**Accessibility (§14)**
- Ustawa o dostępności cyfrowej applies. Providers should follow WCAG in the data and in descriptions: mark English text with "Ustaw język" and give logos alt text.

**Personal data (§15)**
- The provider remains the GDPR controller. A DPIA (art. 35) is recommended; sensitive data is not recommended; GDPR conditions are recommended; information duties (arts. 13–14) apply; consult the DPO.

**DGA (§16)**
- Every public-sector body must publish a list of its protected data resources. Misja AED publishes its own as a
  second dataset in `harvester.xml` (see `dane-gov-pl-formats.md`, "List of protected data (DGA)").

---

## 4. Wskazówki dotyczące przygotowania danych do publikacji w portalu (v1.0.1, 10.07.2025; v1.0 for rzeczy znalezione, 15.05.2026)

A short version of POD annex 2 §3.1–3.2 with pictures. Twelve "wymagania techniczne" (technical requirements):

- Publish data "o możliwie najwyższym stopniu otwartości (… XLSX, CSV, JSON)" (as open as possible); "Nie powinno się udostępniać danych w formatach utrudniających maszynowy odczyt, takich jak PDF, JPG, PNG, TIF".
- 1 one header row, headers unique and non-empty; 2 no merged cells; 3 one record per row; 4 no aggregating formulas or filters; 5 nothing outside the table; 6 no formulas pointing outside the file; 7 one kind of data per column; 8 one elementary value per column; 9 consistent format within a column; 10 single sheets recommended.
- **11 (added in v1.0.1): "w komórkach, dla których wypełnienie pozycji jest niemożliwe lub niecelowe należy wstawić znak „X” (Iks), nie należy pozostawiać niewypełnionych (pustych) komórek w arkuszu"** (put `X` in every cell that cannot be filled; leave no empty cells). This goes further than the Standard techniczny, which forbids only completely empty columns and rows. The rzeczy znalezione and ceny mieszkań XML templates declare `<specialSign>X</specialSign>` to match.
- 12 in CSV, quote special characters (commas, newlines inside fields).
- Recommendations: dates `yyyy-mm-dd`; datetimes `yyyy-mm-ddThh:m[m]` or `yyyy-mm-dd hh:mm:ss`; phone 9 digits (`+` prefix allowed); REGON 9/14 digits, NIP 10, KRS 10 (required), no spaces or hyphens.

---

## 5. Harvester: XSD 1.13 and the XML import guides

Sources: the XSD, the general guide v1.02 (doc 225), the developers' instruction 1.0.6 (doc 256), the limit on the
number of resources (doc 268), the ceny mieszkań FAQ and the templates. *(code)* = mcod `harvester/`.

**Source types the portal can harvest** *(code)*: `ckan` (CKAN API), `xml` (XSD 1.13 file), `dcat` (DCAT-AP).
Providers see only the XML route in the knowledge base. A source is created by the portal administrator on request
(`kontakt@dane.gov.pl`: provider name, editors' e-mails, XML and MD5 URLs, frequency). Frequencies in the guide: daily,
weekly, monthly, quarterly. *(code)* `frequency_in_days`. The developers' FAQ: first import when the administrator
switches the source on, then **once a day**. There are no test accounts.

**Checks run when the source is created (general guide §III)**
1. **File name without spaces, ending in `.xml`**; the same name on every update. **Files on standard ports only (80 for http, 443 for https).**
2. A HEAD request; the **`Content-Type` must contain `text/xml` or `application/xml`**.
3. MD5: the **`.md5` file is at the same URL as the XML with `.md5` added** (or `.xml` replaced by `.md5`); the portal computes the hash and compares. **"wielkość liter w hashu ma znaczenie - powinny być to małe litery"** (the hash is case-sensitive and must be lowercase).
4. Validation against the current XSD.

**File content rules**
- The file describes **all** datasets and resources of that source. **Datasets and resources whose `extIdent` disappears from the file are deleted from the portal** (general guide IV, step 4).
- Regenerate the XML + MD5 at the declared frequency.
- **At most 1000 `<resource>` per XML file (recommendation)**; ask for a new source before going over. In a new file define new datasets (no `intIdent`), make titles state the period, and do not duplicate the old source.
- `extIdent` (dataset and resource): **1–36 characters, unique within the file**. MC: "Identyfikator powinien składać się z 36 znaków (rekomendujemy używanie jedynie cyfr i liter, bez znaków diakrytycznych)" (36 characters recommended, digits and letters only, no diacritics). Do not change it: a new `extIdent` means delete + recreate, a new creation date and a new download.
- `intIdent`: the portal id, used to take over a resource created by hand. It takes priority over `extIdent`; use it once only.
- To replace a **local** file, change its `extIdent`. **Remote** files are re-read from the provider.

**XSD 1.13 field constraints** (MUST, enforced by schema validation)

| Element | Rule |
|---|---|
| `dataset/@status`, `resource/@status` | `published` (default) or `draft` |
| `title/polish` | required, 1–300 characters; `title/english` optional (XSD) but required in MC's templates |
| `description/polish` | required, 1–**1000** characters (developers' instruction 1.0.4 changed the limit); `english` optional, 1–1000 |
| `dataset/url` | optional, ≤ 1000 |
| `updateFrequency` | required: `daily`, `weekly`, `monthly`, `quarterly`, `everyHalfYear`, `yearly`, `irregular`, `notPlanned` |
| `categories/category` | ≥ 1 of AGRI, EDUC, ENVI, ENER, TRAN, TECH, ECON, SOCI, **HEAL** (Zdrowie), GOVE, REGI, JUST, INTR |
| `conditions` | optional: `source`, `modification` (booleans, art. 15 ust. 1 pkt 1–2), `responsibilities` (≤ 4000), `dbOrCopyrighted` (≤ 4000), `dbOrCopyrightedLicenseChosen` ∈ {CC0 1.0, CC BY 4.0, CC BY-SA 4.0, CC BY-NC 4.0, CC BY-NC-SA 4.0, CC BY-ND 4.0, CC BY-NC-ND 4.0}, `personalData` (≤ 4000) |
| `resources/resource` | ≥ 1 |
| `tags/tag` | ≥ 1, attribute `lang` = `pl` or `en` required |
| `lastUpdateDate` | `xs:dateTime`, optional |
| `has*` flags | `hasDynamicData`, `hasHighValueData`, `hasHighValueDataFromEuropeanCommissionList`, `hasResearchData` (dataset and resource); `containsProtectedData` (resource); booleans |
| `supplements` | optional, **1–10**; `url` **must match `https://.*`**, ≤ 2000; `name` (title type); `language` pl or en |
| `resource/url` | required, **`https://.*`**, ≤ 2000. "Adres URL zasobu (pliku, API, strony WWW)" (file, API or web page) |
| `availability` | `local` (portal downloads and serves its copy) or `remote` (served from the provider's URL). Developers: `local` |
| `dataDate` | `xs:date`, "dzień, na który przypada aktualność danych" (the day the data is current for); defaults to the import date |
| `specialSigns/specialSign` | from the 5 signs above. Changing them may trigger a new download |
| `isAutoDataDate`, `endlessDataDateUpdate`, `dataDateUpdatePeriod` (daily, weekly, monthly), `autoDataDateStart`, `autoDataDateEnd` | the automatic "dane na dzień" update |
| `regions/terytIdent` | **TERYT codes 2–7 characters** (województwo … gmina/miasto) = "lokalizacja danych" |

---

## 6. Rozporządzenie RM w sprawie portalu danych (Dz.U. 2022 poz. 2415), binding

- §4: data is published as (1) a file stored in the portal, (2) a URL, or (3) a file, URL or metadata **with automated processes** (harvesting).
- **§6.1, dataset metadata entered by the provider:** 1 tytuł (title); **2 słowo kluczowe – minimum jednego** (at least one keyword); 3 opis (description); 4 częstotliwość aktualizacji (update frequency); 5 kategoria (category); 6 warunki ponownego wykorzystywania (re-use conditions, arts. 14–15 of the act); 7 źródło (source URL); 8 logotyp (logo); 9 oznaczenie danych badawczych (research flag); 10 oznaczenie danych dynamicznych (dynamic flag); 11 oznaczenie danych o wysokiej wartości (HVD flag). Items 6–11 only "o ile dotyczą danego zbioru" (where they apply).
- §6.3, added by the portal: identifier, provider, publication date, update date and time.
- **§7.1, resource (ISP) metadata entered by the provider:** 1 tytuł; 2 opis; **3 dane na dzień** (data as of); **4 znaki umowne** (special signs); **5 lokalizacja danych** (by territorial division); **6 język danych** (language). Items 4–5 only where they apply.
- §7.3, added by the portal: identifier, format, publication date, **type (plik / strona internetowa / API: file, web page or API)**, source URL, **"poziom otwartości danych – klasyfikacja ISP na podstawie 5-stopniowej skali, która określa jakość danych"** (the openness level on the 5-star scale is the official "quality" metric).
- §8: for harvested sources the portal adds the import frequency and the source URL, and copies the other §6/§7 metadata from the source system.
- **§10.1: the portal checks automatically** (1) that the metadata is complete (§6 ust. 1 pkt 1–5 and 9–11; §7 ust. 1 pkt 1–3 and 6) and (2) the data formats. **§10.2: the portal monitors whether each URL is reachable** (the public "Uszkodzone linki" list of broken links is refreshed monthly).

---

## 7. Ustawa o otwartych danych i ponownym wykorzystywaniu ISP (Dz.U. 2021 poz. 1641 z późn. zm.)

Rules that bear on publishing (the duties apply to "podmioty zobowiązane", obliged public bodies, art. 3. A private
or civic provider is a "dostawca danych prywatnych", art. 35, to whom arts. 10 ust. 1–3, 12, 13, 32 ust. 4 and 6 apply):

- **Art. 2 pkt 11, "otwarte dane"** (open data): "kompletne, aktualne, w wersji źródłowej, w otwartym i niezastrzeżonym formacie przeznaczonym do odczytu maszynowego… do bezpłatnego ponownego wykorzystywania na tych samych zasadach dla każdego użytkownika, **bez konieczności potwierdzania tożsamości**" (complete, current, in source form, open machine-readable format, free, same terms for all, no identification). Pkt 6 "format otwarty" (open format); pkt 7 "format przeznaczony do odczytu maszynowego" (machine-readable format).
- **Art. 10 ust. 2:** use the formats and protocols of the KRI (art. 18 ustawy o informatyzacji), "jeżeli to możliwe w formacie przeznaczonym do odczytu maszynowego wraz z metadanymi" (machine-readable with metadata, where possible). **Art. 10 ust. 3, API: "zapewnia dostępność, stabilność, jednolitość sposobu korzystania i standardów, łatwość i utrzymanie przez cały cykl użytkowania oraz bezpieczeństwo stosowanego API"** (availability, stability, uniform use and standards, ease of use, maintenance over the whole life cycle, security).
- **Art. 11 ust. 3 and 5:** on the portal, the conditions of re-use are stated with the data; **no stated conditions = re-use without conditions**.
- **Art. 13: "niezwłocznie publikuje… informacje o zaprzestaniu udostępniania lub aktualizowania takich informacji oraz informacje dotyczące dostępności informacji sektora publicznego udostępnianych za pośrednictwem API"** (publish promptly when publication or updating stops, and publish information on API availability).
- Art. 14: re-use is unconditional unless the act says otherwise. Where the provider holds copyright or database rights it **must** set conditions (attribution of the author). Art. 15 ust. 1, optional conditions: (1) cite the source and the time the data was created and obtained; (2) state that the data was processed; (3) the provider's liability; (4) personal data. **Ust. 3: standard open licences may be used.** Art. 16: conditions must be objective, proportionate, non-discriminatory, and must not restrict re-use without reason. Art. 17: free of charge.
- **Art. 24, dane dynamiczne** (dynamic data: frequently or real-time updated, e.g. sensor data): published "niezwłocznie po ich zgromadzeniu; za pośrednictwem API; jeżeli to możliwe – do zbiorczego pobrania" (immediately after collection, through an API, and as a bulk download where possible).
- **Art. 25–26, HVD:** free, machine-readable, API, bulk download where possible. The special regime applies **only** to datasets on the Commission's implementing-act list.
- **Art. 32 ust. 4–6:** formats and protocols follow the KRI; metadata follows the portal regulation; "udostępniają w portalu danych, o ile to możliwe, otwarte dane" (publish open data where possible); **"systematycznie weryfikują, aktualizują oraz podnoszą ich jakość"** (verify, update and improve quality regularly).
- **Art. 34 ust. 4–5:** the minister checks data and metadata against these requirements and calls for prompt correction.

---

## 8. Licences: which one to pick

Sources: Przewodnik §4.1.15, the licence page (doc 14), the XSD, arts. 14–16 of the act.

- **Default and recommendation: no conditions = CC0 1.0** ("Nie wypełniaj zakładki „Warunki”": leave the "Warunki" tab empty).
- CC BY 4.0 ≈ the three basic conditions of art. 15 ust. 1 pkt 1–3; a separate liability clause can be added.
- **"Wybór innej licencji Creative Commons (innej niż CC BY 4.0) dotyczy wyłącznie przypadku opisanego w pkt I.5. Jest to sytuacja wyjątkowa."** (Any other CC licence, CC BY-SA, NC or ND, is only for the exceptional case where the provider holds copyright or database rights and *must* set IP conditions.) Even then, use the Standard prawny analysis to show re-use is not restricted without reason.
- Custom conditions instead of CC: "Nie zalecamy… stosuj takie rozwiązanie w ostateczności" (not recommended, a last resort).
- ODbL is not selectable (XSD enum, `Dataset.LICENSES` *(code)*).
- HVD on the Commission's list: CC0 or CC BY 4.0, or an equivalent or less restrictive licence (Reg. 2023/138 art. 4 ust. 3).

---

## 9. High-value data (HVD) and dynamic data

- KB "Dane o wysokiej wartości": the **provider decides** whether its data meets the statutory definition and may set the flag. "Uznanie… nie rodzi dodatkowych skutków prawnych" (no legal consequences), so general rules apply. The special regime (free, machine-readable, **API**, bulk download, Reg. 2023/138 conditions) applies **only** to the Commission's list. "To Komisja Europejska, a nie dysponent… określa" (the Commission decides) which data is on it, and the flag "HVD z wykazu KE" may be set **only** for those datasets.
- Reg. 2023/138 (for reference): API + terms of use and QoS criteria in human- and machine-readable form; API documentation in an open format; a contact point; the dataset marked as HVD in its metadata; CC0 or CC BY 4.0. The geospatial category covers INSPIRE administrative units, geographical names, addresses, buildings and cadastral parcels (plus reference and agricultural parcels). **AED registers are not in any of the 6 categories**, so for an AED dataset `hasHighValueDataFromEuropeanCommissionList` = **false**; `hasHighValueData` is the provider's own call.
- Dynamic data: the KB examples are environmental, traffic, satellite, meteorological and sensor data. If a dataset is flagged dynamic, art. 24 requires an API. Status that changes rarely (an AED moved or out of service) does not have to be "dynamic"; live readiness telemetry would be.

---

## 10. Accessibility (WCAG) for the provider's own content

- Ustawa z 4.04.2019 o dostępności cyfrowej (Dz.U. 2023 poz. 82, amended by poz. 511): public bodies' websites must meet the annex, i.e. **WCAG 2.1 level AA**, through the Polish Norm implementing EN 301 549 V3.2.1:2021 (clauses 9–11), and publish an accessibility statement ("deklaracja dostępności", art. 10). The 2023 amendment moved the reference from EN 301 549 v2.1.2 to v3.2.1; both are built on WCAG 2.1 ([eli.gov.pl, Dz.U. 2023 poz. 511](https://eli.gov.pl/api/acts/DU/2023/511/text/U/D20230511Lj.pdf), [EC note on EN 301 549](https://digital-strategy.ec.europa.eu/pl/policies/latest-changes-accessibility-standard)). The hackathon brief requires WCAG and responsive design in any case.
- In the portal (Przewodnik §14, LOD report doc 92):
  - mark English fragments in descriptions with "Ustaw język";
  - logo alt text, never just "logo";
  - descriptions: do not repeat the title; put the content first; use "Nagłówek 2" only for subheadings; links with meaningful text (not "tutaj"/"więcej", not a bare URL);
  - **xlsx/docx supplements:** set the document title property; name the sheet; put the data in an Excel *table* with a marked header row; no merged cells; text and fill contrast ≥ 4.5:1; alt text for charts and images; styles, headings and lists in docx; plain language; language declared.

---

## 11. Reference-scope precedents (how MC itself ships a data template)

| | rzeczy znalezione (2026-05) | ceny mieszkań 2025 (archived) | ceny mieszkań 2026-11 (Dz.U. 2026 poz. 1489) |
|---|---|---|---|
| Formats | xlsx + csv | xlsx + csv | **xlsx + csv + xml + json** |
| CSV | UTF-8, no BOM, **comma**, quotes, dates `yyyy-mm-dd`, **`X` in empty cells** | UTF-8, **semicolon**, CRLF | UTF-8 **with BOM**, **semicolon**, CRLF, **decimal comma** (`19,721071`), datetime `yyyy-mm-dd hh:mm:ss`, `X` in empty cells |
| JSON | – | – | `{"oferty_sprzedazy":[{…}]}`, snake_case Polish keys without diacritics, numbers as JSON numbers with a decimal point, datetime `yyyy-mm-ddThh:mm:ss`, postal code as a string `02-776` |
| Address | – | split | split into województwo, powiat, gmina, miejscowość, ulica (with `ul.`), numer nieruchomości, numer lokalu, kod pocztowy; longitude and latitude in separate columns |
| XML template | XSD 1.13, `updateFrequency irregular`, category REGI, `availability local`, `specialSign X`, all `has*` flags explicitly `false` | XSD 1.13, `daily`, ECON, `local`, `X`, `hasHighValueData true` | – |
| Recommendation | – | **one new file per day** ("każdy plik odpowiada jednemu dniowi") | file name pattern `ceny-ofertowe-mieszkan-dewelopera-{firma}-YYYY-MM-DD.{ext}` |

Note: the 2025 and 2026 developer CSVs use a semicolon and a decimal comma, which **contradicts** the Standard
techniczny's recommendations (comma separator, RFC 4180, decimal point). The format there comes from a sector
regulation; for a general dataset the Standard techniczny applies. Follow the Standard, not those CSVs.

---

## 12. Other portal behaviour worth knowing *(code)*

- Upload size limit `RESOURCE_MAX_FILE_SIZE` = 1 GB; the table view and report cover up to 100 000 rows.
- Link checks: HTTPS after redirects, status 200, an allowed Content-Type. **`application/json` without `Content-Disposition: attachment` is classed as an API, not a file.** HEAD first, then GET; 180 s download timeout.
- Column type inference uses the first 5000 rows (75% wins); only the first 1000 rows are validated. **Only declared special signs count as missing values**, so an empty cell in a typed column fails.
- Painless quality rules: `pna` `\d\d-\d\d\d`; `date` `yyyy-mm-dd`; **`datetime` rejects a `+hh:mm` offset**; `phone` 9 digits or `+48` + 9; `bool`; `address_feature` (street prefix in its own column).
- Openness score: JSON that parses as RDF = 4★; linked to ≥ 2 domains = 5★.

---

## Checklist

One line per checkable rule. M = MUST/MUST NOT, S = SHOULD/SHOULD NOT (any deviation explained in the documentation),
R = recommendation outside the standard (portal/MC guidance), C = enforced by portal code. Sources: **ST** = POD annex
2 Standard techniczny, **SA** = POD annex 3 Standard API, **PR** = Przewodnik 1.23, **WS** = Wskazówki v1.0.1, **XG**
= XML guide v1.02, **XD** = XSD 1.13, **XI** = developers' XML instruction 1.0.6, **RP** = portal regulation 2022,
**UD** = act 2021, **LIC** = licence page, **LA** = LOD API report, **LW** = LOD accessibility report, **DC** = ustawa
o dostępności cyfrowej.

### Formats and openness
| # | Rule | Level | Source |
|---|---|---|---|
| F1 | No resource published at level 1 only (PDF/JPG/PNG/TXT as the data) | S | ST §1; WS |
| F2 | Level-3+ data also offered through an API | S | ST §1 |
| F3 | Structured data offered as CSV and/or JSON (recommended level-3 formats) | S | ST §2.10–2.11, table 9 |
| F4 | XLSX not used as the only/main data format (not recommended above 2★; table 9: not allowed at 3★+) | S | ST §2.6, table 9 |
| F5 | TXT used only as a supplement, not as a data resource (TXT counts as 1★) | S | ST §2.3, table 9 |
| F6 | GeoJSON counts as 3★ vector spatial data; follows W3C Spatial Data on the Web Best Practices | S | ST §2.14 |
| F7 | 4★ JSON = JSON-LD with **every** property mapped to a URI; context passed in an HTTP header (Link) | M (for 4★) | ST §5.2 |
| F8 | 5★ = links to other datasets | M (for 5★) | ST §5.2, §7.4 |
| F9 | 4★ CSV = CSVW metadata (W3C tabular data model) | M (for 4★) | ST §4.3 |
| F10 | 4★ XML = XML Namespaces for all elements | M (for 4★) | ST §6.2, table 9 |
| F11 | No xls/xlsx with macros | R | PR §5.1 |
| F12 | File ≤ 1 GB | C | settings |
| F13 | Archives only ZIP (no proprietary extensions), 7z, gzip, bzip2 for 3★+ | M | ST §2.4, table 9 |

### Value formatting (all formats)
| # | Rule | Level | Source |
|---|---|---|---|
| V1 | Numbers, dates, times and booleans correctly formatted | M | ST §3 |
| V2 | Booleans written as `true` / `false` (not T/0/NIE/tak) | S (≤3★), M (4★+ typed) | ST §3, table 5 |
| V3 | Decimal point, no thousands separator | S | ST §3 |
| V4 | Dates `yyyy-mm-dd`; datetimes `yyyy-mm-ddThh:mm` or `yyyy-mm-dd hh:mm:ss` | S | ST §3; WS |
| V5 | Datetimes without a `+hh:mm` offset (portal check) | C | painless/datetime |
| V6 | One value per field, finest granularity | S | ST §3, §3.1.3 |
| V7 | REGON 9/14 digits, NIP 10, KRS 10, no spaces or hyphens | M | ST §3.2 |
| V8 | Phone 9 digits, no spaces or hyphens, `+` prefix allowed | S | ST §3.2 |
| V9 | No leading hyphen or operator-like characters that a spreadsheet may read as a formula | S | ST §3.1.5 |
| V10 | No line breaks inside cells | R | PR §12 |

### Addresses and location
| # | Rule | Level | Source |
|---|---|---|---|
| A1 | Postal address split into separate fields: street, building number, postal code, town (+ flat number) | M | ST §3.3 |
| A2 | Street prefix (`ul.`, `al.`, `pl.`) in its own "cecha" column | S (table 6) / C (address_feature) | ST §3.3; PR §8 |
| A3 | Address names literally as at the source (TERYT ULIC/SIMC) | M | ST §3.3 |
| A4 | Adres uniwersalny column `PNA\|TERC\|SIMC\|SIMC\|ULIC\|x\|y\|nr` | S | ST §3.3 |
| A5 | Postal code `dd-ddd` (portal PNA check) | C | PR §8; painless/pna |
| A6 | Coordinates in WGS84, numeric columns (needed for the portal map) | M (for the map) | PR §10 |
| A7 | Resource "lokalizacja danych" / XML `regions/terytIdent` (2–7 characters) set | M (where it applies) | RP §7.1.5; XD |

### CSV
| # | Rule | Level | Source |
|---|---|---|---|
| C1 | RFC 4180: CRLF, comma separator, quoting | S (3★), M (4★) | ST §4.1 |
| C2 | UTF-8, or the charset declared in `Content-Type` | S (3★), M (4★) | ST §4.1 |
| C3 | Exactly one header row | M | ST §4.2 |
| C4 | No empty or whitespace-only header, no duplicate headers | M | ST §4.2 |
| C5 | Same number of cells in every row | M | ST §4.2 |
| C6 | No completely empty column or row | M | ST §4.2 |
| C7 | Each row stands alone (no blanks meaning "same as above") | M | ST §4.2 |
| C8 | No legend, title or notes rows | M | ST §4.2 |
| C9 | No empty cells: special sign `X` (or another declared sign) | R | WS pt 11 |
| C10 | Every special sign used in the file declared in the resource metadata | M (where it applies) | RP §7.1.4; PR §5.2.12 |
| C11 | Columns holding TERYT, postal codes, phones or REGON set to text in the panel | R | PR §7 |

### Spreadsheets (xlsx field dictionary or any xlsx resource)
| # | Rule | Level | Source |
|---|---|---|---|
| X1 | One header row covering every column | M | ST §3.1.1 |
| X2 | No merged cells | M | ST §3.1.1a; WS |
| X3 | No record spread over several rows | M | ST §3.1.1b |
| X4 | No titles, notes or comments outside the table | M | ST §3.1.1c |
| X5 | No SUM or other aggregating formulas, no filters | M | ST §3.1.1d |
| X6 | No formulas referencing other sheets or files | M | ST §3.1.1e |
| X7 | One data type per column | M | ST §3.1.2 |
| X8 | Single sheet; only the first sheet is converted to csv/json-ld | S | ST §3.1.7; PR §5.7 |
| X9 | Document title set, sheet named, data in an Excel table with a header row, contrast ≥ 4.5:1 | R | LW §2 |

### JSON / API (Standard API)
| # | Rule | Level | Source |
|---|---|---|---|
| P1 | HTTPS only | M | SA §2.13, §11.3 |
| P2 | Open to anonymous users (no mandatory registration or key) | M | SA §11 |
| P3 | JSON responses (RFC 8259); XML optional through `Accept` or `format=` | M | SA §2.8; ST §5.1 |
| P4 | JSON:API message structure (`data`, `links`, `meta`, error objects) | M ("należy przyjąć") | ST §5.1; SA §2, §6 |
| P5 | JSON-LD context in responses | S | SA §6.4 |
| P6 | Version in the path `/api/vN/` | M ("obowiązkowe") | SA §9.3 |
| P7 | `/version` resource | S | SA §9.6 |
| P8 | API on an `api.` subdomain (or the reason documented) | M unless justified | SA §4.1 |
| P9 | Lowercase paths, plural nouns, hyphens, no underscores, no diacritics, no verbs | M/S | SA §3, §4.5 |
| P10 | No file extensions or format names in URIs | M | SA §4.6 |
| P11 | No trailing slash | S | SA §4.4 |
| P12 | HATEOAS links; `links` with `self`, `first`, `prev`, `next`, `last` | M | SA §5, §8 |
| P13 | Filtering `filter[attr]=`, sorting `sort=-a,b`, paging `page` + `limit` | M (filter/sort/fields) | SA §6, §14, annex 4 |
| P14 | Sparse fieldsets `fields=` | M | SA §14.1 |
| P15 | Detailed error objects (`error-result`, `error-reason`, `error-solution`, `error-code`, `error-help`) | M | SA §10, §14.4 |
| P16 | HEAD supported, caching | S | SA §2.3 |
| P17 | Minimal set of HTTP status codes; `429` with the limit policy if limits exist | S | SA §10, §12.14 |
| P18 | No SQL queries; GET only | M | SA §6.6, §10 |
| P19 | Metadata in responses: title, url, provider, datePublished, dateModified (ISO 8601, to the second), description, keywords, temporalCoverage, language, update period, contentType, rights, isPartOf, checksum | S | SA §7, annex 5 |
| P20 | Documentation: resources, methods, parameters, example requests and responses; OpenAPI 3 + Swagger UI | M (contents) / S (OpenAPI) | SA §13 |
| P21 | Simple web query builder usable without code or login | S | SA §1.3.3 |
| P22 | Contact for API questions | S | SA §1.2.14 |
| P23 | Information on API availability and on ending publication/updates published | M (obliged bodies) | UD art. 13 |
| P24 | API resource on the portal marked as type "API" | R | PR §5.6 |
| P25 | API dataset on the portal: description with categories, filter parameters, period and update dates, formats, registration requirements, limits, conditions, **API version, keyword "api"** | R | LA §3.2.1 |
| P26 | API documentation published as a supplement or link | R | LA §3.2.2; PR §4.4 |
| P27 | Example API calls published as resources (CSV recommended) | R | LA §3.2.3 |

### Dataset and resource metadata (portal panel / XML)
| # | Rule | Level | Source |
|---|---|---|---|
| D1 | Dataset title, 1–300 characters, understandable, no date | M / R (no date) | RP §6.1.1; XD; PR §4.1.1 |
| D2 | Dataset description ≥ 20 characters (panel), ≤ 1000 (XSD), expands the title, cites the legal basis | M | PR §4.1.2; XD |
| D3 | ≥ 1 keyword; reuse existing tags; `lang` attribute in XML | M | RP §6.1.2; PR §4.1.13; XD |
| D4 | Update frequency from the enum | M | RP §6.1.4; XD |
| D5 | ≥ 1 category (AED: HEAL) | M | RP §6.1.5; XD |
| D6 | Source URL (provider's page) | M (where it applies) | RP §6.1.7 |
| D7 | Research, dynamic and HVD flags set explicitly | M (where they apply) | RP §6.1.9–11; XI |
| D8 | HVD-KE flag only for datasets on the Reg. 2023/138 list (AED: false) | M | KB HVD-KE |
| D9 | Dataset contains ≥ 1 resource | R / XD | PR §4.1.1; XD |
| D10 | Resource title distinct from the dataset title; dates in titles as `yyyy-mm-dd` | R | PR §5.2.2 |
| D11 | Resource description ≥ 20 characters, ≤ 1000 | M | PR §5.2.3; XD |
| D12 | Resource "dane na dzień" correct; automatic update set for remote, API or link resources that change | M / R | RP §7.1.3; PR §5.2.5 |
| D13 | Resource language set | M | RP §7.1.6 |
| D14 | English title and description (EN) | R | PR §4.2, §5.3; XI (required for developers) |
| D15 | Logo alt text (if a logo is used) | R | PR §4.1.14; LW |
| D16 | English fragments of descriptions marked with "Ustaw język" | R | PR §4.2, §14 |
| D17 | ≤ 10 supplements, https URL, types doc/docx/pdf/txt/odt | M (XD) / C | PR §4.4; XD; code |
| D18 | Resource URLs `https://`, ≤ 2000 characters | M | PR §5.1; XD |

### Licence and conditions
| # | Rule | Level | Source |
|---|---|---|---|
| L1 | Prefer no conditions = CC0 1.0 (leave "Warunki" empty) | R | PR §4.1.15; LIC |
| L2 | CC BY 4.0 if attribution, change notice or liability terms are needed | R | LIC |
| L3 | CC BY-SA / NC / ND only when the provider holds IP or database rights and must set conditions; justify it | R (exceptional) | LIC pt I.5, II |
| L4 | Only CC0 1.0, CC BY(-SA/-NC/-ND…) 4.0 selectable; no ODbL | C / XD | XSD enum |
| L5 | Conditions objective, proportionate, not restricting re-use without reason | M | UD art. 16 |
| L6 | Conditions stated with the data on the portal (absence = no conditions) | M | UD art. 11 ust. 3, 5 |
| L7 | Personal data: DPIA, GDPR conditions, information duties | R / M (GDPR) | PR §15 |

### Harvester XML source
| # | Rule | Level | Source |
|---|---|---|---|
| H1 | Valid against `otwarte_dane_latest.xsd` (`urn:otwarte-dane:harvester:1.13`) | M | XG §III.4 |
| H2 | File name without spaces, ending `.xml`, stable | M | XG §III.1 |
| H3 | Standard port (443 for https) | M | XG §III.1 |
| H4 | HEAD returns `Content-Type` containing `text/xml` or `application/xml` | M | XG §III.2 |
| H5 | `.md5` at the same URL + `.md5`; lowercase hex; matches the file | M | XG §III.3 |
| H6 | XML and MD5 regenerated at the declared frequency | M | XG §IV.3 |
| H7 | `extIdent` 1–36 characters, unique in the file, stable (a change = delete + recreate); 36 alphanumeric characters recommended | M / R | XD; XI; FAQ |
| H8 | Every published dataset or resource present in each file (missing = deleted) | M | XG §IV.4 |
| H9 | ≤ 1000 `<resource>` per file | R | doc 268 |
| H10 | `availability` chosen deliberately (local = portal copy + conversion; remote = served from the provider) | R | XI; PR §5.7 |
| H11 | `specialSigns` declared when the files use them | M (where it applies) | XI; RP §7.1.4 |
| H12 | All `has*` flags and `containsProtectedData` explicitly false or true | R | XI; templates |

### Publishing practice
| # | Rule | Level | Source |
|---|---|---|---|
| G1 | Resources versioned (new file at a new URL) instead of overwritten; stable URL per file | S | ST §9 |
| G2 | Permanent availability of every published resource | S | ST §9 |
| G3 | Data kept current and quality improved regularly | M (obliged bodies) | UD art. 32 ust. 6 |
| G4 | Dynamic data → API, published promptly, bulk download if possible | M (if flagged dynamic) | UD art. 24 |
| G5 | Links reachable (monitored; listed monthly as "Uszkodzone linki" if broken) | M | RP §10.2 |
| G6 | `application/json` exports sent with `Content-Disposition: attachment` so they count as files, not APIs | C | link_validation |
| G7 | Publisher's own web service meets WCAG 2.1 AA (EN 301 549 V3.2.1) and has an accessibility statement | M (public bodies) | DC |
| G8 | Deviations from "zaleca się" rules explained in the dataset or API documentation | M | ST §1 |
