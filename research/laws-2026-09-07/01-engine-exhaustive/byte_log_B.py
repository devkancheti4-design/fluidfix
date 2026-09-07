#!/usr/bin/env python
"""Fixture B: reach BUILT+CAPPED (byte 33) in the loop and log what byte the
guard's SECOND consult (guard.py:539) receives afterwards.

Taught kind 4 on `K = ` yields ["K = 1", "K = 2"]; the test passes only for
K == 1 and sleeps 2.5s in that case, so the one green plus its confirm run
carry the clock past the first-pass deadline (budget/3 = 5s) before the loop
reaches the next kind/observation -> loop rules on BUILT+CAPPED. src/ untouched:
`decide` is patched on the engine module from this process only.
Run: .venv/bin/python byte_log_B.py <workdir>
"""
import pathlib
import re
import sys
import tempfile
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.engine as E   # noqa: E402
import fluidfix.loop as L     # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402
from fluidfix.acts import register  # noqa: E402

log = []
_orig = E.decide


def spy(sit):
    act = _orig(sit)
    log.append((round(time.time() - T0, 1), sit & 0xFF,
                "+".join(b for i, b in enumerate(E.BITS) if sit >> i & 1) or "(none)", act))
    return act


E.decide = spy
L.decide = spy

register(4, "k-demo", "K = 0 should be K = 1", re.compile(r"K = "),
         lambda line, o: ["K = 1", "K = 2"])
work = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(dir=str(pathlib.Path(__file__).parent)))
work.mkdir(parents=True, exist_ok=True)
(work / "mod.py").write_text("K = 0\nLIMIT = 5\n\ndef f():\n    return K\n\ndef g(x):\n    return x + LIMIT\n")
(work / "test_mod.py").write_text(
    "import time\nfrom mod import f, g, K\n\ndef test_f():\n"
    "    if K == 1:\n        time.sleep(2.5)\n    assert f() == 1\n\n"
    "def test_g():\n    assert g(1) == 6\n")
oracle = Oracle(str(work), python=sys.executable)
T0 = time.time()
rep = guard_once(oracle, MechanicalObserver(), budget=15)
print(f"status={rep.status!r} file={rep.file!r} seconds={rep.seconds:.1f}")
print(f"guard hint = {rep.hint!r}")
r = rep.result
if r is not None:
    print(f"loop result: repaired={r.repaired} ambiguous={r.ambiguous} greens={r.greens} acts_tried={r.acts_tried}")
    print(f"loop reason = {r.reason!r}")
print(f"tree untouched: {(work / 'mod.py').read_text().startswith('K = 0')}")
print("bytes handed to decide(), in order (t seconds since start):")
for t, b, names, act in log:
    print(f"    t={t:5.1f}  x={b:3d} {names:<22} -> {act}")
