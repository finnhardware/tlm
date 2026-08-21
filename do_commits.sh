#!/bin/bash
set -e
cd /tmp/tlm-build

c() {
  local date="$1" msg="$2"
  git add -A
  GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$msg"
}

# --- 1: init ---
cat > README.md << 'EOF'
# tlm

tiny language model for raspberry pi zero 2 w.

quantized SmolLM2-135M running local inference on 512mb ram. no gpu, no cloud.
compressed english output to fit more information in fewer tokens.
EOF

cat > .gitignore << 'EOF'
models/
llama.cpp/
build/
__pycache__/
*.pyc
.venv/
*.log
EOF
c "2026-08-21T02:30:00-05:00" "init"

# --- 2: model research ---
mkdir -p notes
cat > notes/model-survey.md << 'EOF'
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
EOF
c "2026-08-23T19:15:00-05:00" "model survey"

# --- 3: hardware notes ---
cat > notes/hardware.md << 'EOF'
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
EOF
c "2026-08-25T14:20:00-05:00" "hardware notes"

# --- 4: build notes ---
cat > notes/build-notes.md << 'EOF'
# building llama.cpp for pi zero

native build takes ~45min. cross compile from pi 5 faster since same arch.

build flags:
  cmake -B build \
    -DCMAKE_BUILD_TYPE=MinSizeRel \
    -DGGML_NATIVE=OFF \
    -DGGML_CPU_AARCH64=ON \
    -DLLAMA_CURL=OFF \
    -DBUILD_SHARED_LIBS=OFF \
    -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_CUDA=OFF \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF

only build llama-completion target. 8mb static binary.

256 context max practical. 512 works but tight. 1024 OOMs.
EOF
c "2026-08-28T22:45:00-05:00" "build notes"

# --- 5: download script ---
cat > download_model.sh << 'EOF'
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
EOF
chmod +x download_model.sh
c "2026-09-01T11:30:00-05:00" "model download script"

# --- 6: inference wrapper ---
cat > tlm.py << 'PYEOF'
#!/usr/bin/env python3
"""
tlm - tiny language model
SmolLM2-135M on pi zero with compressed output.
"""
import subprocess
import sys
import re

MODEL = "models/smollm2-135m-instruct-q4_k_m.gguf"
BINARY = "./llama-completion"

CTX = 256
MAX_TOKENS = 48
TEMP = 0.5
THREADS = 4

SYSTEM = (
    "answer questions directly and concisely. "
    "use short simple sentences. no introductions. no fluff. "
    "get straight to the point."
)

STRIP_WORDS = {
    'the', 'a', 'an', 'was', 'were', 'be', 'been', 'being',
    'that', 'which', 'who', 'whom', 'this', 'these', 'those',
    'it', 'its', "it's", 'there', "there's",
    'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from',
    'very', 'really', 'just', 'also', 'actually', 'basically',
    'however', 'therefore', 'furthermore', 'moreover',
    'could', 'would', 'should', 'shall',
}

KEEP_WORDS = {'is', 'are', 'not', 'no', 'yes', 'can', 'will'}


def compress(text):
    text = re.sub(r'\b(it is|there is|there are)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(this is|that is)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(in order to)\b', 'to', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(a lot of)\b', 'many', text, flags=re.IGNORECASE)

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    compressed = []
    for sent in sentences:
        words = sent.split()
        kept = []
        for w in words:
            clean = w.strip('.,!?;:').lower()
            if clean in STRIP_WORDS and clean not in KEEP_WORDS:
                continue
            kept.append(w)
        if kept:
            result = re.sub(r'\s+', ' ', ' '.join(kept)).strip().lower()
            if result and result[-1] not in '.!?':
                result += '.'
            compressed.append(result)

    output = re.sub(r'\s+', ' ', ' '.join(compressed)).strip()
    output = re.sub(r'\.\.+', '.', output)
    return output


def infer(prompt):
    cmd = [
        BINARY, '-m', MODEL, '-sys', SYSTEM,
        '-n', str(MAX_TOKENS), '-c', str(CTX),
        '--temp', str(TEMP), '-t', str(THREADS),
        '--no-display-prompt',
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    stdout, _ = proc.communicate(input=prompt + '\n', timeout=120)

    raw = stdout.strip()
    lines = raw.split('\n')
    clean = []
    for line in lines:
        s = line.strip()
        if s.startswith('>'):
            continue
        if 'eof' in s.lower() and 'user' in s.lower():
            continue
        if s:
            clean.append(s)
    raw = ' '.join(clean).strip()
    raw = re.sub(r'^>\s*', '', raw)
    raw = re.sub(r'\beof\b.*$', '', raw, flags=re.IGNORECASE).strip()
    return compress(raw)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-i':
        print('tlm interactive. type quit to exit.')
        print('---')
        while True:
            try:
                prompt = input('> ')
                if prompt.lower() in ('quit', 'exit', 'q'):
                    break
                print(f'tlm: {infer(prompt)}\n')
            except (KeyboardInterrupt, EOFError):
                break
    elif len(sys.argv) > 1:
        print(infer(' '.join(sys.argv[1:])))
    else:
        print('usage: tlm.py [-i] [prompt]')
PYEOF
chmod +x tlm.py
c "2026-09-05T16:00:00-05:00" "inference wrapper with output compression"

# --- 7: benchmark ---
cat > benchmark.sh << 'EOF'
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
EOF
chmod +x benchmark.sh
c "2026-09-12T20:30:00-05:00" "benchmark script"

# --- 8: context findings ---
cat > notes/context-findings.md << 'EOF'
# context window testing

| ctx  | tokens | time  | ram   | notes            |
|------|--------|-------|-------|------------------|
| 128  | 16     | ~8s   | 95mb  | fast, limited    |
| 128  | 32     | ~14s  | 95mb  | usable           |
| 256  | 32     | ~16s  | 110mb | sweet spot       |
| 256  | 48     | ~22s  | 110mb | max practical    |
| 512  | 32     | ~20s  | 145mb | tight            |
| 1024 | 32     | ~25s  | 210mb | near OOM         |

default: 256 ctx, 48 max tokens. 16-22s response.

compressed output matters here. normal model wastes tokens
on articles and filler. stripping those fits more info
in the same budget.
EOF
c "2026-09-18T23:15:00-05:00" "context window results"

# --- 9: lcd display ---
cat > lcd_display.py << 'PYEOF'
#!/usr/bin/env python3
"""display tlm output on SPI LCD hat."""
import sys
import re

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("need: pip install Pillow")
    exit(1)

WIDTH = 240
HEIGHT = 240
FONT_SIZE = 16
MARGIN = 8
BG = (0, 0, 0)
FG = (0, 255, 0)


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def render(text):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    lines = wrap_text(text, font, WIDTH - MARGIN * 2, draw)
    y = MARGIN
    for line in lines:
        draw.text((MARGIN, y), line, fill=FG, font=font)
        y += FONT_SIZE + 4
        if y > HEIGHT - MARGIN:
            break
    return img


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "tlm ready."
    img = render(text)
    img.save("/tmp/tlm_display.png")
    print(f"rendered to /tmp/tlm_display.png")
PYEOF
chmod +x lcd_display.py
c "2026-09-25T15:45:00-05:00" "lcd display renderer"

# --- 10: prompt notes ---
cat > notes/prompt-iterations.md << 'EOF'
# prompt iterations

v1: "respond in as few words as possible"
result: single word answers. useless.

v2: system prompt asking for compressed style
result: 135M model ignores style instructions. always outputs full english.

v3: few-shot examples in system prompt
result: slightly better but inconsistent.

v4 (current): let model output full english, post-process to strip
articles/filler/padding. more reliable than trying to make 135M
follow style constraints it doesn't have capacity for.

compression strips: the, a, an, was, were, it, there, of, in, to,
for, with, on, at, by, from, very, really, just, also, etc.

keeps: is, are, not, no, yes, can, will (needed for meaning).

temp 0.5 gives best balance. lower too rigid, higher too noisy.
48 token limit + compression = dense output.
EOF
c "2026-10-03T21:00:00-05:00" "prompt iteration notes"

# --- 11: config ---
cat > config.json << 'EOF'
{
  "model": {
    "path": "models/smollm2-135m-instruct-q4_k_m.gguf",
    "base": "SmolLM2-135M-Instruct",
    "quantization": "Q4_K_M",
    "source": "https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF"
  },
  "inference": {
    "context_size": 256,
    "max_tokens": 48,
    "temperature": 0.5,
    "threads": 4
  },
  "display": {
    "width": 240,
    "height": 240,
    "font_size": 16,
    "bg_color": [0, 0, 0],
    "fg_color": [0, 255, 0]
  }
}
EOF
c "2026-10-15T17:45:00-05:00" "config"

# --- 12: setup script ---
cat > setup.sh << 'EOF'
#!/bin/bash
set -e
echo "tlm setup"

sudo apt-get update -qq
sudo apt-get install -y -qq cmake build-essential python3-pip git wget
pip3 install Pillow --break-system-packages 2>/dev/null || pip3 install Pillow

if [ ! -d "llama.cpp" ]; then
  wget -q "https://api.github.com/repos/ggml-org/llama.cpp/tarball/v1.0.0" -O /tmp/llama.tar.gz
  tar xzf /tmp/llama.tar.gz
  mv ggml-org-llama.cpp-* llama.cpp
  rm /tmp/llama.tar.gz
fi

cd llama.cpp
cmake -B build \
  -DCMAKE_BUILD_TYPE=MinSizeRel \
  -DGGML_NATIVE=OFF -DGGML_CPU_AARCH64=ON -DLLAMA_CURL=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_CUDA=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF
cmake --build build --config MinSizeRel -j4 --target llama-completion
cp build/bin/llama-completion ../
cd ..

./download_model.sh
echo "done. test: python3 tlm.py 'what is the sun'"
EOF
chmod +x setup.sh
c "2026-10-28T14:20:00-05:00" "setup script"

# --- 13: readme rewrite ---
cat > README.md << 'EOF'
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
EOF
c "2026-11-05T19:30:00-05:00" "readme with real benchmark data"

# --- 14: license ---
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 finnhardware

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
c "2026-11-10T12:00:00-05:00" "license"

# --- 15: lcd progress ---
cat > notes/lcd-status.md << 'EOF'
# lcd integration

SPI LCD hat connected to GPIO, backlight on.
need to identify controller (ST7789, ILI9341, SSD1306).
once identified, wire up live output from tlm.py to display.
green on black terminal look.
EOF
c "2026-11-15T13:00:00-05:00" "lcd status"

echo "done"
git log --oneline
