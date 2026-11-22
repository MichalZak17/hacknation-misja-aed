"""Prompt variants for extracting structured AED facts from OSM free text."""

RULES = """You extract structured facts about AED defibrillators from OpenStreetMap tags. The free text is mostly Polish.

Most fields are EMPTY for most records — that is the correct answer. Start from null / [] / false / "unknown" and fill a
field ONLY when the text explicitly says so. Never guess, never assume typical values.

Fields:
- placement:
  "vehicle" ONLY if the AED is carried in a vehicle (samochód, wóz, pojazd, GBA, karetka, "na wyposażeniu samochodu").
  A fire station building (remiza, strażnica, "na ścianie remizy", "w budynku remizy") is NOT a vehicle.
  "inside_building" if the text or indoor=yes says it is inside (hol, korytarz, portiernia, recepcja, sekretariat, pokój, piętro, w budynku).
  "outside_on_building" for an outside wall / capsule on a facade (na ścianie budynku, elewacja, kapsuła zewnętrzna, indoor=no with a wall).
  "freestanding_outdoor" for a post, pole, column or kiosk in open space (słup, wolnostojąca kolumna, przystanek).
  Otherwise "unknown".
- floor: integer floor only if the text names it (parter=0, "I piętro"/"1 piętro"=1, piwnica=-1) or a numeric 'level' tag
  exists. Do NOT assume parter.
- opening_hours: if a valid OSM 'opening_hours' tag exists, copy it unchanged. If it is malformed but convertible, return
  the corrected OSM value; if it is prose that cannot be converted, return null. Otherwise convert hours stated in the
  free text ("pon-pt 7:30-15:30" -> "Mo-Fr 07:30-15:30", "całodobowo"/"24h" -> "24/7"). Do not invent days that are not
  stated (use just "08:00-18:00"). Else null.
- access_conditions: only conditions written in the free text. ask_staff_or_security (portier/ochrona/pracownik udostępni,
  "u ochrony", "w portierni"), key_holder (klucz u ...), call_phone (zadzwonić pod numer), siren_or_alarm_button
  (włączyć syrenę / przycisk alarmowy), only_during_opening_hours ("dostępny w godzinach pracy/otwarcia"),
  only_during_events (podczas imprez/spektakli), staff_only (tylko dla pracowników / wyłącznie personel), other.
  The 'access' tag alone is not a condition. Usually [].
- seasonal: true only if availability or location changes by season/holidays (wakacje, sezon, ferie).
- device_count: number of devices only if the text states it ("są 2", "dwa AED", "w dwóch wozach"); else null.
- enclosure: "capsule" (kapsuła), "cabinet" (szafka, skrzynka, gablota), else "unknown".
- position_hint: a short Polish phrase condensed from the text saying where exactly the AED hangs (e.g. "przy wejściu
  głównym, po lewej"), without the institution name or address; null if the text has no position.
- evidence: exact substrings of the input that justify each non-empty field."""

EXAMPLES = [
    (
        {"defibrillator:location": "Na ścianie remizy", "opening_hours": "24/7", "indoor": "no", "access": "yes"},
        {
            "placement": "outside_on_building",
            "floor": None,
            "opening_hours": "24/7",
            "access_conditions": [],
            "seasonal": False,
            "device_count": None,
            "enclosure": "unknown",
            "position_hint": "na ścianie remizy",
            "evidence": ["Na ścianie remizy", "24/7"],
        },
    ),
    (
        {"defibrillator:location": "Samochód ratowniczo-gaśniczy", "note": "są 2", "access": "private"},
        {
            "placement": "vehicle",
            "floor": None,
            "opening_hours": None,
            "access_conditions": [],
            "seasonal": False,
            "device_count": 2,
            "enclosure": "unknown",
            "position_hint": None,
            "evidence": ["Samochód ratowniczo-gaśniczy", "są 2"],
        },
    ),
    (
        {
            "defibrillator:location:pl": "Portiernia, parter. Poza godzinami pracy klucz u sołtysa, tel. 600 100 200",
            "indoor": "yes",
        },
        {
            "placement": "inside_building",
            "floor": 0,
            "opening_hours": None,
            "access_conditions": ["ask_staff_or_security", "key_holder"],
            "seasonal": False,
            "device_count": None,
            "enclosure": "unknown",
            "position_hint": "portiernia",
            "evidence": ["Portiernia", "parter", "klucz u sołtysa"],
        },
    ),
    (
        {"defibrillator:location": "w czarnej kapsule przy wejściu głównym do szkoły. Dostępny pon-pt 7:00-16:00"},
        {
            "placement": "outside_on_building",
            "floor": None,
            "opening_hours": "Mo-Fr 07:00-16:00",
            "access_conditions": ["only_during_opening_hours"],
            "seasonal": False,
            "device_count": None,
            "enclosure": "capsule",
            "position_hint": "przy wejściu głównym",
            "evidence": ["w czarnej kapsule przy wejściu głównym", "pon-pt 7:00-16:00"],
        },
    ),
    (
        {
            "defibrillator:location": "Hol",
            "description": "AED niedostępny podczas miesięcznej przerwy wakacyjnej",
            "level": "0",
            "indoor": "yes",
        },
        {
            "placement": "inside_building",
            "floor": 0,
            "opening_hours": None,
            "access_conditions": [],
            "seasonal": True,
            "device_count": None,
            "enclosure": "unknown",
            "position_hint": "hol",
            "evidence": ["Hol", "przerwy wakacyjnej"],
        },
    ),
]


def _strip_evidence(obj):
    return {k: v for k, v in obj.items() if k != "evidence"}


def system_prompt(variant, evidence=True, batch=False):
    import json

    text = (
        RULES
        if evidence
        else RULES.replace("\n- evidence: exact substrings of the input that justify each non-empty field.", "")
    )
    if batch:
        text += (
            '\n\nThe user message is a JSON array of records, each with an integer "id". Return {"items": [...]} '
            "with exactly one result per input record, in the same order, each carrying the record's id."
        )
    if variant == "fewshot":
        text += "\n\nExamples (input -> output):"
        for inp, out in EXAMPLES:
            out = out if evidence else _strip_evidence(out)
            text += f"\n{json.dumps(inp, ensure_ascii=False)}\n-> {json.dumps(out, ensure_ascii=False)}"
    return text


# "strict": same task, with the access rules rewritten as a decision list and counter-examples. Written after the
# 4B models over-used ask_staff_or_security (for any building with access=customers) and missed AEDs kept *in* a lodge.
ACCESS_STRICT = """- access_conditions: what a rescuer must do or wait for to get the AED, ONLY as written in the free text.
  Decide each one separately; most records have none, so [] is the usual answer.
  * ask_staff_or_security: the AED is kept INSIDE a staffed room or desk — "portiernia", "w portierni", "recepcja",
    "na recepcji", "u ochrony", "u ochroniarza", "pomieszczenie ochrony", "dyżurka", "dyspozytor", "pod nadzorem ochrony",
    or the text says staff/security will hand it over. NOT when it only hangs next to one ("obok portierni",
    "przy portierni", "przy pomieszczeniu portierni", "od strony ochrony"). NEVER infer it from the access tag
    (access=customers/permit/private) or from being inside a building.
  * only_during_opening_hours: the free text limits availability to working/opening hours ("dostępny w godzinach
    pracy", "w godzinach otwarcia", "Dostępny od 6.00 do 15.00", "AED dostępność 8:00-15:00"). An opening_hours tag
    alone is NOT a condition.
  * key_holder: someone holds a key ("klucz u sołtysa"). call_phone: the text says to phone a number.
  * siren_or_alarm_button: the rescuer must switch on a siren / press an alarm button first.
  * only_during_events: available only during events/shows. staff_only: only for employees / staff.
  * other: any other explicit condition."""

EXAMPLES_STRICT = EXAMPLES + [
    (
        {
            "defibrillator:location": "wewnątrz budynku, obok portierni",
            "opening_hours": "Mo-Fr 07:30-15:30",
            "indoor": "yes",
            "access": "customers",
        },
        {
            "placement": "inside_building",
            "floor": None,
            "opening_hours": "Mo-Fr 07:30-15:30",
            "access_conditions": [],
            "seasonal": False,
            "device_count": None,
            "enclosure": "unknown",
            "position_hint": "obok portierni",
            "evidence": ["wewnątrz budynku, obok portierni"],
        },
    ),
    (
        {"defibrillator:location": "Korytarz na 1 piętrze", "level": "1", "indoor": "yes", "access": "permit"},
        {
            "placement": "inside_building",
            "floor": 1,
            "opening_hours": None,
            "access_conditions": [],
            "seasonal": False,
            "device_count": None,
            "enclosure": "unknown",
            "position_hint": "korytarz",
            "evidence": ["Korytarz na 1 piętrze"],
        },
    ),
    (
        {"defibrillator:location": "AED na recepcji. Dostępny w godzinach pracy przychodni.", "indoor": "yes"},
        {
            "placement": "inside_building",
            "floor": None,
            "opening_hours": None,
            "access_conditions": ["ask_staff_or_security", "only_during_opening_hours"],
            "seasonal": False,
            "device_count": None,
            "enclosure": "unknown",
            "position_hint": "na recepcji",
            "evidence": ["AED na recepcji", "Dostępny w godzinach pracy przychodni"],
        },
    ),
]


def _access_strict(text):
    start = text.index("- access_conditions:")
    end = text.index("- seasonal:")
    return text[:start] + ACCESS_STRICT + "\n" + text[end:]


_base_system_prompt = system_prompt


def system_prompt(variant, evidence=True, batch=False):  # noqa: F811 — extends the function above
    import json

    if variant != "strict":
        return _base_system_prompt(variant, evidence, batch)
    text = _access_strict(_base_system_prompt("rules", evidence, batch))
    text += "\n\nExamples (input -> output):"
    for inp, out in EXAMPLES_STRICT:
        out = out if evidence else _strip_evidence(out)
        text += f"\n{json.dumps(inp, ensure_ascii=False)}\n-> {json.dumps(out, ensure_ascii=False)}"
    return text
