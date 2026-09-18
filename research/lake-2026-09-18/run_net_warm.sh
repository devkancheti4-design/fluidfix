#!/bin/bash
# The same incident the cold net is grinding through now, but with the shape already known — the
# difference between a first encounter and a remembered one, measured on the same fault.
set -u; L=$1; R=$2; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
D=/Users/kanchetidevieswar/neo/fluidfix/examples/taught-2026-09-16/rules_session.py
until grep -q NET_DONE net.log 2>/dev/null; do sleep 20; done
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from life import Life
l = Life("net_memory_warm.json"); l.learn("shapes", "kind:6"); l.save()
print("seeded: the net already knows the inverted-guard shape")
PY
MEM=net_memory_warm.json python3 - <<'PY'
import os, subprocess, sys
env = dict(os.environ, PYTHONPATH="/Users/kanchetidevieswar/neo/fluidfix/src")
# point net.py at the warm memory by swapping the file it opens
import pathlib, shutil
shutil.copy("net_memory_warm.json", "net_memory.json")
sys.exit(subprocess.run([sys.executable, "net.py",
    os.environ["L"], "rich/notdrop-1", "--template", os.environ["R"],
    "--dictionary", os.environ["D"], "--max-nodes", "200", "--width", "24", "--fanout", "4"],
    env=env).returncode)
PY
echo NET_WARM_DONE
