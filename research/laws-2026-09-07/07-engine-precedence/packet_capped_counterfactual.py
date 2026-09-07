#!/usr/bin/env python
"""07-engine-precedence, counterfactual: the SAME broken fixture as
packet_capped_fixture.py, but repair() is given the FULL (untruncated) packet
— i.e. what the RAISE_BUDGET lane's full-sight escalation would see if the
guard had delivered packet-CAPPED into the byte at loop.py:217.

Run (one real suite run, under nice + the timeout shim next to this file):
    cd <this dir> && nice -n 15 ./timeout.sh 300 \\
        /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python packet_capped_counterfactual.py
"""
import itertools
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import MechanicalObserver, Oracle, repair           # noqa: E402
from fluidfix.guard import rank_observations                      # noqa: E402
from fluidfix.localize import build_packet                        # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fixture-packet-capped-full"
COMPENSATOR = "    return grade(v - 0, limit)"
BUG = "    if v > limit:"

names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
body = ["x = None", "y = None", "", "def tier(v, limit):", COMPENSATOR, ""]
body += [f"f_{n} = x and y" for n in names]
body += ["", "def grade(v, limit):", BUG, "        return 1", "    return 0", ""]
if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir()
(ROOT / "mod.py").write_text("\n".join(body) + "\n")
(ROOT / "test_mod.py").write_text(
    "from mod import tier\n\ndef test_t():\n"
    "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
src = (ROOT / "mod.py").read_text()
oracle = Oracle(str(ROOT), python=sys.executable)

pk = build_packet(oracle, "mod.py", max_lines=5000)      # full sight
print(f"full packet: truncated={pk.truncated} lines={len(pk.lines)}")
fails, out = oracle.failing_output()
obs = rank_observations("\n".join(pk.src_lines),
                        MechanicalObserver().observe([pk])[0], out,
                        root=oracle.root, rel="mod.py")
res = repair(oracle, "mod.py", obs)
print(f"repaired   = {res.repaired}")
print(f"ambiguous  = {res.ambiguous}")
print(f"suite_runs = {res.suite_runs}")
print(f"greens     = {res.greens}")
print(f"reason     = {res.reason}")
print(f"tree untouched = {(ROOT / 'mod.py').read_text() == src}")
