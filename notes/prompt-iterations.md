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
