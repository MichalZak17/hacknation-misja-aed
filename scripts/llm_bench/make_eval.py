"""Sample a stratified evaluation set of OSM AED records with free text (inputs only; gold labels are added by hand).

python3 scripts/llm_bench/make_eval.py backend/var/snapshots/osm-poland/<snapshot>.geojson scripts/llm_bench/eval_inputs.jsonl  # then hand-label into eval_gold.jsonl
"""

import json
import random
import re
import sys

from common import TEXT_KEYS, record_input

TEMPLATE = re.compile(
    r"^(samoch[oó]d ratowniczo-ga[sś]niczy|samoch[oó]d po[zż]arniczy|na wyposa[zż]eniu (jednostki|osp|jednostki osp))\.?$",
    re.I,
)
HARD = re.compile(
    r"godz|\d[:.]\d\d|całodob|klucz|syren|alarm|sezon|wakac|imprez|piętr|pietr|parter|piwnic|kapsu|szafk|są \d|dwa\b|dwie\b"
    r"|ochron|portier|tylko|wyłącznie|pracowni|zewn|wewn|elewac|remiz|wóz|wozie|pojazd",
    re.I,
)


def text(r):
    return " | ".join(str(r["input"].get(k, "")) for k in TEXT_KEYS)


def main(src, dst, n_hard=95, n_random=25, seed=2026):
    with open(src) as fh:
        features = json.load(fh)["features"]
    seen, pool = set(), []
    for f in features:
        p = f["properties"]
        rec = record_input(p)
        if not any(k in rec for k in TEXT_KEYS):
            continue
        key = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        pool.append({"id": f"{p['@osm_type']}/{p['@osm_id']}", "input": rec})
    rng = random.Random(seed)
    hard = [
        r
        for r in pool
        if HARD.search(text(r)) and not TEMPLATE.match(r["input"].get("defibrillator:location", "").strip())
    ]
    chosen = rng.sample(hard, n_hard)
    ids = {r["id"] for r in chosen}
    chosen += rng.sample([r for r in pool if r["id"] not in ids], n_random)
    with open(dst, "w") as out:
        for r in chosen:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(pool)} distinct texted records, {len(hard)} hard; wrote {len(chosen)} to {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
