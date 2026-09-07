#!/usr/bin/env python
"""Re-rule the 22 authoring events (read-only copy of the private dev repo's
ENGINE_LAW.py, fetched with `gh api` into dev_repo/) through fluidfix's
VENDORED engine.decide(). fluidfix's situation() pins job=2 (DEBUG); the law
is job-invariant (0 of 256 differ), so the job column is bookkeeping.
Prints every event, flags the SELF ones.
Rerun: .venv/bin/python events_check.py
"""
import ast, sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, ACTS, BITS

src = open(__file__.rsplit("/", 1)[0] + "/dev_repo/ENGINE_LAW.py").read()
tree = ast.parse(src)
events = None
for node in tree.body:
    if isinstance(node, ast.Assign) and node.targets[0].id == "EVENTS":
        events = ast.literal_eval(node.value)
assert events is not None
print(f"events in upstream ENGINE_LAW.py: {len(events)}")
ok = 0
self_events = []
for job, obs, act, note in events:
    got = decide(situation(**obs))
    want = ACTS[act]
    hit = got == want
    ok += hit
    flag = "SELF" if obs.get("SELF") else "    "
    bits = "+".join(b for b in BITS if obs.get(b))
    print(f"  {flag} {job:<10} {bits:<16} want {want:<22} got {got:<22} {'ok' if hit else 'MISMATCH'}")
    if obs.get("SELF"):
        self_events.append((job, bits, want, note))
print(f"reproduced under fluidfix's vendored law: {ok}/{len(events)}")
print()
print("the SELF events, with the authoring note:")
for job, bits, want, note in self_events:
    print(f"  {job:<10} {bits:<16} -> {want}")
    print(f"      {note.strip()}")
