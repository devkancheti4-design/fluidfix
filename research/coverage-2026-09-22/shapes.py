#!/usr/bin/env python3
"""What shape are the real one-line fixes the vocabulary does NOT reach? A token-level census."""
import json, re, tokenize, io
from collections import Counter, defaultdict
rows = json.load(open("research/real-history-2026-09-19/remine.json"))["rows"]
reached = set(json.load(open("research/coverage-2026-09-22/coverage.json"))["reached"])

def toks(s):
    try:
        return [(t.type, t.string) for t in tokenize.generate_tokens(io.StringIO(s.strip()).readline)
                if t.type not in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT)]
    except Exception:
        return [(0, w) for w in s.split()]

OPS = set("< > <= >= == != + - * / // % ** and or not in is & | ^ << >>".split())
def kind_of(t):
    ty, s = t
    if ty == tokenize.NUMBER: return "number literal"
    if ty == tokenize.STRING: return "string literal"
    if s in ("True", "False", "None"): return "True/False/None"
    if s in OPS or ty == tokenize.OP and s in OPS: return "operator"
    if ty == tokenize.NAME: return "a name"
    return "punctuation"

def classify(minus, plus):
    if len(plus) > 1: return "one line became several"
    a, b = toks(minus[0]), toks(plus[0])
    import difflib
    sm = difflib.SequenceMatcher(a=[x[1] for x in a], b=[x[1] for x in b])
    changed_a, changed_b = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal": continue
        changed_a += a[i1:i2]; changed_b += b[j1:j2]
    if not changed_a and not changed_b: return "whitespace only"
    if not changed_a: return "tokens added: " + ("call/attr" if any(x[1] in ("(", ".") for x in changed_b) else kind_of(changed_b[0]))
    if not changed_b: return "tokens removed"
    ka = {kind_of(x) for x in changed_a}; kb = {kind_of(x) for x in changed_b}
    if len(changed_a) == 1 and len(changed_b) == 1:
        k = kind_of(changed_a[0]); k2 = kind_of(changed_b[0])
        return f"one {k} swapped" if k == k2 else f"one token: {k} -> {k2}"
    if ka == kb and len(ka) == 1: return f"several {next(iter(ka))}s changed"
    return "rewritten (many tokens)"

bucket = defaultdict(list)
for i, r in enumerate(rows):
    if len(r["minus"]) != 1 or not r["plus"]: continue
    bucket[classify(r["minus"], r["plus"])].append(i)

print(f"{'shape of the real one-line fix':40} {'count':>5} {'reached':>7}   example")
print("-" * 118)
for k, idx in sorted(bucket.items(), key=lambda kv: -len(kv[1])):
    got = sum(1 for i in idx if i in reached)
    ex = next((i for i in idx if i not in reached), idx[0]); r = rows[ex]
    m = r["minus"][0].strip()[:34]; p = r["plus"][0].strip()[:34]
    print(f"{k:40} {len(idx):>5} {got:>7}   {m}  ->  {p}")
print("-" * 118)
tot = sum(len(v) for v in bucket.values()); print(f"{'total one-line':40} {tot:>5} {len(reached):>7}")
json.dump({k: v for k, v in bucket.items()}, open("research/coverage-2026-09-22/shapes.json", "w"))
