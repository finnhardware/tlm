#!/usr/bin/env python3
"""
tlm - tiny language model
SmolLM2-135M on pi zero with compressed output.
135M can't follow style prompts, so compression is post-processing.
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

# aggressive strip list — everything that doesn't carry core meaning
STRIP_WORDS = {
    # articles, determiners
    'the', 'a', 'an', 'this', 'that', 'these', 'those',
    # pronouns
    'it', 'its', "it's", 'they', 'them', 'their', 'we', 'our',
    'which', 'who', 'whom', 'whose',
    # be-verbs (except is/are — kept for structure)
    'was', 'were', 'be', 'been', 'being',
    # existentials
    'there', "there's", "there're",
    # prepositions
    'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from',
    'into', 'onto', 'upon', 'about', 'through', 'during', 'between',
    'among', 'within', 'without', 'toward', 'towards',
    # modals (except can/will)
    'could', 'would', 'should', 'shall', 'might', 'may',
    # filler adverbs
    'very', 'really', 'just', 'also', 'actually', 'basically',
    'essentially', 'generally', 'typically', 'usually', 'often',
    'sometimes', 'particularly', 'especially', 'specifically',
    'certainly', 'definitely', 'probably', 'possibly', 'perhaps',
    'simply', 'merely', 'quite', 'rather', 'somewhat',
    # conjunctive filler
    'however', 'therefore', 'furthermore', 'moreover', 'although',
    'nevertheless', 'nonetheless', 'meanwhile', 'consequently',
    # padding verbs/words
    'has', 'have', 'had', 'does', 'do', 'did',
    'known', 'called', 'referred', 'considered', 'regarded',
    'such', 'as', 'like', 'both', 'each', 'every', 'many',
    'some', 'most', 'several', 'various', 'numerous',
    'much', 'more', 'other', 'another', 'own',
    'while', 'since', 'because', 'when', 'where', 'how',
    'what', 'than', 'then', 'still', 'even', 'well',
    'over', 'under', 'after', 'before',
}

KEEP_WORDS = {'is', 'are', 'not', 'no', 'yes', 'can', 'will', 'and', 'or', 'but'}

# phrases to nuke entirely
FILLER_PHRASES = [
    r'\b(it is|there is|there are|there were)\b',
    r'\b(this is|that is|that are|that was)\b',
    r'\b(which is|which are|which was)\b',
    r'\b(has been|have been|had been)\b',
    r'\b(is known as|is called|is referred to as)\b',
    r'\b(is often|is usually|is typically|is generally)\b',
    r'\b(as well as)\b',
    r'\b(a lot of|lots of)\b',
    r'\b(in order to)\b',
    r'\b(due to|because of|as a result of)\b',
    r'\b(one of|some of|many of|most of|part of)\b',
    r'\b(kind of|type of|sort of|form of)\b',
    r'\b(in fact|of course|for example|for instance)\b',
    r'\b(on the other hand|at the same time)\b',
    r'\b(it can be|it may be|it could be)\b',
    r'\b(is a|is an|are a|are an)\b',
]

MAX_SENTENCES = 3  # hard cap — keep it short


def compress(text):
    """aggressive compression — half-sentence shorthand."""
    # nuke filler phrases
    for pattern in FILLER_PHRASES:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # strip quoted fluff
    text = re.sub(r'"[^"]*"', '', text)
    text = re.sub(r"'[^']*'", '', text)

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    compressed = []

    for sent in sentences[:MAX_SENTENCES]:
        words = sent.split()
        kept = []
        for w in words:
            clean = w.strip('.,!?;:()[]').lower()
            if not clean:
                continue
            if clean in STRIP_WORDS and clean not in KEEP_WORDS:
                continue
            kept.append(w.lower().strip('()[]'))
        if kept:
            result = re.sub(r'\s+', ' ', ' '.join(kept)).strip()
            # strip trailing punctuation clutter, re-add period
            result = result.rstrip('.,!?;: ')
            if result:
                result += '.'
                compressed.append(result)

    output = ' '.join(compressed)
    # final cleanup
    output = re.sub(r'\s+', ' ', output).strip()
    output = re.sub(r'\.\.+', '.', output)
    output = re.sub(r'\s+\.', '.', output)
    return output


def infer(prompt):
    """run inference and return compressed output."""
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
