"""HOW MUCH would have been enough? Run exactly the work the escalation pass
does on the span fixture — the rank-1 file with FULL SIGHT (untruncated
packet) — with NO deadline, and stop at the first suite-green candidate.
That time is the budget the escalation pass actually needed.

usage: run_span_fullsight.py OUTDIR
"""
import itertools, json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import probe
probe.install()
from fluidfix import MechanicalObserver, Oracle
from fluidfix.guard import rank_observations
from fluidfix.localize import build_packet
from fluidfix import loop as L

out = sys.argv[1]
root = tempfile.mkdtemp(prefix="fullsight-", dir=out)
names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
filler = [f"f_{n} = True" for n in names]
fn = ["", "def tier(v, limit):", "    if v > limit:",
      "        return 1", "    return 0", ""]
open(os.path.join(root, "test_mod.py"), "w").write(
    "from mod import tier\n\ndef test_t():\n"
    "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(root, python=sys.executable)
body = filler[:400] + fn + filler[400:]
open(os.path.join(root, "mod.py"), "w").write("\n".join(body) + "\n")
bug_lineno = 403
pk0 = build_packet(oracle, "mod.py")
print("pass0 packet: lines=%d truncated=%s bug_in=%s"
      % (len(pk0.lines), pk0.truncated, bug_lineno in pk0.lines), flush=True)

# what escalation builds: 990, then unbounded if still truncated
pk = build_packet(oracle, "mod.py", max_lines=990)
if pk.truncated:
    pk = build_packet(oracle, "mod.py", max_lines=10 ** 9)
print("full-sight packet: lines=%d truncated=%s bug_in=%s"
      % (len(pk.lines), pk.truncated, bug_lineno in pk.lines), flush=True)
fails, o = oracle.failing_output()
obs = rank_observations("\n".join(pk.src_lines),
                        MechanicalObserver().observe([pk])[0], o,
                        root=oracle.root, rel="mod.py")
print("observations: %d ; rank of the bug line %d: %s"
      % (len(obs), bug_lineno,
         next((i for i, x in enumerate(obs) if x.lineno == bug_lineno), None)),
      flush=True)

class FirstGreen(Exception):
    pass

_c = oracle.check
def c(timeout=None):
    r = _c(timeout=timeout)
    if r[0]:
        raise FirstGreen()      # stop the clock at the first green
    return r
oracle.check = c

import time
t0 = time.time()
try:
    res = L.repair(oracle, "mod.py", obs)
    stopped = "search finished; repaired=%s" % res.repaired
except FirstGreen:
    stopped = "FIRST GREEN"
took = time.time() - t0
rows = probe.ROWS
green = [r for r in rows if r["ok"]]
print("STOP %s  after %.1fs  candidates judged=%d" % (stopped, took, len(rows)),
      flush=True)
if rows:
    print("last candidate site: line %s at t=%.1f" % (rows[-1]["line"], rows[-1]["t"]),
          flush=True)
probe.dump(os.path.join(out, "span_fullsight.json"))
json.dump({"stopped": stopped, "seconds": took, "rows": len(rows),
           "pass0_packet_lines": len(pk0.lines),
           "fullsight_packet_lines": len(pk.lines),
           "n_obs": len(obs), "bug_lineno": bug_lineno,
           "bug_obs_rank": next((i for i, x in enumerate(obs)
                                 if x.lineno == bug_lineno), None)},
          open(os.path.join(out, "span_fullsight_summary.json"), "w"), indent=1)
shutil.rmtree(root, ignore_errors=True)
print("DONE", flush=True)
