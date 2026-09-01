#!/bin/bash
MODEL_DIR="models"
MODEL_URL="https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/resolve/main/SmolLM2-135M-Instruct-Q4_K_M.gguf"
MODEL_FILE="$MODEL_DIR/smollm2-135m-instruct-q4_k_m.gguf"

mkdir -p "$MODEL_DIR"
if [ -f "$MODEL_FILE" ]; then
  echo "already downloaded: $MODEL_FILE"
  exit 0
fi
echo "downloading SmolLM2-135M-Instruct Q4_K_M..."
wget -O "$MODEL_FILE" "$MODEL_URL"
ls -lh "$MODEL_FILE"
