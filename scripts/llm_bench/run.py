"""Run one benchmark configuration against an OpenAI-compatible endpoint (vLLM) and score it.

    python3 scripts/llm_bench/run.py --model qwen --prompt fewshot --batch 1 --concurrency 32 \
        --gold scripts/llm_bench/eval_gold.jsonl --out scripts/llm_bench/results/

Throughput-only run on unlabelled records (no scoring): --inputs <jsonl with {"id","input"}> --limit 1000
"""

import argparse
import concurrent.futures as cf
import json
import os
import time
import urllib.request

from common import batch_schema, item_schema, score
from prompts import system_prompt


def post(base, body, timeout=600):
    req = urllib.request.Request(
        f"{base}/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def run(args, rows):
    sys_txt = system_prompt(args.prompt, evidence=args.evidence, batch=args.batch > 1)
    schema = batch_schema(args.evidence) if args.batch > 1 else item_schema(args.evidence)
    chunks = [rows[i : i + args.batch] for i in range(0, len(rows), args.batch)]

    def call(chunk):
        if args.batch > 1:
            user = json.dumps([{"id": i, **r["input"]} for i, r in enumerate(chunk)], ensure_ascii=False)
        else:
            user = json.dumps(chunk[0]["input"], ensure_ascii=False)
        body = {
            "model": args.model,
            "temperature": 0,
            "max_tokens": 400 * len(chunk),
            "messages": [{"role": "system", "content": sys_txt}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "aed", "schema": schema, "strict": True},
            },
            "chat_template_kwargs": {"enable_thinking": False},
        }
        t = time.time()
        try:
            resp = post(args.base_url, body)
            content = json.loads(resp["choices"][0]["message"]["content"])
            usage = resp.get("usage") or {}
        except Exception as exc:  # invalid JSON, timeouts, truncation
            return [None] * len(chunk), {"error": repr(exc)[:200]}, time.time() - t
        if args.batch > 1:
            by_id = {it.get("id"): it for it in content.get("items", [])}
            preds = [by_id.get(i) for i in range(len(chunk))]
        else:
            preds = [content]
        return preds, usage, time.time() - t

    t0 = time.time()
    with cf.ThreadPoolExecutor(args.concurrency) as ex:
        results = list(ex.map(call, chunks))
    wall = time.time() - t0
    preds = [p for r in results for p in r[0]]
    usages = [r[1] for r in results]
    return preds, {
        "wall_s": round(wall, 1),
        "records_per_s": round(len(rows) / wall, 2),
        "avg_request_latency_s": round(sum(r[2] for r in results) / len(results), 2),
        "prompt_tokens_per_record": round(sum(u.get("prompt_tokens", 0) for u in usages) / len(rows), 1),
        "completion_tokens_per_record": round(sum(u.get("completion_tokens", 0) for u in usages) / len(rows), 1),
        "failed_records": sum(p is None for p in preds),
        "errors": [u["error"] for u in usages if "error" in u][:3],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "http://100.78.88.117:8000/v1"))
    ap.add_argument("--model", required=True)
    ap.add_argument("--label", help="name for the results file (defaults to the model)")
    ap.add_argument("--prompt", choices=["rules", "fewshot", "strict"], default="fewshot")
    ap.add_argument("--no-evidence", dest="evidence", action="store_false")
    ap.add_argument("--batch", type=int, default=1, help="records per request")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--gold")
    ap.add_argument("--inputs")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    with open(args.gold or args.inputs) as fh:
        rows = [json.loads(line) for line in fh]
    if args.limit:
        rows = rows[: args.limit]
    preds, perf = run(args, rows)
    cfg = {k: getattr(args, k) for k in ("model", "prompt", "evidence", "batch", "concurrency")}
    report = {"label": args.label or args.model, "config": cfg, "perf": perf, "n": len(rows)}
    if args.gold:
        report["score"] = score([r["gold"] for r in rows], preds, [r.get("gold_alt", {}) for r in rows])
    os.makedirs(args.out, exist_ok=True)
    name = f"{report['label']}_{args.prompt}_{'ev' if args.evidence else 'noev'}_b{args.batch}_c{args.concurrency}"
    name += "" if args.gold else "_throughput"
    with open(os.path.join(args.out, name.replace("/", "-") + ".json"), "w") as f:
        json.dump(
            {**report, "predictions": [{"id": r["id"], "pred": p} for r, p in zip(rows, preds, strict=True)]},
            f,
            ensure_ascii=False,
            indent=1,
        )
    s = report.get("score")
    acc = (
        ""
        if not s
        else " | ".join(f"{k}={v['ok']}/{v['n']} inv{v['invented']}" for k, v in s["fields"].items())
        + f" | exact={s['record_exact']}/{s['n']}"
    )
    print(
        f"{name}: {perf['records_per_s']} rec/s, {perf['completion_tokens_per_record']} out tok/rec, "
        f"failed={perf['failed_records']} {acc}"
    )


if __name__ == "__main__":
    main()
