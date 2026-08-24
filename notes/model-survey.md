# model candidates

constraints:
- 512mb ram, ~200mb usable after OS
- arm cortex-a53, no gpu
- need GGUF for llama.cpp
- target interactive response time under 30s

evaluated:
- SmolLM2-135M: 135M params, Q4_K_M ~80mb. best fit.
- Qwen3-0.6B: 600M params. Q2 still too large.
- TinyLlama-1.1B: way too large even at Q2.
- GPT-2 124M: similar size but no instruct tuning, older arch.

decision: SmolLM2-135M-Instruct Q4_K_M.
