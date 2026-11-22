# LLM extraction benchmark

Measures how well a local model turns OSM AED free text into structured fields (placement, floor, opening_hours,
access conditions, seasonal, device count, enclosure, position hint), and how fast it does it on vLLM.
Findings and the recommended setup: [docs/llm-extraction/report.mdx](../../docs/llm-extraction/report.mdx).

| File | What |
|---|---|
| `eval_gold.jsonl` | 120 distinct OSM records (95 with harder text, 25 random) with hand-checked answers; `gold_alt` lists other acceptable answers for genuinely ambiguous texts |
| `common.py` | which tags go to the model, the JSON schema, scoring (accuracy per field + "invented" = filled a field that should be empty) |
| `prompts.py` | prompt variants: `rules`, `fewshot`, `strict` (decision-list access rules + counter-examples; the recommended one) |
| `run.py` | run one config against an OpenAI-compatible endpoint and score it; `--inputs` for throughput-only runs |
| `serve.sh` / `bench_all.sh` | start a throwaway vLLM container for a model / run every candidate |
| `make_eval.py` | how the eval inputs were sampled from a snapshot |
| `summarize.py` | markdown tables from `results/` |

```bash
cd scripts/llm_bench
# against the shared production server (Qwen3.8-27B, served as "qwen")
python3 run.py --model qwen --prompt strict --gold eval_gold.jsonl
# another model: stop the shared vLLM first (one model fits on the GPU), then
sudo docker compose -f /home/user/vllm/docker-compose.yml stop
./serve.sh Qwen/Qwen3-4B-Instruct-2507-FP8
LLM_BASE_URL=http://127.0.0.1:8010/v1 python3 run.py --model bench --label qwen3-4b --prompt strict --no-evidence --gold eval_gold.jsonl --concurrency 64
# always restore the shared server afterwards
sudo docker rm -f vllm-bench; sudo docker compose -f /home/user/vllm/docker-compose.yml up -d
python3 summarize.py
```

**How the answers were made.** Qwen3.8-27B pre-labelled the 120 records, then every record was reviewed by hand: 19
labels were corrected and 24 records got accepted alternatives. Because the key started from the 27B's output, the
27B's score is somewhat flattering. The `strict` prompt was written after looking at the 4B models' errors on this
same set, so its gain is measured in-sample; its examples are synthetic, not taken from the set.
