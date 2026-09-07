#!/usr/bin/env python
"""Log every observation byte the BODY hands to the engine law on a fixture.

Patches the `decide` name imported into fluidfix.guard / fluidfix.loop from
this script's own process (src/ is untouched). Fixture A: a defect on a line
the mechanical observer reports NOTHING for (no digit, comparison, operator),
so no act is tried and nothing is capped -> does guard.py:539 hand byte 0 to
the law?  Run: .venv/bin/python byte_log.py <workdir>
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.engine as E   # noqa: E402
import fluidfix.guard as G    # noqa: E402
import fluidfix.loop as L     # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402

log = []
_orig = E.decide


def spy(sit):
    act = _orig(sit)
    log.append((sit & 0xFF, "+".join(b for i, b in enumerate(E.BITS) if sit >> i & 1) or "(none)", act))
    return act


E.decide = spy   # guard_once does `from .engine import decide` inside the function
L.decide = spy

work = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(dir=str(pathlib.Path(__file__).parent)))
work.mkdir(parents=True, exist_ok=True)
(work / "mod.py").write_text("def f(x):\n    return x\n")            # bug: should return x.upper(); no observable kind
(work / "test_mod.py").write_text("from mod import f\n\ndef test_f():\n    assert f('a') == 'A'\n")
oracle = Oracle(str(work), python=sys.executable)
rep = guard_once(oracle, MechanicalObserver())
print(f"status={rep.status!r} file={rep.file!r} candidates={rep.candidates}")
print(f"hint={rep.hint!r}")
print("bytes handed to decide(), in order:")
for b, names, act in log:
    print(f"    x={b:3d} {names:<22} -> {act}")
