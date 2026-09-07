#!/usr/bin/env python
"""framed fixture: run guard_once with the file list the widened ranking
would have produced (api.py then core.py) — the body's own --file path.
Measures what the repair costs once core.py is merely OFFERED."""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import MechanicalObserver, Oracle
from fluidfix.guard import guard_once
src = os.path.join(HERE, "fixtures", "framed"); root = os.path.join(HERE, "work", "framed-offered")
if os.path.isdir(root): shutil.rmtree(root)
shutil.copytree(src, root)
oracle = Oracle(root, python=sys.executable)
t0 = time.time()
rep = guard_once(oracle, MechanicalObserver(), files=["pkg/api.py", "pkg/core.py"])
print(f"status={rep.status} file={rep.file} seconds={time.time()-t0:.1f}")
if rep.result: r = rep.result; print(f"lineno={r.lineno} old={r.old_line.strip()!r} new={r.new_line.strip()!r} suite_runs={r.suite_runs} reason={r.reason!r}")
print("green after:", oracle.green())
