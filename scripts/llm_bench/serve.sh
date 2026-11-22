#!/usr/bin/env bash
# Start a throwaway vLLM container for benchmarking on 127.0.0.1:8010 (served name "bench").
# Usage: scripts/llm_bench/serve.sh <hf-model-id> [extra vllm args...]
# The shared production vLLM must be stopped first (only one model fits on the GPU):
#   sudo docker compose -f /home/user/vllm/docker-compose.yml stop
# Restore it afterwards:
#   sudo docker rm -f vllm-bench; sudo docker compose -f /home/user/vllm/docker-compose.yml up -d
set -euo pipefail
model="$1"; shift
sudo docker rm -f vllm-bench >/dev/null 2>&1 || true
sudo docker run -d --name vllm-bench --gpus all --network host --ipc host \
  -v /home/user/.cache/huggingface:/root/.cache/huggingface -v /home/user/.cache/vllm:/root/.cache/vllm \
  vllm/vllm-openai:latest --model "$model" --served-model-name bench --host 127.0.0.1 --port 8010 \
  --max-model-len "${MAX_MODEL_LEN:-8192}" --max-num-seqs "${MAX_NUM_SEQS:-128}" \
  --gpu-memory-utilization "${GPU_UTIL:-0.90}" --enable-prefix-caching "$@" >/dev/null
for i in $(seq 1 120); do
  if curl -sf -m 2 http://127.0.0.1:8010/v1/models >/dev/null; then echo "ready after $((i*5))s"; exit 0; fi
  if ! sudo docker ps -q -f name=vllm-bench | grep -q .; then echo "container died"; sudo docker logs --tail 40 vllm-bench; exit 1; fi
  sleep 5
done
echo "timeout"; sudo docker logs --tail 40 vllm-bench; exit 1
