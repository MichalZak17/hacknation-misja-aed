#!/usr/bin/env bash
# Benchmark every candidate model with the same configs. Needs the production vLLM stopped (see serve.sh).
# Usage: scripts/llm_bench/bench_all.sh <all_inputs.jsonl for the throughput run>
set -uo pipefail
cd "$(dirname "$0")"
POOL="$1"
export LLM_BASE_URL=http://127.0.0.1:8010/v1
MM='--limit-mm-per-prompt={"image":0,"video":0}'
models=(
  "qwen3-4b-2507-fp8|Qwen/Qwen3-4B-Instruct-2507-FP8|"
  "qwen3.5-2b|Qwen/Qwen3.5-2B|$MM"
  "qwen3.5-4b|Qwen/Qwen3.5-4B|$MM"
  "gemma-4-e4b|google/gemma-4-E4B-it|$MM"
  "qwen3.5-9b|Qwen/Qwen3.5-9B|$MM"
  "qwen3-30b-a3b-2507-fp8|Qwen/Qwen3-30B-A3B-Instruct-2507-FP8|"
  "qwen3.8-27b-fp8|Qwen/Qwen3.8-27B-FP8|$MM"
)
for entry in "${models[@]}"; do
  IFS='|' read -r label model extra <<<"$entry"
  echo "=== $label ($model) $(date +%T)"
  if [ "$label" != "qwen3-4b-2507-fp8" ] || ! curl -sf -m 2 $LLM_BASE_URL/models >/dev/null; then
    t=$(date +%s)
    if ! ./serve.sh "$model" $extra; then
      echo "retrying without extra args"; ./serve.sh "$model" || { echo "SKIP $label"; continue; }
    fi
    echo "startup_s=$(( $(date +%s) - t ))"
  fi
  sudo docker logs vllm-bench 2>&1 | grep -E "KV cache|Maximum concurrency|Model loading took" | tail -3
  for args in "--prompt fewshot" "--prompt strict" "--prompt strict --no-evidence"; do
    python3 run.py --model bench --label "$label" $args --gold eval_gold.jsonl --concurrency 64 --out results
  done
  python3 run.py --model bench --label "$label" --prompt strict --no-evidence --inputs "$POOL" --limit 2000 --concurrency 128 --out results
done
sudo docker rm -f vllm-bench >/dev/null
echo "=== done $(date +%T)"
