"""What granularity rungs actually exist, and which are reachable.
Static + dynamic audit. No src/ edits, no suite runs."""
import re, sys, inspect
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import acts
from fluidfix.acts import ACTS, KINDS, Observation, SpanEdit, candidates, act_for
from fluidfix.engine import decide, situation

print("=== A. EDIT-granularity rungs: what do the 10 shipped appliers return? ===")
line = "    return a - b"
obs = Observation(lineno=2, kinds=[2, 3, 11])
rows = []
for code, fn in sorted(ACTS.items()):
    out = fn(line, obs)
    out = [out] if isinstance(out, str) else out
    kinds_of = {type(c).__name__ for c in out}
    multiline = any(isinstance(c, str) and "\n" in c for c in out)
    rows.append((code, fn.__name__, sorted(kinds_of), multiline))
for r in rows:
    print(f"  act {r[0]:>2}  {r[1]:<28} returns={r[2]} multiline_str={r[3]}")
print("  shipped appliers returning SpanEdit:",
      sum(1 for r in rows if "SpanEdit" in r[2]), "of", len(rows))

print("\n=== B. is any statement/AST rung present anywhere in the body? ===")
import subprocess
for mod in ("acts", "loop", "guard", "oracle", "coracle"):
    p = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/%s.py" % mod
    src = open(p).read()
    hits = {w: len(re.findall(r"\b%s\b" % w, src))
            for w in ("ast", "tokenize", "SpanEdit", "statement", "block")}
    print(f"  {mod:<8} {hits}")
print("  (localize.py uses ast only to EXPAND coverage anchors, not to edit:)")
src = open("/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/localize.py").read()
print("   ", [l.strip() for l in src.splitlines() if "ast." in l][:6])

print("\n=== C. does anything CONSULT the CHANGE_GRANULARITY ruling? ===")
loop_src = open("/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/loop.py").read()
for i, l in enumerate(loop_src.splitlines(), 1):
    if "HIDDEN" in l or "CHANGE_GRANULARITY" in l.replace("#", ""):
        if "decide(" in l or "ruling" in l:
            print(f"  loop.py:{i}: {l.strip()}")
print("  uses of the variable `ruling` after loop.py:391:")
for i, l in enumerate(loop_src.splitlines(), 1):
    if i > 391 and "ruling" in l:
        print(f"  loop.py:{i}: {l.strip()}")

print("\n=== D. the law's ruling on every situation containing HIDDEN ===")
from itertools import combinations
BITS = ["BUILT","AMB","UNREAD","NOTWIN","HIDDEN","CAPPED","REFUTED","SELF"]
tally = {}
for x in range(256):
    if not (x >> 4) & 1:
        continue
    on = {BITS[b]: True for b in range(8) if (x >> b) & 1}
    r = decide(situation(**on))
    tally.setdefault(r, []).append("+".join(sorted(on)))
for r, v in sorted(tally.items(), key=lambda kv: -len(kv[1])):
    print(f"  {r:<24} {len(v):>3}/128  e.g. {v[0]}")
print("  decide(situation(HIDDEN=True)) =", decide(situation(HIDDEN=True)))
