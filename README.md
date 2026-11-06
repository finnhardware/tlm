# tlm

tiny language model for raspberry pi zero 2 w.

quantized SmolLM2-135M running local inference on 512mb ram. no gpu, no cloud.
output is post-processed to strip articles, filler, and padding. fits more
information into fewer tokens.

## hardware

- raspberry pi zero 2 w
- 4x ARM Cortex-A53 1GHz
- 512mb ram (415mb usable)
- SPI LCD hat
- battery hat

## model

- base: SmolLM2-135M-Instruct
- quantization: Q4_K_M GGUF
- ram: ~80-100mb
- runtime: llama.cpp (llama-completion, 8mb static binary)
- context: 256 tokens
- max output: 48 tokens
- speed: ~10 tokens/sec, 16-22s per response

## setup

```
git clone https://github.com/finnhardware/tlm.git
cd tlm
./setup.sh
python3 tlm.py -i
```

## example

```
> what is the moon
tlm: moon is celestial body orbits around earth. rocky, metal-rich body.

> how does wifi work
tlm: wifi works allowing devices share single network connection each other.

> explain gravity
tlm: gravity is force attracts all objects mass towards each other.
```

## how it works

the 135M model doesn't have capacity to follow style constraints in a system
prompt. it outputs full english regardless. so the compressed output is done
in post-processing: strip articles (the, a, an), filler (very, really, just),
structural words (of, in, to, for, with). keep words that carry meaning
(is, are, not, can, will).

result is dense output that reads like shorthand. not broken english, just
efficient.

## files

```
tlm.py              inference + compression
lcd_display.py       SPI LCD output
download_model.sh    model download
benchmark.sh         timing tests
setup.sh             one-command install
config.json          model and display config
notes/               research and build log
```

## license

MIT
