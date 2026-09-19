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
