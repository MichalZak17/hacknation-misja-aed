"""Shared pieces of the LLM extraction benchmark: which OSM tags go to the model, the output schema, scoring."""

import re

# Free-text tags plus the structured tags that give the model context (and that it may copy/correct).
TEXT_KEYS = (
    "defibrillator:location:pl",
    "defibrillator:location",
    "defibrillator:location:en",
    "description",
    "description:pl",
    "note",
    "fixme",
    "location",
)
CONTEXT_KEYS = ("opening_hours", "level", "indoor", "access")

PLACEMENTS = ["vehicle", "inside_building", "outside_on_building", "freestanding_outdoor", "unknown"]
ACCESS = [
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
SCORED = ["placement", "floor", "opening_hours", "access_conditions", "seasonal", "device_count", "enclosure"]


def record_input(props):
    return {k: props[k] for k in TEXT_KEYS + CONTEXT_KEYS if k in props}


def item_schema(with_evidence=True, with_id=False):
    props = {
        "placement": {"enum": PLACEMENTS},
        "floor": {"type": ["integer", "null"]},
        "opening_hours": {"type": ["string", "null"]},
        "access_conditions": {"type": "array", "items": {"enum": ACCESS}},
        "seasonal": {"type": "boolean"},
        "device_count": {"type": ["integer", "null"]},
        "enclosure": {"enum": ENCLOSURES},
        "position_hint": {"type": ["string", "null"]},
    }
    if with_evidence:
        props["evidence"] = {"type": "array", "items": {"type": "string"}}
    if with_id:
        props = {"id": {"type": "integer"}, **props}
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


def batch_schema(with_evidence=True):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {"items": {"type": "array", "items": item_schema(with_evidence, with_id=True)}},
    }


def norm_oh(v):
    if v is None:
        return None
    return re.sub(r"\s+", "", v).replace("Sa,Su", "Sa-Su").lower()


def _norm(field, v):
    if field == "opening_hours":
        return norm_oh(v)
    if field == "access_conditions":
        return sorted(set(v or []))
    return v


def _empty(v):
    return v in (None, [], False, "unknown")


def score(gold_rows, pred_rows, alt_rows=None):
    """Per-field accuracy, and 'invented' = model filled a field whose gold value is empty.

    alt_rows: per record {field: [other acceptable values]} for genuinely ambiguous texts.
    """
    fields = {f: {"ok": 0, "n": 0, "invented": 0, "missed": 0} for f in SCORED}
    exact = 0
    alt_rows = alt_rows or [{}] * len(gold_rows)
    for gold, pred, alt in zip(gold_rows, pred_rows, alt_rows, strict=True):
        all_ok = True
        for f in SCORED:
            g, p = _norm(f, gold[f]), _norm(f, (pred or {}).get(f))
            accepted = [g] + [_norm(f, a) for a in (alt or {}).get(f, [])]
            ok = p in accepted
            st = fields[f]
            st["n"] += 1
            st["ok"] += ok
            if not ok:
                all_ok = False
                if _empty(g) and not _empty(p):
                    st["invented"] += 1
                elif not _empty(g) and _empty(p):
                    st["missed"] += 1
        exact += all_ok
    return {"fields": fields, "record_exact": exact, "n": len(gold_rows)}
