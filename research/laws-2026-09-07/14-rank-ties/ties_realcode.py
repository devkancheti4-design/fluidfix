"""How big are the RANK ties on REAL code, not a hand-built fixture?

Read-only. Points the MechanicalObserver + guard.rank_observations at
fluidfix's OWN source files (nothing is written, nothing under src/ is
edited) and reports, per file, the priority classes the law produced and
the size of the class the defect would sit in.

Two failing-output shapes are measured, because they are the two shapes
the body actually sees:
  (a) assertion failure  -- "FAILED tests/test_x.py::test_<fn> - assert"
      no traceback line numbers, so FRAME is 0 on every line.
  (b) traceback          -- one real 'File "<f>", line N' frame, so exactly
      one line can reach priority 0.

Run:
  nice -n 15 perl -e 'alarm 300; exec @ARGV' -- \
    /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python ties_realcode.py
"""
import ast
import glob
import os
import sys
from collections import Counter

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.rank as rankmod                     # noqa: E402
from fluidfix import MechanicalObserver             # noqa: E402
from fluidfix.guard import rank_observations        # noqa: E402
from fluidfix.localize import Packet                # noqa: E402

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix"

BYTES = []
_real = rankmod.rank


def spy(x):
    p = _real(x)
    BYTES.append((x, p))
    return p


rankmod.rank = spy


def first_def(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and not node.name.startswith("_"):
            return node.name, node.lineno, (node.end_lineno or node.lineno)
    return None


rows = []
for path in sorted(glob.glob(os.path.join(SRC, "*.py"))):
    rel = os.path.basename(rel_src := path)
    src = open(path, encoding="utf-8").read()
    src_lines = src.split("\n")
    fd = first_def(src)
    if fd is None:
        continue
    fn, lo, hi = fd
    pk = Packet(defect_file=rel, failure="", mode="coverage",
                lines=[i + 1 for i, l in enumerate(src_lines) if l.strip()],
                src_lines=src_lines)
    obs = MechanicalObserver().observe([pk])[0]
    if len(obs) < 5:
        continue
    for shape, out in (
        ("assert", f"FAILED tests/test_{rel[:-3]}.py::test_{fn} - assert 1 == 2"),
        ("trace",  f'FAILED tests/test_{rel[:-3]}.py::test_{fn}\n'
                   f'  File "{rel}", line {lo + 1}, in {fn}\n'
                   f'    x = 1\nAssertionError'),
    ):
        BYTES.clear()
        ordered = rank_observations(src, obs, out, rel=rel)
        prios = [p for _, p in BYTES[:len(obs)]]
        classes = Counter(prios)
        top = min(classes)
        rows.append((rel, shape, len(obs), dict(sorted(classes.items())),
                     top, classes[top],
                     [o.lineno for o in ordered][:5]))

print("== per-file priority classes on real fluidfix source ==")
print(f"{'file':22s} {'shape':7s} {'obs':>5s}  {'top':>3s} {'|top class|':>11s}  classes")
for rel, shape, n, classes, top, ntop, first5 in rows:
    print(f"{rel:22s} {shape:7s} {n:5d}  {top:3d} {ntop:11d}  {classes}")

print("\n== summary ==")
for shape in ("assert", "trace"):
    rs = [r for r in rows if r[1] == shape]
    n_obs = sum(r[2] for r in rs)
    n_top = sum(r[5] for r in rs)
    singletons = sum(1 for r in rs if r[5] == 1)
    print(f"  {shape}: {len(rs)} files, {n_obs} observations, "
          f"top class size total {n_top}, "
          f"files whose top class is a SINGLETON: {singletons}/{len(rs)}")
    sizes = sorted(r[5] for r in rs)
    if sizes:
        print(f"    top-class sizes min/median/max: "
              f"{sizes[0]}/{sizes[len(sizes)//2]}/{sizes[-1]}")
    # how many DISTINCT priorities did the law ever produce on real code
    seen = set()
    for r in rs:
        seen |= set(r[3])
    print(f"    distinct priorities produced: {sorted(seen)}")

print("\n== how many observations are in a tie (class size > 1) ==")
for shape in ("assert", "trace"):
    rs = [r for r in rows if r[1] == shape]
    tied = sum(sum(v for v in r[3].values() if v > 1) for r in rs)
    tot = sum(r[2] for r in rs)
    print(f"  {shape}: {tied}/{tot} observations sit in a class of >1 "
          f"({100.0*tied/tot:.1f}%)")
