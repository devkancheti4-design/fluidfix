#!/usr/bin/env python
"""RANK BITS AUDIT — for each of the 8 ranking-law bits, exercise the exact
body code that measures it and classify measured / approximated / hardcoded.

No src/ edits. Everything below calls fluidfix's OWN functions.

  nice -n 15 timeout 300 \
    /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python bits_audit.py

Sections:
  A  call-site census: which guard entry points consult the law at all
  B  per-bit probe on a PYTHON fixture (the only path that ranks)
  C  per-bit probe on a C fixture (the Box2D/cglm language)
  D  the RETRIED lane: is the data present in the body, is it passed
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

FF = "/Users/kanchetidevieswar/neo/fluidfix"
HERE = os.path.dirname(os.path.abspath(__file__))

import fluidfix.guard as G          # noqa: E402
import fluidfix.rank as R           # noqa: E402
from fluidfix.acts import Observation  # noqa: E402
from fluidfix.observers import MechanicalObserver  # noqa: E402

BAR = "=" * 74


# --------------------------------------------------------------- SECTION A
print(BAR)
print("A. CALL-SITE CENSUS — which guard entry points consult the ranking law")
print(BAR)
for rel in ("src/fluidfix/guard.py", "src/fluidfix/coracle.py",
            "src/fluidfix/javaoracle.py", "src/fluidfix/loop.py",
            "src/fluidfix/acts.py", "src/fluidfix/cli.py"):
    txt = open(os.path.join(FF, rel)).read().split("\n")
    for i, l in enumerate(txt, 1):
        if "rank_observations" in l or re.search(r"observer\.observe\(", l):
            print(f"  {rel}:{i}: {l.strip()[:88]}")
print()


# --------------------------------------------------------------- SECTION B
# The body's own measurement code, driven by wrapping observe_bits so we
# capture the byte rank_observations built for every candidate line.
SEEN: list[dict] = []
_orig = R.observe_bits


def _tap(**kw):
    SEEN.append({k: bool(v) for k, v in kw.items()})
    return _orig(**kw)


R.observe_bits = _tap
G.observe_bits = _tap if hasattr(G, "observe_bits") else None


def probe(label, src, obs, failing_output, root=None, rel=None, retried=None):
    SEEN.clear()
    out = G.rank_observations(src, obs, failing_output,
                              root=root, rel=rel, retried=retried)
    print(f"-- {label}")
    print(f"   rel={rel!r}  order in={[o.lineno for o in obs]} "
          f"out={[o.lineno for o in out]}")
    for o, b in zip(obs, SEEN):
        on = "+".join(k.upper() for k in R.BITS
                      if b.get(k.lower(), False)) or "(none)"
        byte = R.observe_bits.__wrapped__ if False else None
        raw = sum(1 << R.BITS.index(k) for k in R.BITS
                  if b.get(k.lower(), False))
        print(f"   line {o.lineno:4d}  byte 0x{raw:02x} = {on:<40s} "
              f"rank={R.rank(raw)}")
    print()
    return out


PY_SRC = '''def ordinal_number(n):
    return "th"


def unrelated_helper(x):
    return x + 1


def another(y):
    return y * 2
'''
PY_OUT = ('FAILED test_mod.py::test_ordinal_number - AssertionError\n'
          '  File "mod.py", line 2, in ordinal_number\n')

print(BAR)
print("B. PER-BIT PROBE — PYTHON fixture (guard_once is the only ranking path)")
print(BAR)
py_obs = [Observation(lineno=2, kinds=[1]),
          Observation(lineno=6, kinds=[1]),
          Observation(lineno=10, kinds=[1])]
probe("python, traceback names mod.py:2", PY_SRC, py_obs, PY_OUT, rel="mod.py")

# same, but with the retried lane the body never passes
probe("python, SAME inputs + retried={2} (a kwarg no body call site passes)",
      PY_SRC, py_obs, PY_OUT, rel="mod.py", retried={2})


# --------------------------------------------------------------- SECTION C
print(BAR)
print("C. PER-BIT PROBE — C fixture (the Box2D / cglm language)")
print(BAR)
C_SRC = '''float b2LengthSquared(b2Vec2 v)
{
\treturn v.x * v.x + v.y * v.y + 1;
}

float b2Distance(b2Vec2 a, b2Vec2 b)
{
\treturn b2Length(b2Sub(a, b));
}
'''
# Two REAL C failing-output shapes, both cited in coracle.py's own header
# comment (coracle.py lines 59-60).
C_OUT_A = ('assert fail in /repo/test/test_vec2.h on line 3 :  '
           'ASSERT(b2LengthSquared(v) == 4.0f)\n'
           'FAILED math_test.c:3: assertion failed\n')
c_obs = [Observation(lineno=3, kinds=[1]), Observation(lineno=8, kinds=[1])]
probe("C source, real C failing-output shape", C_SRC, c_obs, C_OUT_A,
      rel="math_functions.c")

# control: identical evidence, but rename the file .py so the FRAME regex fires
C_OUT_PY = C_OUT_A.replace("math_test.c:3", "math_functions.py:3")
probe("CONTROL: same C source, output rewritten to name a .py file",
      C_SRC, c_obs, C_OUT_PY, rel="math_functions.py")

print("   FRAME regex in guard.py:364 (verbatim):")
print("     " + r'([\w./\\-]+\.py)[\":,]+\s*(?:line\s+)?(\d+)')
print("   -> the literal '.py' means no non-Python path can ever set FRAME.")
pat = re.compile(r"([\w./\\-]+\.py)[\":,]+\s*(?:line\s+)?(\d+)")
print(f"   matches in the real C failing output: {pat.findall(C_OUT_A)}")
print()
print("   NAMED needs ast.parse(src) (guard.py:375). On the C source above:")
import ast  # noqa: E402
try:
    ast.parse(C_SRC)
    print("     ast.parse succeeded (unexpected)")
except SyntaxError as e:
    print(f"     SyntaxError: {str(e)[:70]} -> line_toks stays empty, NAMED=0")
print("   NAMED also needs pytest's '^FAILED <path>::<name>' line "
      "(guard.py:370):")
print("     tokens from the C output:",
      [m for m in re.findall(r"^(?:FAILED|ERROR)\s+\S*?::(\S+)", C_OUT_A,
                             re.M)])
print()


# --------------------------------------------------------------- SECTION D
print(BAR)
print("D. THE RETRIED LANE — is the data present, is it passed?")
print(BAR)
gsrc = open(os.path.join(FF, "src/fluidfix/guard.py")).read().split("\n")
for i, l in enumerate(gsrc, 1):
    if "rank_observations(" in l and "def " not in l:
        blk = "\n".join(gsrc[i - 1:i + 3])
        print(f"  guard.py:{i} call site kwargs -> "
              f"{'retried=' in blk and 'PASSES retried' or 'NO retried kwarg'}")
lsrc = open(os.path.join(FF, "src/fluidfix/loop.py")).read().split("\n")
for i, l in enumerate(lsrc, 1):
    if "at_str = " in l or "tried_log.append" in l or l.strip().startswith(
            "tried: set"):
        print(f"  loop.py:{i}: {l.strip()[:80]}")
print()
print("  So: loop.py records every rejected candidate as "
      "'<file>:<lineno>' in result.tried_log, guard_once accumulates them")
print("  into `attempts`, and neither rank_observations call site turns that")
print("  into the `retried` set the law's veto lane reads.")
print()
print("  Does a second pass over the SAME file happen? guard.py:509-510 adds a")
print("  file to full_sight ONLY when its packet was untruncated; guard.py:574")
print("  skips only files in full_sight. A TRUNCATED pass-0 file is therefore")
print("  re-ranked at guard.py:585 with retried=None.")
print()
print("  loop.repair()'s own dedupe set is per-call (loop.py:185), so the")
print("  escalation pass re-tries pass-0 candidates and pays the suite runs")
print("  again. Demonstrated below by construction:")
print(f"    loop.py:185 -> {lsrc[184].strip()}")
