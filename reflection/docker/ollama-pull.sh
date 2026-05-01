#!/bin/sh
set -eu

MODEL="${REFLECTION_LLM_MODEL:-qwen2.5:7b-instruct}"
if [ -z "${MODEL}" ]; then
  MODEL="qwen2.5:7b-instruct"
fi

echo "[ollama-pull] pulling model: ${MODEL}"

# ждём сеть/сервер
sleep 2

i=1
while [ "$i" -le 30 ]; do
  # `ollama pull` очень шумный: спамит "pulling manifest".
  # Оставляем только строки про реальную загрузку/проверку.
  if ollama pull "${MODEL}" 2>&1 \
    | grep -v "pulling manifest" \
    | grep -E "downloading|verifying|success|sha256|error|\\b[0-9]+%\\b" \
    ; then
    echo "[ollama-pull] done"
    exit 0
  fi
  i=$((i + 1))
  sleep 5
done

echo "[ollama-pull] failed after retries"
exit 1

