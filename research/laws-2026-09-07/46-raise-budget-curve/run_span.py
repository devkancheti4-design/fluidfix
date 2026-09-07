"""Progress-rate curve on the span fixture.

Replicates tests/test_span_edits.py::test_budget_hands_first_pass_over_to_
escalation verbatim (the ONLY fixture in that file that reaches the
CAPPED -> RAISE_BUDGET escalation lane) inside our own tmp dir, with probe.py
recording every suite-judged candidate and its timestamp.

usage: run_span.py OUTDIR BUDGET
"""
import itertools, json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import probe
probe.install()
from fluidfix import MechanicalObserver, Oracle, guard_once
from fluidfix.localize import build_packet

out, budget = sys.argv[1], (int(sys.argv[2]) if len(sys.argv) > 2 else 450)
root = tempfile.mkdtemp(prefix="span-", dir=out)
names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
filler = [f"f_{n} = True" for n in names]
fn = ["", "def tier(v, limit):", "    if v > limit:",
      "        return 1", "    return 0", ""]
open(os.path.join(root, "test_mod.py"), "w").write(
    "from mod import tier\n\ndef test_t():\n"
    "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
oracle = Oracle(root, python=sys.executable)
placed = None
for pad in range(6):
    body = filler[:400 + pad] + fn + filler[400 + pad:]
    bug_lineno = (400 + pad) + 3
    open(os.path.join(root, "mod.py"), "w").write("\n".join(body) + "\n")
    pk = build_packet(oracle, "mod.py")
    if pk is not None and pk.truncated and bug_lineno not in pk.lines:
        placed = {"pad": pad, "bug_lineno": bug_lineno,
                  "packet_lines": len(pk.lines), "truncated": pk.truncated,
                  "file_lines": len(body)}
        break
assert placed, "could not place the bug outside the first-pass sample"
print("PLACED", json.dumps(placed), flush=True)

rep = guard_once(oracle, MechanicalObserver(), budget=budget)
print("STATUS", rep.status, "seconds", round(rep.seconds, 2),
      "file", rep.file,
      "new_line", (rep.result.new_line.strip() if rep.result and
                   getattr(rep.result, "new_line", None) else None), flush=True)
print("HINT", (rep.hint or "")[:300], flush=True)
probe.ROWS and None
import probe as P
P.dump(os.path.join(out, "span_budget%d.json" % budget))
json.dump({"placed": placed, "status": rep.status,
           "seconds": rep.seconds, "file": rep.file,
           "candidates": rep.candidates,
           "new_line": (rep.result.new_line.strip() if rep.result and
                        getattr(rep.result, "new_line", None) else None),
           "hint": rep.hint},
          open(os.path.join(out, "span_budget%d_summary.json" % budget), "w"),
          indent=1)
shutil.rmtree(root, ignore_errors=True)
print("DONE", flush=True)
