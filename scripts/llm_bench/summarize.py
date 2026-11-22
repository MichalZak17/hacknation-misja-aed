"""Print a markdown table of all results in scripts/llm_bench/results/."""

import glob
import json
import os
import sys

from common import SCORED, score

here = os.path.dirname(os.path.abspath(__file__))
d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "results")
# Re-score saved predictions against the current answer key, so fixes to eval_gold.jsonl apply to every run.
with open(os.path.join(here, "eval_gold.jsonl")) as fh:
    gold = {r["id"]: r for r in map(json.loads, fh)}
quality, throughput = [], {}
for path in sorted(glob.glob(os.path.join(d, "*.json"))):
    with open(path) as fh:
        r = json.load(fh)
    c, p = r["config"], r["perf"]
    if "score" not in r:
        throughput[r["label"]] = {**p, "n": r["n"], "concurrency": c["concurrency"]}
        continue
    preds = r["predictions"]
    s = score(
        [gold[x["id"]]["gold"] for x in preds],
        [x["pred"] for x in preds],
        [gold[x["id"]].get("gold_alt", {}) for x in preds],
    )
    inv = sum(v["invented"] for v in s["fields"].values())
    quality.append((r["label"], c["prompt"], "yes" if c["evidence"] else "no", c["batch"], s, inv, p))

print("| Model | Prompt | Evidence | Batch | Exact records | " + " | ".join(SCORED) + " | Invented | Out tok/rec |")
print("|---|---|---|---|---|" + "---|" * len(SCORED) + "---|---|")
for label, prompt, ev, batch, s, inv, p in sorted(quality, key=lambda q: (-q[4]["record_exact"], q[0])):
    cells = " | ".join(f"{s['fields'][f]['ok']}" for f in SCORED)
    print(
        f"| {label} | {prompt} | {ev} | {batch} | **{s['record_exact']}**/{s['n']} | {cells} | {inv} | "
        f"{p['completion_tokens_per_record']} |"
    )

if throughput:
    print("\n| Model | Records/s | Inputs | Concurrency | Est. full run (13,395) | Out tok/rec | Failed |")
    print("|---|---|---|---|---|---|---|")
    for label, p in sorted(throughput.items(), key=lambda t: -t[1]["records_per_s"]):
        mins = 13395 / p["records_per_s"] / 60
        print(
            f"| {label} | {p['records_per_s']} | {p['n']} | {p['concurrency']} | {mins:.0f} min | {p['completion_tokens_per_record']} | "
            f"{p['failed_records']} |"
        )
