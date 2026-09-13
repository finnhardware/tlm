#!/bin/bash
MODEL="models/smollm2-135m-instruct-q4_k_m.gguf"
CLI="./llama-completion"

echo "tlm benchmark"
echo "model: SmolLM2-135M-Instruct Q4_K_M"
echo "hardware: $(cat /proc/device-tree/model 2>/dev/null || echo unknown)"
echo "ram: $(free -h | awk '/Mem:/{print $2}')"
echo ""

for ctx in 128 256; do
  for tokens in 16 32 48; do
    echo "ctx=$ctx tokens=$tokens"
    time echo "what is gravity" | $CLI -m $MODEL \
      -sys "answer concisely" \
      -n $tokens -c $ctx --temp 0.7 -t 4 --no-display-prompt 2>/dev/null
    echo ""
  done
done
