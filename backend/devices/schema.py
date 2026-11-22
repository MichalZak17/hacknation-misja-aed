"""The reference AED record (wzorcowy zakres danych) — one definition used by the API, CSV/JSON/GeoJSON exports and
the XLSX deliverable. level: 1 = podstawowy (required), 2 = rozszerzony, 3 = pełny.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SchemaField:
    field: str
    label: str
    type: str
    level: int
    example: str
    note: str = ""


SCHEMA: list[SchemaField] = [
    # 1 — podstawowy
    SchemaField("id", "Identyfikator AED", "string", 1, "AED-PL-000231", "Nadawany przy scaleniu; stały"),
    SchemaField(
        "lat", "Szerokość geograficzna", "number (WGS84)", 1, "52.23058", "EPSG:4326, min. 5 miejsc po przecinku"
    ),
    SchemaField("lon", "Długość geograficzna", "number (WGS84)", 1, "21.01105", "EPSG:4326"),
    SchemaField("address", "Adres", "string", 1, "ul. Marszałkowska 126/134", "Zgodny z PRG; pełny zapis"),
    SchemaField(
        "street_type",
        "Cecha ulicy",
        "string",
        1,
        "ul.",
        "ul. | al. | pl. | os. | rondo | skwer | bulw. | park | rynek | szosa | droga | wyb.; z pola address, "
        "puste gdy źródło jej nie podaje",
    ),
    SchemaField("street", "Nazwa ulicy", "string", 1, "Marszałkowska", "Bez cechy; z pola address"),
    SchemaField("house_number", "Numer budynku", "string", 1, "126/134", "Z pola address"),
    SchemaField("postal_code", "Kod pocztowy", "string", 1, "00-008"),
    SchemaField("city", "Miejscowość", "string", 1, "Warszawa"),
    SchemaField("teryt", "Kod TERYT gminy", "string(7)", 1, "1465011"),
    SchemaField("access", "Dostępność", "enum", 1, "public", "public | limited | private | unknown"),
    SchemaField(
        "operational_status",
        "Stan urządzenia",
        "enum",
        1,
        "operational",
        "operational | out_of_service | missing | decommissioned | unknown",
    ),
    SchemaField(
        "readiness",
        "Gotowość",
        "enum",
        1,
        "ready",
        "ready | attention | expired | unknown — wyliczana z dat elektrod, baterii i przeglądu",
    ),
    SchemaField(
        "verified_on", "Data weryfikacji", "date (ISO 8601)", 1, "2026-11-18", "Kiedy ktoś potwierdził AED na miejscu"
    ),
    SchemaField(
        "sources",
        "Źródła",
        "string[]",
        1,
        "osm-poland;warszawa-19115",
        "Identyfikatory źródeł, z których scalono rekord",
    ),
    # 2 — rozszerzony
    SchemaField("building_name", "Obiekt", "string", 2, "Stacja metra Centrum"),
    SchemaField("location_detail", "Lokalizacja w obiekcie", "string", 2, "Antresola, przy kasach biletowych"),
    SchemaField(
        "floor", "Piętro", "integer", 2, "-1", "Liczba całkowita; półpiętro i opisy trafiają do lokalizacji w obiekcie"
    ),
    SchemaField("indoor", "Wewnątrz budynku", "boolean", 2, "true"),
    SchemaField(
        "placement",
        "Umiejscowienie",
        "enum",
        2,
        "outside_on_building",
        "vehicle | inside_building | outside_on_building | freestanding_outdoor | unknown — vehicle: AED wożony "
        "w pojeździe (np. wóz OSP), współrzędne to miejsce stacjonowania",
    ),
    SchemaField("opening_hours", "Godziny dostępności", "string (OSM opening_hours)", 2, "Mo-Su 05:00-24:00"),
    SchemaField(
        "opening_hours_raw", "Godziny dostępności (opis)", "string", 2, "pon.–pt. 8:00–16:00", "Tekst źródłowy"
    ),
    SchemaField(
        "access_conditions",
        "Warunki dostępu",
        "string[]",
        2,
        "ask_staff_or_security;key_holder",
        "Co trzeba zrobić, żeby dostać AED: ask_staff_or_security | key_holder | call_phone | siren_or_alarm_button "
        "| only_during_opening_hours | only_during_events | staff_only | other",
    ),
    SchemaField("seasonal", "Dostępność sezonowa", "boolean", 2, "true", "Dostępność lub miejsce zmienia się sezonowo"),
    SchemaField("cabinet", "Szafka", "enum", 2, "alarm", "alarm | open | locked | none | unknown"),
    SchemaField(
        "is_mobile", "Urządzenie mobilne", "boolean", 2, "false", "Np. w radiowozie; poza mapą punktów stałych"
    ),
    SchemaField("photo_url", "Zdjęcie", "url", 2, "https://example.org/aed/000231.jpg"),
    SchemaField(
        "coordinate_method",
        "Metoda ustalenia położenia",
        "enum",
        2,
        "gps",
        "gps | survey | geocoded | source | unknown",
    ),
    SchemaField("coordinate_accuracy_m", "Dokładność położenia [m]", "number", 2, "5"),
    SchemaField("pads_type", "Rodzaj elektrod", "enum", 2, "universal", "adult | pediatric | universal | unknown"),
    SchemaField("pediatric_pads_available", "Elektrody pediatryczne", "boolean", 2, "true"),
    SchemaField("pediatric_mode", "Tryb pediatryczny", "boolean", 2, "true"),
    # 3 — pełny (dane dysponenta)
    SchemaField("serial_number", "Numer seryjny", "string", 3, "A21B-04567"),
    SchemaField("manufacturer", "Producent", "string", 3, "Philips"),
    SchemaField("model", "Model", "string", 3, "HeartStart FRx"),
    SchemaField("inventory_number", "Numer inwentarzowy", "string", 3, "INW/2024/118"),
    SchemaField("manufactured_on", "Data produkcji", "date", 3, "2021-05-01"),
    SchemaField("installed_on", "Data instalacji", "date", 3, "2022-01-15"),
    SchemaField("pads_replaced_on", "Ostatnia wymiana elektrod", "date", 3, "2026-03-31"),
    SchemaField("pads_expiry_date", "Ważność elektrod", "date", 3, "2028-03-31"),
    SchemaField("battery_installed_on", "Ostatnia wymiana baterii", "date", 3, "2024-03-31"),
    SchemaField("battery_expiry_date", "Ważność baterii", "date", 3, "2028-03-31"),
    SchemaField("battery_status", "Stan baterii", "enum", 3, "ok", "ok | low | replace | unknown"),
    SchemaField(
        "last_self_test_at",
        "Ostatni autotest",
        "datetime (UTC)",
        3,
        "2026-11-20T02:00:00Z",
        "ISO 8601 w UTC, z literą Z",
    ),
    SchemaField("last_self_test_result", "Wynik autotestu", "string", 3, "pass"),
    SchemaField("last_inspection_on", "Ostatni przegląd", "date", 3, "2026-10-14"),
    SchemaField("next_inspection_due", "Następny przegląd", "date", 3, "2027-10-14"),
    SchemaField("last_used_on", "Ostatnie użycie", "date", 3, "2025-07-02", "Po użyciu elektrody wymagają wymiany"),
    SchemaField("verification_method", "Sposób weryfikacji", "string", 3, "inspekcja na miejscu"),
    SchemaField("operator_name", "Dysponent", "string", 3, "Metro Warszawskie sp. z o.o."),
    SchemaField("operator_regon", "REGON dysponenta", "string", 3, "012345675"),
    SchemaField(
        "operator_contact", "Kontakt do dysponenta", "string", 3, "+48226554242", "Wyłącznie kontakt instytucjonalny"
    ),
    SchemaField("simc", "Kod SIMC miejscowości", "string(7)", 3, "0918123"),
]

EXPORT_FIELDS = [f.field for f in SCHEMA]

# What the open data carries: the reference record without the one-line `address`. The Standard techniczny asks for
# one elementary value per field and the address in separate fields (street_type, street, house_number, postal_code,
# city), so the line stays internal: it is what the merge stores and what the UI shows, and an operator file may
# still give it (the import splits it).
INTERNAL_FIELDS = {"address"}
PUBLISHED_SCHEMA = [f for f in SCHEMA if f.field not in INTERNAL_FIELDS]
PUBLISHED_FIELDS = [f.field for f in PUBLISHED_SCHEMA]


def list_columns(field: str) -> list[tuple[str, str, str]]:
    """A list field as flat boolean columns for tables (CSV, the XLSX template): one elementary value per cell, as
    the Standard techniczny asks. access_conditions → [("access_conditions_key_holder", "Warunek dostępu: szafka
    zamknięta, klucz u wskazanej osoby", "key_holder"), …]. JSON, GeoJSON and the API keep the list."""
    label = next(f.label for f in SCHEMA if f.field == field)
    singular = {"access_conditions": "Warunek dostępu"}.get(field, label)
    return [(f"{field}_{value}", f"{singular}: {meaning}", value) for value, meaning in ALLOWED_VALUES[field]]


# The address split into parts (dane.gov.pl Standard techniczny §3: street with its prefix and the building number in
# separate fields). Derived from the merged `address` on read (Device properties), never merged or stored.
ADDRESS_PART_FIELDS = {"street_type", "street", "house_number"}

# Fields a SourceRecord's normalised `data` may carry and the merge copies onto a Device
MERGE_FIELDS = [f for f in EXPORT_FIELDS if f not in {"id", "lat", "lon", "readiness", "sources"} | ADDRESS_PART_FIELDS]

# Merge rule: most fields take the highest-priority source that states them; these take the most recent date, since
# a newer replacement or check supersedes an older one whichever source reports it.
LATEST_DATE_FIELDS = {
    "verified_on",
    "pads_replaced_on",
    "pads_expiry_date",
    "battery_installed_on",
    "battery_expiry_date",
    "last_self_test_at",
    "last_inspection_on",
    "next_inspection_due",
    "last_used_on",
}
DATE_FIELDS = {
    "verified_on",
    "manufactured_on",
    "installed_on",
    "pads_replaced_on",
    "pads_expiry_date",
    "battery_installed_on",
    "battery_expiry_date",
    "last_inspection_on",
    "next_inspection_due",
    "last_used_on",
}
DATETIME_FIELDS = {"last_self_test_at"}
BOOL_FIELDS = {"indoor", "is_mobile", "pediatric_pads_available", "pediatric_mode", "seasonal"}
LIST_FIELDS = {"access_conditions"}
FLOAT_FIELDS = {"coordinate_accuracy_m"}
ENUM_FIELDS = {
    "access": {"public", "limited", "private"},
    "placement": {"vehicle", "inside_building", "outside_on_building", "freestanding_outdoor"},
    "operational_status": {"operational", "out_of_service", "missing", "decommissioned"},
    "coordinate_method": {"gps", "survey", "geocoded", "source"},
    "cabinet": {"alarm", "open", "locked", "none"},
    "pads_type": {"adult", "pediatric", "universal"},
    "battery_status": {"ok", "low", "replace"},
}

NUMBER_FIELDS = {"lat", "lon"} | FLOAT_FIELDS

# ------------------------------------------------------------ the dictionary (słownik pól) of the reference scope
#
# What a data holder needs to fill the template without asking: a description per field, which fields must be filled,
# the format and the allowed values with their meaning. Used by the XLSX/TXT deliverables and /api/schema.

# A record without these cannot be placed on a map or answer "can I use it": the rest may be empty (= no data).
# Enumerations take `unknown` when the holder does not know the value.
REQUIRED_FIELDS = {"id", "lat", "lon", "access", "operational_status"}

UNKNOWN = ("unknown", "brak danych")
ALLOWED_VALUES: dict[str, list[tuple[str, str]]] = {
    "street_type": [
        ("ul.", "ulica"),
        ("al.", "aleja"),
        ("pl.", "plac"),
        ("os.", "osiedle"),
        ("rondo", "rondo"),
        ("skwer", "skwer"),
        ("bulw.", "bulwar"),
        ("park", "park"),
        ("rynek", "rynek"),
        ("szosa", "szosa"),
        ("droga", "droga"),
        ("wyb.", "wybrzeże"),
    ],
    "access": [
        ("public", "dostępne dla każdego"),
        ("limited", "dostępne z ograniczeniami, np. dla klientów lub w godzinach otwarcia obiektu"),
        ("private", "niedostępne publicznie, np. tylko dla pracowników"),
        UNKNOWN,
    ],
    "operational_status": [
        ("operational", "sprawne i na miejscu"),
        ("out_of_service", "czasowo wyłączone (awaria, serwis)"),
        ("missing", "brak urządzenia w miejscu instalacji"),
        ("decommissioned", "wycofane z użytku"),
        UNKNOWN,
    ],
    "readiness": [
        ("ready", "znana ważność elektrod lub baterii i nic nie jest przeterminowane"),
        ("attention", "bateria słaba albo elektrody, bateria lub przegląd tracą ważność w ciągu 30 dni"),
        ("expired", "przeterminowane elektrody, bateria lub przegląd albo urządzenie niesprawne"),
        ("unknown", "brak danych serwisowych"),
    ],
    "placement": [
        ("inside_building", "wewnątrz budynku"),
        ("outside_on_building", "na zewnętrznej ścianie budynku"),
        ("freestanding_outdoor", "wolnostojące na zewnątrz (słupek, kapsuła)"),
        ("vehicle", "w pojeździe (np. wóz OSP); współrzędne to miejsce stacjonowania"),
        UNKNOWN,
    ],
    "access_conditions": [
        ("ask_staff_or_security", "trzeba poprosić obsługę lub ochronę"),
        ("key_holder", "szafka zamknięta, klucz u wskazanej osoby"),
        ("call_phone", "trzeba zadzwonić pod wskazany numer"),
        ("siren_or_alarm_button", "otwarcie szafki włącza alarm lub wymaga przycisku"),
        ("only_during_opening_hours", "tylko w godzinach otwarcia obiektu"),
        ("only_during_events", "tylko podczas wydarzeń"),
        ("staff_only", "tylko dla personelu"),
        ("other", "inny warunek (opisany w polu Lokalizacja w obiekcie)"),
    ],
    "cabinet": [
        ("alarm", "szafka z alarmem"),
        ("open", "szafka otwarta, bez zamka"),
        ("locked", "szafka zamknięta na klucz lub kod"),
        ("none", "bez szafki"),
        UNKNOWN,
    ],
    "coordinate_method": [
        ("gps", "pomiar GPS na miejscu"),
        ("survey", "pomiar geodezyjny"),
        ("geocoded", "wyliczone z adresu"),
        ("source", "przejęte ze źródła bez informacji o metodzie"),
        UNKNOWN,
    ],
    "pads_type": [
        ("adult", "elektrody dla dorosłych"),
        ("pediatric", "elektrody pediatryczne"),
        ("universal", "elektrody uniwersalne (dorośli i dzieci)"),
        UNKNOWN,
    ],
    "battery_status": [
        ("ok", "bateria sprawna"),
        ("low", "bateria słaba"),
        ("replace", "bateria do wymiany"),
        UNKNOWN,
    ],
    "last_self_test_result": [("pass", "autotest zaliczony"), ("fail", "autotest niezaliczony")],
}
BOOL_VALUES = [("true", "tak"), ("false", "nie")]

DESCRIPTIONS = {
    "id": "Stały identyfikator urządzenia. W pliku dysponenta: własny identyfikator (np. numer w rejestrze); w zbiorze "
    "ogólnokrajowym nadawany przy scaleniu (AED-PL-nnnnnn).",
    "lat": "Szerokość geograficzna miejsca, w którym znajduje się AED (WGS84).",
    "lon": "Długość geograficzna miejsca, w którym znajduje się AED (WGS84).",
    "address": "Adres w jednym polu (cecha, ulica, numer), dla wygody czytelnika; te same dane są rozdzielone w polach "
    "Cecha ulicy, Nazwa ulicy i Numer budynku.",
    "street_type": "Cecha ulicy według TERYT ULIC.",
    "street": "Nazwa ulicy bez cechy, w brzmieniu z TERYT ULIC.",
    "house_number": "Numer budynku, z literą lub numerem lokalu.",
    "postal_code": "Kod pocztowy adresu.",
    "city": "Nazwa miejscowości w brzmieniu z TERYT SIMC.",
    "teryt": "Kod gminy z rejestru TERYT TERC: województwo, powiat, gmina i rodzaj gminy.",
    "access": "Kto może skorzystać z AED.",
    "operational_status": "Czy urządzenie jest sprawne i na miejscu.",
    "readiness": "Czy AED jest gotowe do użycia według terminów serwisowych. Wylicza je zbiór ogólnokrajowy z dat "
    "elektrod, baterii i przeglądu; w pliku dysponenta można zostawić puste.",
    "verified_on": "Kiedy ktoś ostatnio potwierdził na miejscu, że AED tam jest.",
    "sources": "Źródła, z których scalono rekord. Wypełnia zbiór ogólnokrajowy; w pliku dysponenta można zostawić "
    "puste.",
    "building_name": "Nazwa obiektu, w którym lub na którym jest AED.",
    "location_detail": "Gdzie dokładnie w obiekcie szukać AED (wejście, piętro, punkt orientacyjny).",
    "floor": "Piętro: 0 to parter, liczby ujemne to kondygnacje podziemne. Półpiętro lub opis (np. „klatka D”) "
    "wpisz w polu Lokalizacja w obiekcie.",
    "indoor": "Czy AED jest wewnątrz budynku.",
    "placement": "Gdzie umieszczono AED względem budynku.",
    "opening_hours": "Kiedy AED jest dostępne, w składni OpenStreetMap opening_hours (np. 24/7, Mo-Fr 08:00-16:00).",
    "opening_hours_raw": "Godziny dostępności w brzmieniu źródła, gdy nie dają się zapisać w składni opening_hours.",
    "access_conditions": "Co trzeba zrobić, żeby dostać AED. Kilka warunków rozdziela się średnikiem.",
    "seasonal": "Czy dostępność lub miejsce AED zmienia się sezonowo (np. kąpielisko, stok).",
    "cabinet": "W jakiej szafce jest AED.",
    "is_mobile": "Czy AED jest przenośne lub wożone (np. w radiowozie), a nie zamontowane na stałe.",
    "photo_url": "Adres zdjęcia AED lub jego oznakowania.",
    "coordinate_method": "Jak ustalono współrzędne.",
    "coordinate_accuracy_m": "Szacowana dokładność współrzędnych w metrach.",
    "pads_type": "Rodzaj elektrod podłączonych do AED.",
    "pediatric_pads_available": "Czy przy AED są elektrody pediatryczne.",
    "pediatric_mode": "Czy AED ma tryb pediatryczny (przycisk lub klucz).",
    "serial_number": "Numer seryjny nadany przez producenta.",
    "manufacturer": "Producent urządzenia.",
    "model": "Model urządzenia.",
    "inventory_number": "Numer inwentarzowy u dysponenta.",
    "manufactured_on": "Data produkcji urządzenia.",
    "installed_on": "Data instalacji w obecnym miejscu.",
    "pads_replaced_on": "Data ostatniej wymiany elektrod.",
    "pads_expiry_date": "Data ważności zainstalowanych elektrod.",
    "battery_installed_on": "Data ostatniej wymiany baterii.",
    "battery_expiry_date": "Data ważności zainstalowanej baterii.",
    "battery_status": "Stan baterii według wskaźnika urządzenia lub ostatniego przeglądu.",
    "last_self_test_at": "Data i godzina ostatniego autotestu urządzenia.",
    "last_self_test_result": "Wynik ostatniego autotestu.",
    "last_inspection_on": "Data ostatniego przeglądu serwisowego.",
    "next_inspection_due": "Termin następnego przeglądu serwisowego.",
    "last_used_on": "Data ostatniego użycia AED u pacjenta; po użyciu elektrody wymagają wymiany.",
    "verification_method": "Jak potwierdzono AED na miejscu (np. inspekcja na miejscu, zdjęcie).",
    "operator_name": "Nazwa podmiotu odpowiedzialnego za AED (dysponenta).",
    "operator_regon": "Numer REGON dysponenta.",
    "operator_contact": "Instytucjonalny telefon lub e-mail dysponenta. Bez danych osobowych.",
    "simc": "Identyfikator miejscowości z rejestru TERYT SIMC.",
}

# How a value is written (Standard techniczny dane.gov.pl §3), by type and for fields with their own rule
_TYPE_LABELS = {
    "string": ("tekst", "tekst"),
    "string(7)": ("tekst", "7 cyfr, z zerem na początku, jeśli występuje"),
    "number (WGS84)": ("liczba", "liczba z kropką dziesiętną, co najmniej 5 miejsc po przecinku"),
    "number": ("liczba", "liczba z kropką dziesiętną, bez separatora tysięcy"),
    "integer": ("liczba całkowita", "liczba całkowita, np. -1, 0, 2"),
    "enum": ("słownik", "jedna wartość z listy dozwolonych"),
    "date": ("data", "rrrr-mm-dd"),
    "date (ISO 8601)": ("data", "rrrr-mm-dd"),
    "datetime (UTC)": ("data i czas", "rrrr-mm-ddThh:mm:ssZ, czas UTC (litera Z na końcu)"),
    "boolean": ("logiczny", "true albo false"),
    "string[]": ("lista", "wartości rozdzielone średnikiem, bez spacji"),
    "url": ("adres URL", "pełny adres https://"),
    "string (OSM opening_hours)": ("tekst", "składnia OpenStreetMap opening_hours"),
}
_FORMATS = {
    "street_type": "jedna wartość z listy dozwolonych, z kropką jak w TERYT",
    "house_number": "tekst, np. 5, 5a, 12/3",
    "postal_code": "dd-ddd, np. 00-950",
    "access_conditions": "wartości z listy dozwolonych rozdzielone średnikiem, bez spacji",
    "last_self_test_result": "jedna wartość z listy dozwolonych",
    "operator_regon": "9 albo 14 cyfr, bez spacji",
    "operator_contact": "telefon +48 i 9 cyfr bez spacji albo adres e-mail",
}


def field_type(f: SchemaField) -> str:
    if f.type == "string" and f.field in ALLOWED_VALUES:
        return "słownik"
    return _TYPE_LABELS[f.type][0]


def field_format(f: SchemaField) -> str:
    return _FORMATS.get(f.field) or _TYPE_LABELS[f.type][1]


def allowed_values(field: str) -> list[tuple[str, str]]:
    if field in BOOL_FIELDS:
        return BOOL_VALUES
    return ALLOWED_VALUES.get(field, [])


def schema_dicts() -> list[dict]:
    return [
        asdict(f)
        | {
            "description": DESCRIPTIONS[f.field],
            "format": field_format(f),
            "required": f.field in REQUIRED_FIELDS,
            "allowed_values": [{"value": v, "meaning": m} for v, m in allowed_values(f.field)],
        }
        for f in SCHEMA
    ]
