#!/usr/bin/env python
"""What the body does with the law's ruling on observation byte 0.

Fixture: a one-line defect on a line the mechanical observer reports NOTHING
for (no digit, no comparison, no spaced operator), so no act is generated and
nothing is truncated. guard.py:539 then packs CAPPED=False, REFUTED=False —
observation byte 0 — and the law rules SHIP.

This script records, for that single run:
  1. every byte handed to decide() and the ruling,
  2. the guard's status and hint,
  3. the user-visible summary() text,
  4. the hint written into .fluidfix/last_refusal.json,
so the ruling and the actuation can be compared side by side.

src/ is NOT modified: `decide` is patched on the engine/loop modules inside
this process only.
Run: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python byte0_actuation.py <workdir>
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.engine as E   # noqa: E402
import fluidfix.loop as L     # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402
from fluidfix.guard import write_refusal  # noqa: E402

log = []
_orig = E.decide


def spy(sit):
    act = _orig(sit)
    log.append((sit & 0xFF,
                "+".join(b for i, b in enumerate(E.BITS) if sit >> i & 1) or "(none)",
                act))
    return act


E.decide = spy
L.decide = spy

work = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                    else tempfile.mkdtemp(dir=str(pathlib.Path(__file__).parent)))
work.mkdir(parents=True, exist_ok=True)
(work / "mod.py").write_text("def f(x):\n    return x\n")   # want x.upper()
(work / "test_mod.py").write_text(
    "from mod import f\n\ndef test_f():\n    assert f('a') == 'A'\n")

oracle = Oracle(str(work), python=sys.executable)
rep = guard_once(oracle, MechanicalObserver())

print("1. bytes handed to the engine law, in order:")
for b, nm, act in log:
    print(f"     x={b:3d} {nm:<22} -> law rules {act}")
print(f"2. guard status={rep.status!r}  hint={rep.hint!r}  attempts={len(rep.attempts)}")
print("3. user-visible summary():")
print("     " + rep.summary().replace("\n", "\n     "))
path = write_refusal(str(work), rep)
print("4. .fluidfix/last_refusal.json hint:")
print("     " + json.dumps(json.load(open(path))["hint"]))
print(f"5. any ACT NAME from the law present in the user-visible text? "
      f"{[a for a in E.ACTS if a in rep.summary()] or 'NONE'}")
print(f"6. tree untouched: {(work / 'mod.py').read_text() == chr(100) + 'ef f(x):' + chr(10) + '    return x' + chr(10)}")
os.sync() if hasattr(os, "sync") else None
