"""26-router-exhaustive: log every route() call during real repairs.

Wraps fluidfix.acts.route (the module-level name loop.py's act_for resolves)
in this process only; src/ is never edited. Builds one tiny fixture per shipped
fault kind (fixtures_def.py) in this directory, runs the real repair loop on each, and prints every
(F1, A1, Fq) -> act the body actually produced.

Run: ./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python live_trace.py
"""
import os
import shutil
import sys
import textwrap

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fluidfix import MechanicalObserver, Oracle, build_packet, repair  # noqa: E402
from fluidfix import acts as A  # noqa: E402

CALLS = []
_real = A.route


def _traced(F1, A1, Fq):
    r = _real(F1, A1, Fq)
    CALLS.append((F1, A1, Fq, r))
    return r


A.route = _traced

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "fixtures")
shutil.rmtree(WORK, ignore_errors=True)

from fixtures_def import FIXTURES  # noqa: E402

print(f"{'fixture':<18} {'repaired':>8} {'suite runs':>10}  route calls "
      f"(F1,A1,Fq)->act")
rows = []
for name, (src, test) in FIXTURES.items():
    d = os.path.join(WORK, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "mod.py"), "w").write(textwrap.dedent(src))
    open(os.path.join(d, "test_mod.py"), "w").write(textwrap.dedent(test))
    oracle = Oracle(d, python=sys.executable)
    CALLS.clear()
    packet = build_packet(oracle, "mod.py", coverage_target="mod")
    obs = MechanicalObserver().observe([packet])[0] if packet else []
    res = repair(oracle, "mod.py", obs)
    seen = []
    for c in CALLS:
        if c not in seen:
            seen.append(c)
    rows.append((name, res, list(CALLS)))
    print(f"{name:<18} {str(res.repaired):>8} {res.suite_runs:>10}  "
          f"{[f'({a},{b},{c})->{d_}' for a, b, c, d_ in seen]}")
    if res.repaired:
        print(f"{'':<18} new line: {res.new_line.strip()!r}")
    else:
        print(f"{'':<18} refusal: {res.reason[:90]!r}")

print("\n-- every distinct (F1,A1) pair the body produced across all fixtures:")
allpairs = {(a, b) for _, _, cs in rows for a, b, _, _ in cs}
print(f"   {sorted(allpairs)}")
allq = {c for _, _, cs in rows for _, _, c, _ in cs}
print(f"-- every distinct Fq (fault kind) the body produced: {sorted(allq)}")
print(f"-- every distinct act produced: "
      f"{sorted({d_ for _, _, cs in rows for *_, d_ in cs})}")
