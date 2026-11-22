"""The merged dataset in machine-readable formats (dane.gov.pl): GeoJSON, CSV, JSON, JSON-LD, plus the reference
scope (wzorcowy zakres danych) as XLSX, CSV template and TXT dictionary, dane.gov.pl-shaped dataset metadata and the
harvester XML the portal imports automatically. Each is built once per data version and served from Redis; a copy of
the files is written to var/exports/."""

import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime

from django.conf import settings
from django.utils import timezone

from integrations.connectors.common import to_floor

from .cache import cached, data_version
from .dga import build_dga_xlsx
from .models import Device
from .reference_scope import build_reference_txt, build_reference_xlsx, build_template_csv, build_template_xlsx
from .schema import (
    LIST_FIELDS,
    PUBLISHED_FIELDS,
    list_columns,
)

CONTENT_TYPES = {
    "geojson": "application/geo+json",
    "json": "application/json",
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain; charset=utf-8",
    "notes": "text/plain; charset=utf-8",
    "jsonld": "application/ld+json",
    "xml": "application/xml; charset=utf-8",
    "template_csv": "text/csv; charset=utf-8",
    "template_xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "sources_csv": "text/csv; charset=utf-8",
    # no parameters: dane.gov.pl tells a protected-data list's format by mimetypes.guess_extension(Content-Type)
    "dga_xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ATTRIBUTION = (
    "Zawiera dane z OpenStreetMap (© OpenStreetMap contributors, ODbL 1.0) oraz z otwartych danych samorządów "
    "(CC0 1.0 / CC BY 4.0). Lista źródeł: /api/sources."
)


def attribution(base_url: str = "") -> str:
    """ATTRIBUTION with an absolute link to the source list: the text travels inside downloaded files."""
    base = (base_url or settings.PUBLIC_BASE_URL or "").rstrip("/")
    return ATTRIBUTION.replace("/api/sources", base + "/api/sources") if base else ATTRIBUTION


def _value(value):
    if isinstance(value, datetime):
        return utc_iso(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def utc_iso(value: datetime) -> str:
    """yyyy-mm-ddThh:mm:ssZ: the dane.gov.pl datetime check accepts a trailing Z but no +01:00 offset."""
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _csv_cell(value):
    """CSV spells booleans as the schema does (true/false), not Python's True/False; None stays an empty cell."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def rows():
    for device in Device.objects.filter(active=True).order_by("id").iterator(chunk_size=2000):
        row = {field: _value(getattr(device, field)) for field in PUBLISHED_FIELDS}
        row["sources"] = device.sources
        row["floor"] = to_floor(device.floor)  # devices merged before floors were normalised
        yield row


def json_lines(head: dict, key: str, items) -> bytes:
    """`head` plus `key: [items]` as JSON with one item per line. The same document as json.dumps, but a 20 MB file on
    one line makes dane.gov.pl hang: libmagic calls it text/plain, the portal then tries every RDF parser on it, and
    rdflib's N-Triples parser is quadratic in the line length."""
    opening = json.dumps(head, ensure_ascii=False)[:-1] + (", " if head else "") + json.dumps(key) + ": ["
    lines = ",\n".join(json.dumps(item, ensure_ascii=False) for item in items)
    return f"{opening}\n{lines}\n]}}\n".encode()


def build(fmt: str, base_url: str = "") -> bytes:
    meta = {
        "generated_at": timezone.now().isoformat(),
        "data_version": data_version(),
        "attribution": attribution(base_url),
    }
    if fmt == "geojson":
        features = []
        for row in rows():
            lon, lat = row["lon"], row["lat"]
            features.append(
                {
                    "type": "Feature",
                    "id": row["id"],
                    "geometry": {"type": "Point", "coordinates": [round(lon, 7), round(lat, 7)]},
                    "properties": {k: v for k, v in row.items() if k not in {"lat", "lon"}},
                }
            )
        return json_lines({"type": "FeatureCollection", "metadata": meta}, "features", features)
    if fmt == "json":
        return json_lines({"metadata": meta, "fields": PUBLISHED_FIELDS}, "items", rows())
    if fmt == "csv":
        return build_csv()
    if fmt == "sources_csv":
        return build_sources_csv()
    if fmt == "xlsx":
        return build_reference_xlsx()
    if fmt == "template_csv":
        return build_template_csv()
    if fmt == "template_xlsx":
        return build_template_xlsx()
    if fmt == "txt":
        return build_reference_txt()
    if fmt == "dga_xlsx":
        return build_dga_xlsx()
    if fmt == "jsonld":
        return build_jsonld(base_url)
    if fmt == "notes":
        return build_notes_txt(base_url)
    raise ValueError(fmt)


# How the dataset meets the dane.gov.pl standards, and the only two places it cannot. The Standard techniczny (annex 2
# to the Programme for opening data 2021-2027) asks for a justification of every "zaleca się" rule a publisher does
# not follow; this is it, published as a TXT supplement next to the field dictionary.
NOTES_TXT = """Defibrylatory AED w Polsce — informacje o zbiorze

Dokument uzupełniający do zbioru. Opisuje, jak zbiór realizuje Standard techniczny i Standard API portalu dane.gov.pl
(załączniki 2 i 3 do Programu otwierania danych publicznych 2021–2027), i uzasadnia jedyne dwa odstępstwa od zaleceń.

ODSTĘPSTWA

1. Licencja CC BY-SA 4.0 zamiast zalecanej CC0 1.0
   Około 96% rekordów pochodzi z OpenStreetMap, udostępnianego na licencji ODbL 1.0 z warunkiem uznania autorstwa
   i udostępniania na tych samych warunkach. Portal nie oferuje ODbL, a CC0 lub CC BY zniosłyby te warunki, czego nie
   wolno nam zrobić. CC BY-SA 4.0 to licencja z listy portalu najbliższa ODbL. Część z OpenStreetMap pozostaje objęta
   ODbL 1.0: korzystając z niej, należy podać „© OpenStreetMap contributors” i udostępniać zmienioną bazę na tych samych
   warunkach. Dane samorządów pochodzą ze zbiorów na CC0 1.0 lub CC BY 4.0. Dane, które dysponenci przekazują
   bezpośrednio, mogą zostać opublikowane osobno na CC0 1.0.
   Lista źródeł, wydawców i licencji: {base}/api/sources

2. API w domenie serwisu zamiast w subdomenie api.
   API działa pod adresem {base}/api/v1, bo wdrożenie ma jedną domenę publiczną. Wszystkie odnośniki w odpowiedziach
   są budowane z jednego ustawienia, więc przeniesienie do subdomeny api. nie zmienia API.

JAK ZBIÓR REALIZUJE STANDARD

3. Jedna wartość w komórce
   Adres jest w osobnych kolumnach: street_type (cecha według TERYT), street, house_number, postal_code, city, teryt.
   Warunki dostępu to osobne kolumny true/false (access_conditions_…), po jednej na każdy warunek. Źródła rekordu
   są w osobnym zasobie „Powiązania defibrylatorów z rekordami źródeł” (jeden wiersz na parę aed_id, source).
   W JSON, GeoJSON i API listy pozostają listami. Wartość opening_hours to jedna wartość w składni opening_hours
   z OpenStreetMap: średnik należy do tej składni.

4. Brak danych
   Każda pusta komórka CSV zawiera znak umowny „.” (zupełny brak informacji), zadeklarowany przy zasobie. Plik CSV
   pomija kolumny, których nie wypełnia żaden rekord (Standard nie dopuszcza całkowicie pustych kolumn). Pełny zestaw
   kolumn jest w szablonie XLSX i w metadanych CSVW: {base}/api/export/aeds.csv-metadata.json

5. Wersjonowanie
   Każdy dzień danych ma własny adres, który się nie zmienia, a poprzednie wersje pozostają dostępne:
   {base}/api/export/archiwum/RRRR-MM-DD/aeds.csv (lista wersji: {base}/api/export/archiwum). Portal dostaje
   w harvester.xml adres wersji z danego dnia. Stałe adresy /api/export/aeds.csv itd. zawsze wskazują najnowsze dane,
   dla aplikacji.

6. Adres i kody terytorialne
   Kod TERYT gminy, a w miastach miejscowość, ustalamy ze współrzędnych i Państwowego Rejestru Granic tylko wtedy,
   gdy wynik jest pewny. W Warszawie cechę ulicy bierzemy z miejskiego rejestru adresów. Ulicy, numeru ani kodu
   pocztowego nie zgadujemy, dlatego adres ma około 5% rekordów. AED nie ma numeru lokalu: dokładne miejsce opisują
   location_detail i floor.

7. Dane osobowe
   Nie publikujemy telefonów ani adresów e-mail osób. Pole operator_name to nazwa instytucji. operator_contact
   zawiera tylko kontakt instytucjonalny, jeśli przekazał go dysponent. Dane, których nie publikujemy (zgłoszenia
   z formularza, pełne pliki dysponentów, surowe pobrania źródeł), wymienia wykaz chronionych danych:
   {base}/api/export/wykaz-chronionych-danych.xlsx. Portal dane.gov.pl co noc przenosi go do zbiorczego wykazu
   chronionych danych; dostęp do tych danych jest możliwy na wniosek.

8. Dane wywnioskowane
   Część wartości (umiejscowienie, piętro, godziny dostępności, warunki dostępu, sezonowość) pochodzi z opisu
   tekstowego w źródle, odczytanego przez model językowy. Taka wartość jest używana tylko wtedy, gdy żadne źródło nie
   podaje pola wprost, i ma najniższy priorytet. Pochodzenie każdego pola (źródło i metoda: source, geocoded,
   inferred) pokazuje API: {base}/api/devices/{{id}} (pole field_sources).

9. API
   {base}/api/v1/aeds: wersja w ścieżce, struktura JSON:API z odnośnikami self, first, prev, next i last,
   filtrowanie filter[…], sortowanie sort, wybór pól fields, stronicowanie page i limit, błędy w formacie Standardu
   API (error-result, error-reason, error-code, error-help), zasób /api/v1/version, dokumentacja OpenAPI 3:
   {base}/api/v1/docs

10. Formaty
    CSV według RFC 4180 (UTF-8, przecinek, CRLF) z metadanymi CSVW. GeoJSON w EPSG:4326 (WGS84), kolejność
    [długość, szerokość], zgodnie z RFC 7946. JSON-LD w słowniku schema.org z odnośnikami do OpenStreetMap. Mapę na
    portalu buduje się z zasobu CSV (kolumny lat i lon).
"""


def build_notes_txt(base_url: str = "") -> bytes:
    base = (base_url or settings.PUBLIC_BASE_URL or "").rstrip("/")
    return NOTES_TXT.format(base=base).encode()


# dane.gov.pl special sign (znak umowny) "." — "zupełny brak informacji". The portal reads only declared special signs
# as missing (an empty cell in a typed column fails its table validation), and its guide for publishers asks for no
# empty cells at all, so every cell the data leaves empty holds it.
NO_DATA = "."
# Columns that hold several values in JSON go to the CSV as one boolean column per allowed value
CSV_LIST_COLUMNS = {field: list_columns(field) for field in LIST_FIELDS}
# Left out of the CSV: which sources a record merges is a list, published one pair per row in aeds-sources.csv
CSV_EXCLUDED = {"sources"}


def csv_columns() -> list[str]:
    """Every column the CSV can have, in schema order (a list field replaced by its boolean columns)."""
    columns = []
    for field in PUBLISHED_FIELDS:
        if field in CSV_EXCLUDED:
            continue
        columns += [name for name, _, _ in CSV_LIST_COLUMNS[field]] if field in CSV_LIST_COLUMNS else [field]
    return columns


def build_csv() -> bytes:
    """One row per device, one elementary value per cell. Columns follow the schema order, but a column no record
    fills yet is left out: the Standard techniczny (§4) allows no completely empty column. It appears as soon as any
    data holder provides the field; the full column set is the reference scope (schema.xlsx). A list field becomes one
    true/false column per allowed value. Coordinates have 6 decimals (about 10 cm): with 7, a value like 49.5878956
    is 10 characters long and the portal's type guesser takes it for a date. Every empty cell is "."."""
    table = []
    for row in rows():
        for field, columns in CSV_LIST_COLUMNS.items():
            values = row.pop(field, None)
            for name, _, value in columns:
                row[name] = None if values is None else value in values
        row["lat"], row["lon"] = f"{row['lat']:.6f}", f"{row['lon']:.6f}"
        table.append({k: _csv_cell(v) for k, v in row.items()})
    filled = {k for row in table for k, v in row.items() if v not in (None, "", NO_DATA)}
    fields = [f for f in csv_columns() if f in filled] if table else csv_columns()
    for row in table:
        for f in fields:
            if row[f] in (None, ""):
                row[f] = NO_DATA
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(table)
    return ("\ufeff" + buffer.getvalue()).encode()  # BOM so Excel reads UTF-8


def build_sources_csv() -> bytes:
    """Which source records each AED merges: one (AED, source, the source's own record id, its public page) per row,
    instead of a list in one cell. The relation is many-to-many, so it gets its own table, joined on aed_id."""
    from integrations.connectors import REGISTRY
    from integrations.models import SourceRecord

    records = (
        SourceRecord.objects.filter(device__active=True, device__isnull=False, removed_at__isnull=True)
        .values_list("device_id", "integration__slug", "integration__connector", "source_record_id")
        .order_by("device_id", "-integration__priority", "integration__slug", "source_record_id")
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["aed_id", "source", "source_record_id", "source_record_url"])
    for device_id, slug, connector, record_id in records.iterator(chunk_size=5000):
        cls = REGISTRY.get(connector)
        url = cls.record_url(record_id) if cls is not None and cls.record_url_template else None
        writer.writerow([device_id, slug, record_id, url or NO_DATA])
    return ("\ufeff" + buffer.getvalue()).encode()


# schema.org JSON-LD: an RDF graph whose URIs span several domains (our records, OpenStreetMap, the licence), which is
# what dane.gov.pl scores 5★ (resources/score_computation in the portal code). The context is inline, so parsing it
# needs no network.
JSONLD_CONTEXT = {
    "@vocab": "https://schema.org/",
    "sameAs": {"@type": "@id"},
    "additionalType": {"@type": "@id"},
    "license": {"@type": "@id"},
    "url": {"@type": "@id"},
    "isBasedOn": {"@type": "@id"},
}
AED_TYPE = "https://wiki.openstreetmap.org/wiki/Tag:emergency%3Ddefibrillator"


def _source_urls() -> dict[str, list[str]]:
    """Device id → the public pages of its records at their sources (e.g. the OpenStreetMap object), from every
    connector that declares `record_url_template`."""
    from integrations.connectors import REGISTRY
    from integrations.models import SourceRecord

    linked = {key: cls for key, cls in REGISTRY.items() if cls.record_url_template}
    urls: dict[str, list[str]] = {}
    records = SourceRecord.objects.filter(
        integration__connector__in=linked, device__isnull=False, removed_at__isnull=True
    ).values_list("device_id", "integration__connector", "source_record_id")
    for device_id, connector, record_id in records.order_by("device_id", "pk").iterator(chunk_size=5000):
        urls.setdefault(device_id, []).append(linked[connector].record_url(record_id))
    return urls


def build_jsonld(base_url: str) -> bytes:
    base_url = base_url.rstrip("/")
    same_as = _source_urls()
    graph = [
        {
            "@id": base_url + JSONLD_PATH,
            "@type": "Dataset",
            "name": DATASET["title"],
            "description": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", DATASET["notes"])).strip(),
            "keywords": DATASET["keywords"],
            "inLanguage": "pl",
            "license": PORTAL_LICENSES.get(settings.DATASET_LICENSE, DATASET["license_url"]),
            "creditText": attribution(base_url),
            "isBasedOn": ["https://www.openstreetmap.org/copyright"],
            "dateModified": _data_date().isoformat(),
            "spatialCoverage": {"@type": "Country", "name": "Polska", "identifier": "PL"},
        }
    ]
    for device in Device.objects.filter(active=True).order_by("id").iterator(chunk_size=2000):
        place = {
            "@id": f"{base_url}/api/devices/{device.id}",
            "@type": "Place",
            "additionalType": AED_TYPE,
            "identifier": device.id,
            "name": device.building_name or "AED",
            "geo": {"@type": "GeoCoordinates", "latitude": round(device.lat, 7), "longitude": round(device.lon, 7)},
        }
        if device.location_detail:
            place["description"] = device.location_detail
        address = {
            "streetAddress": device.address,
            "postalCode": device.postal_code,
            "addressLocality": device.city,
        }
        if any(address.values()):
            place["address"] = {"@type": "PostalAddress", "addressCountry": "PL"} | {
                k: v for k, v in address.items() if v
            }
        if device.opening_hours:
            place["openingHours"] = device.opening_hours  # OSM opening_hours syntax
        if device.access in {"public", "private"}:
            place["publicAccess"] = device.access == "public"
        if device.photo_url:
            place["photo"] = device.photo_url
        if same_as.get(device.id):
            place["sameAs"] = same_as[device.id]
        graph.append(place)
    return json_lines({"@context": JSONLD_CONTEXT}, "@graph", graph)


# Part of every export cache key. The cache is keyed by data version, which only a sync or an edit bumps, so a deploy
# that changes what the files contain must bump this too, or the old files are served until the next sync.
EXPORT_REVISION = 7
# Exports whose content holds absolute links (JSON-LD @ids, the attribution's source list, the notes' URLs)
BASE_URL_FORMATS = {"jsonld", "geojson", "json", "notes"}


def get_export(fmt: str, base_url: str = "") -> tuple[bytes, str]:
    """(content, etag) for the current data version, per origin for the formats that embed absolute links."""
    key = f"export{EXPORT_REVISION}:{fmt}" + (f":{base_url.rstrip('/')}" if fmt in BASE_URL_FORMATS else "")
    content = cached(key, lambda: build(fmt, base_url), timeout=None)
    return content, hashlib.md5(content).hexdigest()  # noqa: S324 — an ETag, not security


# ------------------------------------------------------------ dane.gov.pl dataset metadata
#
# Mirrors how dane.gov.pl describes a dataset and its resources (API 1.4 `dataset` / `resource` attributes and the
# codes its models store), so the values can be pasted into the publisher panel, each resource registered by link to
# our stable export URL, or the whole dataset imported by the portal's harvester from /api/export/harvester.xml.

# Licences dane.gov.pl offers for a database (harvester XSD `dbOrCopyrightedLicenseChosen`); ODbL is not among them.
PORTAL_LICENSES = {
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}
# The portal's yes/no flags. AED locations are not on the EC high-value list, not research data, and a daily registry
# is not "dynamic data" in the Open Data Directive's sense (sensor-like, real-time).
FLAGS = {
    "has_dynamic_data": False,
    "has_high_value_data": False,
    "has_high_value_data_from_ec_list": False,
    "has_research_data": False,
}
# "Dane na dzień" moves forward on its own every day (the panel's "automatyczna aktualizacja").
AUTO_DATA_DATE = {"is_auto_data_date": True, "data_date_update_period": "daily", "endless_data_date_update": True}

DATASET = {
    "title": "Defibrylatory AED w Polsce — zbiór ogólnokrajowy",
    "notes": (
        "<p>Ogólnopolski wykaz automatycznych defibrylatorów zewnętrznych (AED): położenie, dostępność, godziny "
        "otwarcia i stan gotowości urządzenia. Zbiór łączy dane z wielu źródeł (dysponenci, samorządy, "
        "OpenStreetMap) w jeden rekord na urządzenie według wzorcowego zakresu danych.</p>"
        "<p>Pola opisuje słownik (zasób XLSX i dokument TXT). Wartość pusta oznacza brak danych — nie jest zgadywana (w CSV "
        "w kolumnach liczbowych, datach i kodach: znak umowny „.”). Pole "
        "<code>sources</code> wskazuje źródła, z których scalono rekord. Zgodność ze standardami portalu i "
        "wybór licencji opisuje dokument „Informacje o zbiorze”.</p>"
    ),
    "keywords": [
        "AED",
        "defibrylator",
        "automatyczny defibrylator zewnętrzny",
        "pierwsza pomoc",
        "ratownictwo",
        "nagłe zatrzymanie krążenia",
        "Misja AED",
    ],
    # EU data theme codes, as dane.gov.pl lists them
    "categories": [{"code": "HEAL", "title": "Zdrowie"}, {"code": "REGI", "title": "Regiony i miasta"}],
    # dane.gov.pl code (daily, weekly, monthly, quarterly, everyHalfYear, yearly, irregular, notPlanned)
    "update_frequency": "daily",
    "update_frequency_label": "Codziennie",
    "regions": [{"name": "Polska"}],
    "language": "pl",
    # The portal offers only CC licences; CC BY-SA 4.0 is closest to the ODbL (attribution + share-alike) of the
    # OpenStreetMap part, whose attribution goes into the licence conditions. DATASET_LICENSE can override it.
    "license_name": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "license_condition_custom_description": ATTRIBUTION,
    "contains_protected_data": False,
} | FLAGS

# English title and description for the harvester XML (dane.gov.pl shows both languages)
DATASET_EN = {
    "title": "AED defibrillators in Poland — nationwide dataset",
    "description": (
        "Nationwide register of automated external defibrillators (AED): location, accessibility, opening hours and "
        "device readiness. Merged from operators, municipalities and OpenStreetMap into one record per device using "
        "the reference data scope. An empty value means no data."
    ),
    "keywords": ["AED", "defibrillator", "first aid", "emergency", "sudden cardiac arrest"],
}

# (format, path, title, description, openness score as dane.gov.pl rates the format)
RESOURCES = [
    (
        "csv",
        "/api/export/aeds.csv",
        "Defibrylatory AED w Polsce (CSV)",
        "Jeden wiersz na urządzenie, kolumny według wzorcowego zakresu danych, w jego kolejności, jedna wartość w "
        "komórce. UTF-8 (z BOM), separator przecinek, daty ISO 8601 (data i czas w UTC z literą Z), wartości logiczne "
        "true/false, współrzędne WGS84 z 6 miejscami po przecinku, piętro jako liczba całkowita. Adres w osobnych "
        "kolumnach (cecha, ulica, numer budynku, kod pocztowy, miejscowość, TERYT). Warunki dostępu jako osobne kolumny "
        "true/false, po jednej na każdy warunek. Każda pusta komórka zawiera znak umowny „.” (zupełny brak "
        "informacji). Źródła rekordów są w osobnym zasobie (powiązania z rekordami źródeł). Plik zawiera tylko "
        "kolumny, które wypełnia co najmniej jeden rekord: pozostałe pola (głównie dane serwisowe dysponentów) pojawią "
        "się, gdy poda je którykolwiek dysponent. Pełny zestaw kolumn opisuje wzorcowy zakres danych (zasób XLSX) "
        "i metadane CSVW: /api/export/aeds.csv-metadata.json.",
        3,
    ),
    (
        "sources_csv",
        "/api/export/aeds-sources.csv",
        "Powiązania defibrylatorów z rekordami źródeł (CSV)",
        "Z których rekordów źródłowych powstał każdy defibrylator: jeden wiersz na parę (aed_id, source), "
        "z identyfikatorem rekordu w źródle i adresem jego strony (np. obiekt w OpenStreetMap). Łączy się z zasobem "
        "głównym przez aed_id = id. Opis źródeł, wydawców i licencji: /api/sources. Brak adresu strony: znak umowny "
        "„.”.",
        3,
    ),
    (
        "geojson",
        "/api/export/aeds.geojson",
        "Defibrylatory AED w Polsce (GeoJSON)",
        "FeatureCollection punktów w EPSG:4326 (kolejność [lon, lat]); atrybuty jak w CSV, źródła jako lista.",
        3,
    ),
    (
        "json",
        "/api/export/aeds.json",
        "Defibrylatory AED w Polsce (JSON)",
        "Obiekt {metadata, fields, items}; jeden element items na urządzenie, pola według wzorcowego zakresu danych.",
        3,
    ),
    (
        "jsonld",
        "/api/export/aeds.jsonld",
        "Defibrylatory AED w Polsce (JSON-LD)",
        "Dane powiązane w słowniku schema.org: każde AED jako Place z adresem URI, współrzędnymi (GeoCoordinates), "
        "adresem, godzinami otwarcia i odnośnikiem sameAs do obiektu w OpenStreetMap.",
        5,
    ),
    (
        "api",
        "/api/v1/aeds",
        "API — Defibrylatory AED w Polsce (api, wersja 1)",
        "Interfejs API w wersji 1 zgodny ze Standardem API (załącznik 3 do Programu otwierania danych): struktura "
        "JSON:API, filtrowanie filter[teryt|city|access|readiness|source|updated_since|bbox], sortowanie sort, wybór "
        "pól fields, stronicowanie page i limit z linkami. Dokumentacja OpenAPI 3: /api/v1/docs. Przykład: "
        "/api/v1/aeds?filter[teryt]=1465&filter[access]=public&sort=-updated_at&limit=20",
        3,
    ),
    # A resource, not a supplement: the portal takes supplements only as doc/docx/pdf/txt/odt. One sheet, as the
    # Standard techniczny recommends for spreadsheets (the portal converts only the first sheet anyway); the workbook
    # with the field dictionary stays on our page at /api/export/schema.xlsx.
    (
        "template_xlsx",
        "/api/export/schema-template.xlsx",
        "Wzorcowy zakres danych AED (XLSX)",
        "Szablon dla dysponentów AED: jeden arkusz „Wzorcowy zakres danych” z tabelą Excel, polskimi nagłówkami "
        "wszystkich kolumn zbioru i trzema wierszami przykładowymi (dane fikcyjne, identyfikatory PRZYKLAD-…). Opis "
        "pól (typ, format, poziom 1 podstawowy / 2 rozszerzony / 3 pełny, czy wymagane, dozwolone wartości) jest "
        "w dokumencie „Słownik pól” (TXT). Ten sam szablon w CSV: /api/export/schema-template.csv; skoroszyt ze "
        "słownikiem i instrukcją: /api/export/schema.xlsx.",
        2,
    ),
]

SUPPLEMENTS = [
    (
        "txt",
        "/api/export/schema.txt",
        "Słownik pól — wzorcowy zakres danych AED (TXT)",
        "Opis każdej kolumny: nazwa, opis, typ, format, poziom, czy wymagane, dozwolone wartości i przykład.",
    ),
    (
        "notes",
        "/api/export/notes.txt",
        "Informacje o zbiorze (TXT)",
        "Jak zbiór realizuje Standard techniczny i Standard API dane.gov.pl (jedna wartość w komórce, brak danych, "
        "wersjonowanie, adres, dane osobowe, dane wywnioskowane, API, formaty) i uzasadnienie dwóch odstępstw: "
        "licencji CC BY-SA 4.0 i adresu API.",
    ),
]

# Our list of protected data (devices/dga.py) as a dataset of its own, as institutions publish it on dane.gov.pl: the
# portal copies every such resource into its nationwide table „Wykaz chronionych danych” each night.
DGA_EXT_IDENT = "misja-aed-dga"
DGA_PATH = "/api/export/wykaz-chronionych-danych.xlsx"
DGA_DATASET = {
    "title": "Wykaz zasobów chronionych danych — Misja AED",
    "notes": (
        "Wykaz zasobów chronionych danych (Akt o zarządzaniu danymi, art. 8): danych, które Misja AED przechowuje, "
        "ale nie publikuje, bo są danymi osobowymi albo są objęte prawami podmiotów trzecich. Wykaz powstaje "
        "automatycznie z bazy danych przy każdej aktualizacji zbioru, a portal co noc przenosi go do zbiorczego "
        "wykazu chronionych danych. Dostęp do wymienionych danych jest możliwy wyłącznie na wniosek; warunki "
        "ponownego wykorzystywania zostaną określone indywidualnie w ofercie. Format i rozmiar danych mogą ulec "
        "zmianie. Jak złożyć wniosek: https://dane.gov.pl/pl/dga/information"
    ),
    "notes_en": (
        "List of protected data resources (Data Governance Act, Art. 8): data Misja AED holds but does not publish "
        "because it is personal data or covered by third-party rights. Generated from the database on every update; "
        "the portal copies it into the nationwide list every night. Access only on request, with re-use conditions "
        "set individually in the offer."
    ),
    "keywords": ["DGA", "chronione dane", "wykaz chronionych danych", "AED", "Misja AED"],
    "keywords_en": ["DGA", "protected data", "AED"],
    "categories": [{"code": "GOVE", "title": "Rząd i sektor publiczny"}],
    "update_frequency": "daily",
}
DGA_RESOURCE = (
    "dga_xlsx",
    DGA_PATH,
    "Wykaz chronionych danych",
    "Jeden wiersz na zasób chronionych danych: Lp., Zasób chronionych danych, Format danych, Rozmiar danych, Warunki "
    "ponownego wykorzystywania. Rozmiary liczone z bazy danych przy każdej aktualizacji.",
    2,
)
DGA_ENGLISH = (
    "List of protected data",
    "One row per protected data resource: no., resource, data format, data size, re-use conditions. Sizes are counted "
    "from the database on every update.",
)

# The file format the portal sees, for exports whose internal name is not one
FILE_FORMATS = {"notes": "txt", "sources_csv": "csv", "template_xlsx": "xlsx", "dga_xlsx": "xlsx"}
# extIdent suffixes the portal already knows: changing one deletes and recreates the resource there
EXT_IDENT_SUFFIX = {"template_xlsx": "xlsx", "dga_xlsx": "xlsx"}

# Special signs (znaki umowne) each resource uses, as the portal's XSD codes them ("." = zupełny brak informacji)
SPECIAL_SIGNS = {"csv": [NO_DATA], "sources_csv": [NO_DATA]}

# English (title, description) for the harvester XML, by format
ENGLISH = {
    "csv": (
        "AED defibrillators in Poland (CSV)",
        "One row per device, columns as in the reference data scope and in its order, one value per cell. UTF-8 with "
        "BOM, comma separator, ISO 8601 dates (datetimes in UTC with a Z), true/false booleans, WGS84 coordinates with "
        "6 decimals, floor as a whole number. Address in separate columns; access conditions as one true/false column "
        'each. Every empty cell holds the special sign "." (no information). Record sources are a separate resource. '
        "Only columns at least one record fills are included; the full column set is the reference data scope (XLSX) "
        "and the CSVW metadata.",
    ),
    "sources_csv": (
        "AED defibrillators and their source records (CSV)",
        "Which source records each AED merges: one (aed_id, source) pair per row, with the record id at the source "
        "and its public page. Joins the main resource on aed_id = id.",
    ),
    "geojson": (
        "AED defibrillators in Poland (GeoJSON)",
        "FeatureCollection of points in EPSG:4326 ([lon, lat]); attributes as in the CSV, sources as a list.",
    ),
    "json": (
        "AED defibrillators in Poland (JSON)",
        "Object {metadata, fields, items}; one item per device, fields as in the reference data scope.",
    ),
    "jsonld": (
        "AED defibrillators in Poland (JSON-LD)",
        "Linked data in the schema.org vocabulary: every AED as a Place with a URI, GeoCoordinates, address, opening "
        "hours and a sameAs link to its OpenStreetMap object.",
    ),
    "template_xlsx": (
        "AED reference data scope (XLSX)",
        "Template for AED operators: one sheet with an Excel table, Polish headers for every column of the dataset "
        "and three example rows (fictional data, ids PRZYKLAD-…). The fields are described in the field dictionary "
        "(TXT). The same template as CSV: /api/export/schema-template.csv.",
    ),
    "txt": (
        "Field dictionary — AED reference data scope (TXT)",
        "Every column: name, description, type, format, level, required, allowed values, example.",
    ),
    "api": (
        "API — AED defibrillators in Poland (api, version 1)",
        "Version 1 API following the Polish Standard API: JSON:API structure, filter[...], sort, fields, page and "
        "limit with links. OpenAPI 3 documentation: /api/v1/docs.",
    ),
    "notes": (
        "About the dataset (TXT)",
        "How the dataset meets the dane.gov.pl technical and API standards, and why it departs from two "
        "recommendations: the CC BY-SA 4.0 licence and the API address.",
    ),
    "dga_xlsx": DGA_ENGLISH,
}


def _data_date():
    """When the data last changed: the latest successful sync, else now."""
    from integrations.models import Integration

    latest = (
        Integration.objects.filter(enabled=True, last_success_at__isnull=False)
        .order_by("-last_success_at")
        .values_list("last_success_at", flat=True)
        .first()
    )
    return latest or timezone.now()


def build_dataset(base_url: str) -> dict:
    """dane.gov.pl-shaped metadata for the dataset, its resources (registered by link) and its sources."""
    from integrations.models import Integration

    base_url = base_url.rstrip("/")
    license_chosen = settings.DATASET_LICENSE if settings.DATASET_LICENSE in PORTAL_LICENSES else None
    modified = _data_date()
    data_date = timezone.localdate(modified).isoformat()

    def resource(fmt, path, title, description):
        if fmt == "api":  # served live by /api/v1, nothing to build; the portal classifies it as an API
            return {
                "title": title,
                "description": description,
                "format": "json",
                "export": "api",
                "media_type": "api",
                "path": path,
                "link": base_url + path,
                "content_type": "application/json",
                "data_date": data_date,
                "language": "pl",
                "availability": "remote",
            }
        content, etag = get_export(fmt, base_url)
        name = ARCHIVED.get(fmt)
        version = data_date if name and archived_path(data_date, name) else None
        return {
            "title": title,
            "description": description,
            "format": FILE_FORMATS.get(fmt, fmt),
            "export": fmt,
            "media_type": "file",
            "path": path,
            "link": base_url + path,
            # this day's version at its own address, kept when newer ones come (what the harvester registers)
            "version_link": f"{base_url}{ARCHIVE_PATH}/{version}/{name}" if version else None,
            "content_type": CONTENT_TYPES[fmt].split(";")[0],
            "file_size": len(content),
            "etag": etag,
            "data_date": data_date,
            "language": "pl",
            "availability": "local",
        }

    sources = [
        {
            "slug": i.slug,
            "name": i.name,
            "publisher": i.publisher,
            "homepage_url": i.homepage_url or i.source_url,
            "license": i.license,
            "license_url": i.license_url,
            "attribution": i.attribution,
        }
        for i in Integration.objects.filter(enabled=True).order_by("-priority", "name")
    ]

    def portal_resource(fmt, path, title, description, score, protected=False):
        return (
            resource(fmt, path, title, description)
            | {
                "openness_score": score,
                "contains_protected_data": protected,
                "special_signs": SPECIAL_SIGNS.get(fmt, []),
            }
            # the portal accepts a protected-data list only with every other flag false
            | FLAGS
            | AUTO_DATA_DATE
        )

    fmt, path, title, description, score = DGA_RESOURCE
    return {
        "dataset": DATASET
        | ({"license_name": license_chosen, "license_url": PORTAL_LICENSES[license_chosen]} if license_chosen else {})
        | {
            "url": base_url + "/export",
            "license_chosen": license_chosen,
            "modified": modified.isoformat(),
            "data_date": data_date,
        },
        "resources": [portal_resource(*r) for r in RESOURCES],
        "supplements": [resource(fmt, path, title, description) for fmt, path, title, description in SUPPLEMENTS],
        # the second dataset: our list of protected data, which the portal adds to its nationwide DGA table
        "dga": {
            "dataset": DGA_DATASET
            | FLAGS
            | {"url": base_url + "/export", "modified": modified.isoformat(), "data_date": data_date},
            "resources": [portal_resource(fmt, path, title, description, score, protected=True)],
        },
        "sources": sources,
        "metadata": {
            "records": Device.objects.filter(active=True).count(),
            "fields": len(PUBLISHED_FIELDS),
            "schema_url": base_url + "/api/schema",
            "harvester_url": base_url + HARVESTER_PATH,
            "page_url": base_url + "/export",
            "generated_at": timezone.now().isoformat(),
            "data_version": data_version(),
        },
    }


def get_dataset(base_url: str) -> dict:
    return cached(f"export{EXPORT_REVISION}:dataset:{base_url}", lambda: build_dataset(base_url))


# ------------------------------------------------------------ dane.gov.pl harvester XML
#
# The portal's harvester ("Źródła danych", type XML) re-imports a provider's datasets every 1/7/30/90 days from one
# XML file. It requires: a URL ending in .xml, Content-Type text/xml or application/xml, the file's MD5 at the same
# URL with .md5 instead of .xml, and validity against its XSD (namespace urn:otwarte-dane:harvester:<version>, child
# elements unqualified). Resource and supplement URLs must be https://.

HARVESTER_PATH = "/api/export/harvester.xml"
JSONLD_PATH = "/api/export/aeds.jsonld"
HARVESTER_NS = "urn:otwarte-dane:harvester:1.13"
EXT_IDENT = "misja-aed-polska"  # stable dataset id in our system; max 36 characters


def _text(value: str) -> str:
    """Plain text from the HTML notes, for XSD fields that hold text (description: max 1000 characters)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _sub(parent: ET.Element, tag: str, text=None, **attrib) -> ET.Element:
    element = ET.SubElement(parent, tag, attrib)
    if isinstance(text, bool):
        element.text = "true" if text else "false"
    elif text is not None:
        element.text = str(text)
    return element


def _bilingual(parent: ET.Element, tag: str, polish: str, english: str) -> None:
    element = _sub(parent, tag)
    _sub(element, "polish", polish)
    _sub(element, "english", english)


def _flags(parent: ET.Element) -> None:
    _sub(parent, "hasDynamicData", FLAGS["has_dynamic_data"])
    _sub(parent, "hasHighValueData", FLAGS["has_high_value_data"])
    _sub(parent, "hasHighValueDataFromEuropeanCommissionList", FLAGS["has_high_value_data_from_ec_list"])
    _sub(parent, "hasResearchData", FLAGS["has_research_data"])


def _supplements(parent: ET.Element, supplements: list[dict]) -> None:
    element = _sub(parent, "supplements")
    for s in supplements:
        supplement = _sub(element, "supplement")
        _sub(supplement, "url", s["link"])
        _bilingual(supplement, "name", s["title"], ENGLISH[s["export"]][0])
        _sub(supplement, "language", s["language"])


def _resources(dataset: ET.Element, ext_ident: str, resources: list[dict], modified: str, regions: bool) -> None:
    element = _sub(dataset, "resources")
    for r in resources:
        resource = _sub(element, "resource", status="published")
        suffix = EXT_IDENT_SUFFIX.get(r["export"], r["export"].replace("_", "-"))
        _sub(resource, "extIdent", f"{ext_ident}-{suffix}")
        _sub(resource, "url", r.get("version_link") or r["link"])
        title_en, description_en = ENGLISH[r["export"]]
        _bilingual(resource, "title", r["title"], title_en)
        _bilingual(resource, "description", r["description"], description_en)
        # local: the portal keeps a copy, refreshed on every harvest; remote: the API is called where it lives
        _sub(resource, "availability", r["availability"])
        _sub(resource, "dataDate", r["data_date"])
        _sub(resource, "lastUpdateDate", modified)
        _flags(resource)
        _sub(resource, "containsProtectedData", r["contains_protected_data"])
        if r["special_signs"]:  # the XSD puts them right after containsProtectedData
            signs = _sub(resource, "specialSigns")
            for sign in r["special_signs"]:
                _sub(signs, "specialSign", sign)
        _sub(resource, "isAutoDataDate", r["is_auto_data_date"])
        _sub(resource, "endlessDataDateUpdate", r["endless_data_date_update"])
        _sub(resource, "dataDateUpdatePeriod", r["data_date_update_period"])
        _sub(resource, "autoDataDateStart", r["data_date"])
        if regions and settings.HARVESTER_REGIONS:
            codes = _sub(resource, "regions")
            for code in settings.HARVESTER_REGIONS[:20]:  # XSD: 1–20 codes of 2–7 digits
                _sub(codes, "terytIdent", code)


def _dga_dataset(root: ET.Element, dga: dict) -> None:
    """Our list of protected data. dane.gov.pl accepts one resource flagged containsProtectedData per XML, from a
    state or local institution, and rejects the whole import if its file fails the checks (see devices/dga.py)."""
    meta = dga["dataset"]
    dataset = _sub(root, "dataset", status="published")
    _sub(dataset, "extIdent", DGA_EXT_IDENT)
    _bilingual(dataset, "title", meta["title"], "List of protected data resources — Misja AED")
    _bilingual(dataset, "description", meta["notes"], meta["notes_en"])
    _sub(dataset, "url", meta["url"])
    _sub(dataset, "updateFrequency", meta["update_frequency"])
    categories = _sub(dataset, "categories")
    for category in meta["categories"]:
        _sub(categories, "category", category["code"])
    _resources(dataset, DGA_EXT_IDENT, dga["resources"], meta["modified"], regions=False)
    tags = _sub(dataset, "tags")
    for keyword in meta["keywords"]:
        _sub(tags, "tag", keyword, lang="pl")
    for keyword in meta["keywords_en"]:
        _sub(tags, "tag", keyword, lang="en")
    _sub(dataset, "lastUpdateDate", meta["modified"])
    _flags(dataset)


def build_harvester_xml(base_url: str) -> bytes:
    """Our datasets in the dane.gov.pl harvester schema, built from the same metadata as dataset.json: the AED
    dataset and the list of protected data."""
    meta = build_dataset(base_url)
    dataset_meta = meta["dataset"]
    modified = dataset_meta["modified"]
    attribution = dataset_meta["license_condition_custom_description"].replace(
        "/api/sources", base_url.rstrip("/") + "/api/sources"
    )

    root = ET.Element(f"{{{HARVESTER_NS}}}datasets")
    dataset = _sub(root, "dataset", status="published")
    _sub(dataset, "extIdent", EXT_IDENT)
    _bilingual(dataset, "title", dataset_meta["title"], DATASET_EN["title"])
    _bilingual(
        dataset,
        "description",
        f"{_text(dataset_meta['notes'])} {attribution}",
        f"{DATASET_EN['description']} Contains OpenStreetMap data (© OpenStreetMap contributors, ODbL 1.0).",
    )
    _sub(dataset, "url", dataset_meta["url"])
    _sub(dataset, "updateFrequency", dataset_meta["update_frequency"])
    categories = _sub(dataset, "categories")
    for category in dataset_meta["categories"]:
        _sub(categories, "category", category["code"])

    conditions = _sub(dataset, "conditions")
    _sub(conditions, "source", True)  # cite the source and the date
    _sub(conditions, "modification", True)  # say when the data was processed
    if dataset_meta["license_chosen"]:  # the portal requires both or neither
        _sub(conditions, "dbOrCopyrighted", attribution)
        _sub(conditions, "dbOrCopyrightedLicenseChosen", dataset_meta["license_chosen"])

    _resources(dataset, EXT_IDENT, meta["resources"], modified, regions=True)

    tags = _sub(dataset, "tags")
    for keyword in dataset_meta["keywords"]:
        _sub(tags, "tag", keyword, lang="pl")
    for keyword in DATASET_EN["keywords"]:
        _sub(tags, "tag", keyword, lang="en")
    _sub(dataset, "lastUpdateDate", modified)
    _flags(dataset)
    _supplements(dataset, meta["supplements"])
    _dga_dataset(root, meta["dga"])

    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def get_harvester_xml(base_url: str) -> tuple[bytes, str]:
    """(content, md5) — the harvester checks the downloaded file against the .md5, so both come from one cache entry."""
    content = cached(f"export{EXPORT_REVISION}:harvester:{base_url}", lambda: build_harvester_xml(base_url))
    return content, hashlib.md5(content).hexdigest()  # noqa: S324 — the checksum the portal asks for


# ------------------------------------------------------------ versions
#
# The Standard techniczny recommends versioning resources instead of overwriting them: each new file at a new URL, and
# every published file kept available. The stable /api/export/… URLs always serve the newest data (for apps); every
# day's data is also kept under /api/export/archiwum/<data date>/<file>, and that dated URL is what the portal gets in
# harvester.xml, so each daily version is a new file at a new address and the previous ones stay downloadable. A day
# with several syncs keeps its last one: the dataset is published daily ("dane na dzień").

ARCHIVE_PATH = "/api/export/archiwum"
# export format → file name in a version (the files a portal resource points to)
ARCHIVED = {
    "csv": "aeds.csv",
    "sources_csv": "aeds-sources.csv",
    "geojson": "aeds.geojson",
    "json": "aeds.json",
    "jsonld": "aeds.jsonld",
    "dga_xlsx": "wykaz-chronionych-danych.xlsx",
}
ARCHIVE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def archive_dir():
    return settings.EXPORT_DIR / "archiwum"


def archived_path(day: str, name: str):
    """The file of one version, or None for anything not an archived name and date (no path tricks)."""
    if not ARCHIVE_DATE.fullmatch(day) or name not in ARCHIVED.values():
        return None
    path = archive_dir() / day / name
    return path if path.is_file() else None


def archive_versions() -> list[str]:
    """Data dates with a stored version, newest first."""
    root = archive_dir()
    if not root.is_dir():
        return []
    return sorted((p.name for p in root.iterdir() if p.is_dir() and ARCHIVE_DATE.fullmatch(p.name)), reverse=True)


def archive_current(base_url: str) -> str:
    """Store today's version of every archived file; returns its data date."""
    day = timezone.localdate(_data_date()).isoformat()
    target = archive_dir() / day
    target.mkdir(parents=True, exist_ok=True)
    for fmt, name in ARCHIVED.items():
        content, _ = get_export(fmt, base_url)
        temporary = target / f".{name}.tmp"
        temporary.write_bytes(content)
        temporary.replace(target / name)  # atomic: a download never sees half a file
    return day


def rebuild_all() -> None:
    settings.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    exports = [
        ("geojson", "aeds.geojson"),
        ("csv", "aeds.csv"),
        ("sources_csv", "aeds-sources.csv"),
        ("json", "aeds.json"),
        ("xlsx", "schema.xlsx"),
        ("template_xlsx", "schema-template.xlsx"),
        ("template_csv", "schema-template.csv"),
        ("dga_xlsx", "wykaz-chronionych-danych.xlsx"),
    ]
    if settings.PUBLIC_BASE_URL:  # JSON-LD carries absolute URIs
        exports.append(("jsonld", "aeds.jsonld"))
    for fmt, name in exports + [("txt", "schema.txt"), ("notes", "informacje-o-zbiorze.txt")]:
        content, _ = get_export(fmt, settings.PUBLIC_BASE_URL)
        (settings.EXPORT_DIR / name).write_bytes(content)
    if settings.PUBLIC_BASE_URL:
        archive_current(settings.PUBLIC_BASE_URL)
        # the metadata may have been built before this version was stored: rebuild it with the dated links
        from django.core.cache import cache

        base = settings.PUBLIC_BASE_URL.rstrip("/")
        cache.delete_many(
            [f"v{data_version()}:export{EXPORT_REVISION}:{kind}:{base}" for kind in ("dataset", "harvester")]
        )
    from .regions import municipality_areas

    municipality_areas()  # warm the cached areas behind /api/stats/regions (seconds of ST_Area on a miss)
