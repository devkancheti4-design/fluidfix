#!/usr/bin/env python
"""Fixture C: the SAME misdirection as `named`, plus ONE extra observation.

`named` is the click-shaped click shape: tests/test_shell.py fails with a
pure assertion, pkg/shell.py shares the token "shell" with the test module
(NAMED) and is executed by that test alone (FAILONLY), while the defect
lives in pkg/types.py, which every test executes (UBIQUITOUS penalty).
Measured order there: shell.py 1st (p=2), types.py 6th of 6 (p=6).

This variant changes NOTHING about the defect, the decoy, or the file set.
It only makes the failing assertion PRINT a value that occurs in one source
file: pkg/types.py grows `BUCKET = 95` and a tag() that renders it, so the
AssertionError line reads

    assert 'b95:a b c d' == 'b95:a b c'

and guard.py's assert-literal scan finds 95 in exactly one of six files.
That is the LITERAL lane — a POINTING bit — and R2 says the UBIQUITOUS
penalty is algebraically unreachable once any POINTING bit is set.

Report-only: builds a fresh copy under work/, edits nothing in src/.

    nice -n 15 ./tmo.sh 300 .venv/bin/python literal_variant.py
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fluidfix.sight as sight_mod                        # noqa: E402
from fluidfix import MechanicalObserver, Oracle            # noqa: E402
from fluidfix.guard import find_candidate_files, guard_once  # noqa: E402
from fluidfix.sight import BITS, sight                     # noqa: E402

RECORDED: dict[str, int] = {}
_real = sight_mod.observe_bits


def _rec(**kw):
    b = _real(**kw)
    rel = sys._getframe(1).f_locals.get("rel")
    if rel is not None:
        RECORDED[rel] = b
    return b


def bits_of(b):
    return "|".join(x for i, x in enumerate(BITS) if b >> i & 1) or "-"


def build(root):
    """fixtures/named + the discriminating literal, nothing else."""
    src = os.path.join(HERE, "fixtures", "named")
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(src, root)

    # 1. types.py (the DEFECT file, untouched defect) gains the value.
    p = os.path.join(root, "pkg", "types.py")
    text = open(p, encoding="utf-8").read()
    text = text.replace(
        'DEFAULT_WIDTH = 80',
        'DEFAULT_WIDTH = 80\nBUCKET = 95\n\n\ndef tag():\n'
        '    """Render this module\'s bucket id."""\n'
        '    return "b" + str(BUCKET) + ":"', 1)
    open(p, "w", encoding="utf-8").write(text)

    # 2. shell.py (the NAMED decoy) prefixes the tag. It never spells 95.
    p = os.path.join(root, "pkg", "shell.py")
    text = open(p, encoding="utf-8").read()
    text = text.replace(
        '    return " ".join(str(k) for k in kept)',
        '    return types.tag() + " ".join(str(k) for k in kept)', 1)
    open(p, "w", encoding="utf-8").write(text)

    # 3. the failing assertion now prints the value.
    p = os.path.join(root, "tests", "test_shell.py")
    open(p, "w", encoding="utf-8").write(
        'from pkg import shell\n\n\n'
        'def test_render_respects_limit():\n'
        '    assert shell.render(["a", "b", "c", "d"], 3) == "b95:a b c"\n')
    return root


def main():
    root = build(os.path.join(HERE, "work", "named-literal"))
    oracle = Oracle(root, python=sys.executable)
    fails, out = oracle.failing_output()
    print(f"# fixture named-literal -> {root}")
    print(f"# failing: {fails}")
    for line in out.splitlines()[-14:]:
        print("   |", line)

    sight_mod.observe_bits = _rec
    try:
        ev: dict = {}
        order = find_candidate_files(oracle, out, evidence=ev)
    finally:
        sight_mod.observe_bits = _real
    print("\n# find_candidate_files order:")
    for i, rel in enumerate(order, 1):
        b = RECORDED.get(rel)
        if b is None:
            print(f"   {i}. {rel:<18} SIGHT NOT CONSULTED (frame branch)")
        else:
            print(f"   {i}. {rel:<18} byte=0x{b:02x} {bits_of(b):<34} "
                  f"priority={sight(b)}")
    print(f"# evidence: {json.dumps(ev)}")

    # per-file ledger, exactly as run_measure.py builds it
    import fluidfix.guard as guard_mod
    _rr, _rp = guard_mod.repair, guard_mod.build_packet
    ledger: list[dict] = []
    secs: dict[str, float] = {}

    def _p(o, rel, *a, **kw):
        t = time.time()
        r = _rp(o, rel, *a, **kw)
        secs[rel] = secs.get(rel, 0.0) + (time.time() - t)
        return r

    def _r(o, rel, obs, **kw):
        t = time.time()
        r = _rr(o, rel, obs, **kw)
        ledger.append({"file": rel, "suite_runs": r.suite_runs,
                       "repair_s": round(time.time() - t, 1),
                       "repaired": r.repaired, "reason": r.reason[:60]})
        return r

    # optional: literal_variant.py 15  -> guard_once(budget=15)
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else None
    guard_mod.repair, guard_mod.build_packet = _r, _p
    t0 = time.time()
    try:
        rep = guard_once(oracle, MechanicalObserver(), budget=budget)
    finally:
        guard_mod.repair, guard_mod.build_packet = _rr, _rp
    print("\n# per-file ledger:")
    for e in ledger:
        print("   ", json.dumps(e))
    print(f"# suite runs on WRONG files: "
          f"{sum(e['suite_runs'] for e in ledger if not e['repaired'])}, "
          f"on the repaired file: "
          f"{sum(e['suite_runs'] for e in ledger if e['repaired'])}")
    print(f"\n# guard_once -> status={rep.status} file={rep.file} "
          f"seconds={time.time() - t0:.1f}")
    if rep.result is not None:
        r = rep.result
        print(f"# result: lineno={r.lineno} old={r.old_line.strip()!r} "
              f"new={r.new_line.strip()!r} suite_runs={r.suite_runs} "
              f"reason={r.reason!r}")
    print("# green after:", oracle.green())
    return 0


if __name__ == "__main__":
    sys.exit(main())
