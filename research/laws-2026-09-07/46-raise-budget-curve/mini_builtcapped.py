"""BUILT+CAPPED, in 10 seconds: a green IS found, then the deadline cuts the
uniqueness proof. Shows what repair() returns and what the guard then does
with it. (The span fixture takes 240s to reach the same state.)"""
import os, sys, tempfile, time, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import probe; probe.install()
from fluidfix import MechanicalObserver, Oracle
from fluidfix.guard import rank_observations
from fluidfix.localize import build_packet
from fluidfix import loop as L

out = sys.argv[1]
root = tempfile.mkdtemp(prefix="mini-", dir=out)
fn = ["def tier(v, limit):", "    if v > limit:", "        return 1",
      "    return 0", ""]
filler = [f"K_{i} = {i}" for i in range(120)]
open(os.path.join(root, "mod.py"), "w").write("\n".join(fn + filler) + "\n")
open(os.path.join(root, "test_mod.py"), "w").write(
    "from mod import tier\n\ndef test_t():\n"
    "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
o = Oracle(root, python=sys.executable)
fails, out_txt = o.failing_output()
pk = build_packet(o, "mod.py", max_lines=10**9)
obs = rank_observations("\n".join(pk.src_lines),
                        MechanicalObserver().observe([pk])[0], out_txt,
                        root=o.root, rel="mod.py")
print("observations:", len(obs), "first sites:", [x.lineno for x in obs[:5]])
t0 = time.time()
res = L.repair(o, "mod.py", obs, deadline=time.time() + 10)
print("elapsed %.1fs" % (time.time() - t0))
print("repaired =", res.repaired, "| ambiguous =", res.ambiguous,
      "| greens =", res.greens)
print("reason   =", res.reason)
print("--- what guard.py's escalation loop does with this result ---")
print("guard.py:598-608 tests result.repaired (False) and result.ambiguous "
      "(False) -> `continue`; the reason above is never carried into the "
      "GuardReport. guard.py:610-614 then hardcodes situation(REFUTED=True).")
shutil.rmtree(root, ignore_errors=True)
