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
