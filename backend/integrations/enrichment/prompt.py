"""The extraction prompt and output schema: the `strict` variant without evidence from scripts/llm_bench/, which
scored best on the hand-checked set (117/120 records fully correct with Qwen3.8-27B; docs/llm-extraction/report.mdx).

Changing the prompt or the schema changes PROMPT_VERSION, which changes every cache key, so the next sync re-extracts
every text. Re-run the benchmark before changing either.
"""

PROMPT_VERSION = "strict-v1"

PLACEMENTS = ["vehicle", "inside_building", "outside_on_building", "freestanding_outdoor", "unknown"]
ACCESS_CONDITIONS = [
    "ask_staff_or_security",
    "key_holder",
    "call_phone",
    "siren_or_alarm_button",
    "only_during_opening_hours",
    "only_during_events",
    "staff_only",
    "other",
]
ENCLOSURES = ["capsule", "cabinet", "unknown"]

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "placement",
        "floor",
        "opening_hours",
        "access_conditions",
        "seasonal",
        "device_count",
        "enclosure",
        "position_hint",
    ],
    "properties": {
        "placement": {"enum": PLACEMENTS},
        "floor": {"type": ["integer", "null"]},
        "opening_hours": {"type": ["string", "null"]},
        "access_conditions": {"type": "array", "items": {"enum": ACCESS_CONDITIONS}},
        "seasonal": {"type": "boolean"},
        "device_count": {"type": ["integer", "null"]},
        "enclosure": {"enum": ENCLOSURES},
        "position_hint": {"type": ["string", "null"]},
    },
}

# fmt: off
SYSTEM_PROMPT = """You extract structured facts about AED defibrillators from OpenStreetMap tags. The free text is mostly Polish.

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
- access_conditions: what a rescuer must do or wait for to get the AED, ONLY as written in the free text.
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
  * other: any other explicit condition.
- seasonal: true only if availability or location changes by season/holidays (wakacje, sezon, ferie).
- device_count: number of devices only if the text states it ("są 2", "dwa AED", "w dwóch wozach"); else null.
- enclosure: "capsule" (kapsuła), "cabinet" (szafka, skrzynka, gablota), else "unknown".
- position_hint: a short Polish phrase condensed from the text saying where exactly the AED hangs (e.g. "przy wejściu
  głównym, po lewej"), without the institution name or address; null if the text has no position.

Examples (input -> output):
{"defibrillator:location": "Na ścianie remizy", "opening_hours": "24/7", "indoor": "no", "access": "yes"}
-> {"placement": "outside_on_building", "floor": null, "opening_hours": "24/7", "access_conditions": [], "seasonal": false, "device_count": null, "enclosure": "unknown", "position_hint": "na ścianie remizy"}
{"defibrillator:location": "Samochód ratowniczo-gaśniczy", "note": "są 2", "access": "private"}
-> {"placement": "vehicle", "floor": null, "opening_hours": null, "access_conditions": [], "seasonal": false, "device_count": 2, "enclosure": "unknown", "position_hint": null}
{"defibrillator:location:pl": "Portiernia, parter. Poza godzinami pracy klucz u sołtysa, tel. 600 100 200", "indoor": "yes"}
-> {"placement": "inside_building", "floor": 0, "opening_hours": null, "access_conditions": ["ask_staff_or_security", "key_holder"], "seasonal": false, "device_count": null, "enclosure": "unknown", "position_hint": "portiernia"}
{"defibrillator:location": "w czarnej kapsule przy wejściu głównym do szkoły. Dostępny pon-pt 7:00-16:00"}
-> {"placement": "outside_on_building", "floor": null, "opening_hours": "Mo-Fr 07:00-16:00", "access_conditions": ["only_during_opening_hours"], "seasonal": false, "device_count": null, "enclosure": "capsule", "position_hint": "przy wejściu głównym"}
{"defibrillator:location": "Hol", "description": "AED niedostępny podczas miesięcznej przerwy wakacyjnej", "level": "0", "indoor": "yes"}
-> {"placement": "inside_building", "floor": 0, "opening_hours": null, "access_conditions": [], "seasonal": true, "device_count": null, "enclosure": "unknown", "position_hint": "hol"}
{"defibrillator:location": "wewnątrz budynku, obok portierni", "opening_hours": "Mo-Fr 07:30-15:30", "indoor": "yes", "access": "customers"}
-> {"placement": "inside_building", "floor": null, "opening_hours": "Mo-Fr 07:30-15:30", "access_conditions": [], "seasonal": false, "device_count": null, "enclosure": "unknown", "position_hint": "obok portierni"}
{"defibrillator:location": "Korytarz na 1 piętrze", "level": "1", "indoor": "yes", "access": "permit"}
-> {"placement": "inside_building", "floor": 1, "opening_hours": null, "access_conditions": [], "seasonal": false, "device_count": null, "enclosure": "unknown", "position_hint": "korytarz"}
{"defibrillator:location": "AED na recepcji. Dostępny w godzinach pracy przychodni.", "indoor": "yes"}
-> {"placement": "inside_building", "floor": null, "opening_hours": null, "access_conditions": ["ask_staff_or_security", "only_during_opening_hours"], "seasonal": false, "device_count": null, "enclosure": "unknown", "position_hint": "na recepcji"}"""
# fmt: on
