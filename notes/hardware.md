# target hardware

raspberry pi zero 2 w
- 4x ARM Cortex-A53 1GHz
- 512mb LPDDR2 (415mb usable)
- microSD storage
- 802.11 b/g/n wifi
- 40-pin GPIO
- 5V micro-USB power

attached:
- SPI LCD hat (direct GPIO)
- battery/UPS hat

memory budget:
- kernel + OS: ~250mb
- model weights Q4_K_M: ~80mb
- KV cache 256 ctx: ~10mb
- llama.cpp runtime: ~5mb
- lcd driver: ~2mb
- headroom: ~68mb
