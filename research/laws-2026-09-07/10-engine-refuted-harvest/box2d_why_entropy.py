"""How much does a harvested counterexample TELL you on the C path?

The recorded Box2D refusal on src/contact_solver.c tried 1,063 candidates
(docs/PAIR_LAW_PROMPT.md:30, src/fluidfix/pair.py:50).  Each rejection the
body keeps is {at, tried, why}, where `why` comes from COracle.check().
This script samples wrong candidates from that file, runs each through the
REAL COracle.check(), and counts how many DISTINCT `why` strings the harvest
would hold — i.e. how much a harvested counterexample discriminates.

Every candidate is applied to a private COPY of Box2D in this directory and
the file is restored byte-exactly after each check.

usage: box2d_why_entropy.py [max_candidates]
"""
import os, sys, time
from collections import Counter

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "box2d")
REL = "src/contact_solver.c"
PATH = os.path.join(ROOT, REL)
MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 12

# Hand-built sample of single-token mutations, one per distinct line, of the
# same shapes fluidfix's shipped vocabulary generates (operator flip,
# off-by-one, comparison flip, constant drift).  NOT produced by acts.py --
# stated plainly so the number is not mistaken for the law's own generator.
MUTANTS = [
    (2032, "constraints + wideIndex", "constraints - wideIndex"),
    (2032, "constraints + wideIndex", "constraints + wideIndex + 1"),
    (2032, "constraints + wideIndex", "constraints + wideIndex - 1"),
]

def find_more(lines, want):
    """More sample sites: distinct lines carrying a mutable token."""
    out = []
    seen = set()
    pats = [("+ 1", "+ 2"), ("- 1", "- 2"), ("0.5f", "0.25f"),
            ("< count", "<= count"), ("> 0.0f", ">= 0.0f"),
            ("* 2", "* 3"), ("+= 1", "+= 2")]
    for i, l in enumerate(lines, 1):
        if len(out) >= want:
            break
        if i in seen or i < 100:
            continue
        s = l.strip()
        if not s or s.startswith(("//", "*", "/*", "#")):
            continue
        for a, b in pats:
            if a in l:
                out.append((i, a, b))
                seen.add(i)
                break
    return out

src = open(PATH, encoding="utf-8", newline="").read()
lines = src.split("\n")
MUTANTS += find_more(lines, MAX - len(MUTANTS))
MUTANTS = MUTANTS[:MAX]

oracle = COracle(ROOT, build_cmd="cmake --build build -j4",
                 test_cmd="./build/bin/test", build_dir="build", timeout=300)
print("build:", oracle.build_cmd, "| test:", oracle.test_cmd)
print("baseline green:", oracle.green(timeout=300))
oracle._pristine_checked = True

rows = []
try:
    for (ln, a, b) in MUTANTS:
        old = lines[ln - 1]
        if a not in old:
            print(f"  skip {REL}:{ln} (pattern {a!r} not on the line)")
            continue
        new = list(lines)
        new[ln - 1] = old.replace(a, b, 1)
        open(PATH, "w", encoding="utf-8", newline="").write("\n".join(new))
        t0 = time.time()
        ok, why = oracle.check(timeout=300)
        dt = time.time() - t0
        open(PATH, "w", encoding="utf-8", newline="").write(src)
        rows.append((ln, old.strip()[:48], new[ln - 1].strip()[:48], ok, why, dt))
        print(f"  {REL}:{ln:5d} {dt:5.1f}s ok={ok} why={why[:90]!r}")
finally:
    open(PATH, "w", encoding="utf-8", newline="").write(src)
    print("restored", REL, "byte-exact:",
          open(PATH, encoding="utf-8", newline="").read() == src)

print()
print(f"candidates checked: {len(rows)}")
print(f"green (accidentally passing): {sum(1 for r in rows if r[3])}")
whys = Counter(r[4] for r in rows if not r[3])
print(f"rejections: {sum(whys.values())}  DISTINCT why values: {len(whys)}")
for w, n in whys.most_common():
    print(f"  {n:3d}  {w[:120]!r}")
tot = sum(r[5] for r in rows)
print(f"total wall time {tot:.1f}s, mean per candidate {tot/max(len(rows),1):.2f}s")
