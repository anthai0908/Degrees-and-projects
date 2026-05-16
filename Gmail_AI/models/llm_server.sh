#!/bin/bash 
source ../.env

llama-server \
  -m "$LLM_MODEL_PATH" \
  --port "$PORT" \
  -c "$CTX" \
  -ngl "$GPU_LAYERS" \
  -b "$BATCH" \
  --threads 10 \
  --parallel 1 \
  --cache-reuse 256 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -np 1
