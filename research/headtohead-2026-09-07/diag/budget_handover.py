"""Did 0.15.0 slow the search, or break the escalation handover?
Same fixture as tests/test_span_edits.py::test_budget_hands_first_pass_over_to_escalation,
run at two budgets. Repairs at the larger one -> the handover works and the test
threshold is stale. Refuses at both -> something broke."""
import sys, itertools, pathlib, tempfile, time
sys.path.insert(0, "src")
from fluidfix.oracle import Oracle
from fluidfix.guard import guard_once, build_packet
from fluidfix.observers import MechanicalObserver
names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
filler = [f"f_{n} = True" for n in names]
fn = ["", "def tier(v, limit):", "    if v > limit:", "        return 1", "    return 0", ""]
for budget in (450, 900):
    d = pathlib.Path(tempfile.mkdtemp())
    (d/"test_mod.py").write_text("from mod import tier\n\ndef test_t():\n    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
    o = Oracle(str(d), python=sys.executable)
    placed = False
    for pad in range(6):
        body = filler[:400+pad] + fn + filler[400+pad:]; bug = (400+pad)+3
        (d/"mod.py").write_text("\n".join(body)+"\n")
        pk = build_packet(o, "mod.py")
        if pk is not None and pk.truncated and bug not in pk.lines: placed = True; break
    if not placed: print(f"budget={budget}: could not place the bug", flush=True); continue
    t0=time.time(); r = guard_once(o, MechanicalObserver(), budget=budget)
    print(f"budget={budget:>4}  status={r.status:<8} {time.time()-t0:6.1f}s  ruling={getattr(r.result,'ruling','')}  "
          f"line={getattr(r.result,'new_line','') or (r.hint or '')[:70]!r}", flush=True)
