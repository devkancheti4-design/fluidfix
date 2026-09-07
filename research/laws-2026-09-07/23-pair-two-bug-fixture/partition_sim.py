#!/usr/bin/env python3
"""What the PARTITION ruling would be worth, measured.

The law rules PARTITION on this fixture (byte 23). Nothing in the body
actuates it. This script does by hand exactly what PARTITION says — repair
the disjoint groups one at a time, linearly — using ONLY edits the completed
single-edit search already found, and then re-runs the UNMODIFIED guard on
the residue. Report-only; works in ./work3/.
"""
import os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/kanchetidevieswar/neo/fluidfix"
PY = os.path.join(REPO, ".venv", "bin", "python")
FF = os.path.join(REPO, ".venv", "bin", "fluidfix")
W = os.path.join(HERE, "work3")
if os.path.exists(W):
    shutil.rmtree(W)
os.makedirs(W)
root = os.path.join(W, "repo")
shutil.copytree(os.path.join(HERE, "fixture"), root)

def suite():
    p = subprocess.run([PY, "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider", "--tb=no"], cwd=root,
                       capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1]

def guard():
    t = time.time()
    p = subprocess.run([FF, "guard", root, "--python", PY],
                       capture_output=True, text=True, timeout=280)
    return p.returncode, p.stdout.strip(), time.time() - t

print("baseline:", suite())
rc, out, s = guard()
print(f"GUARD PASS 1 on the un-partitioned repo (exit {rc}, {s:.1f}s):")
print("   " + "\n   ".join(out.splitlines()[:2]))
print("after pass 1:", suite())

# PARTITION step 1: apply the reducer the search itself found for group 1
p = os.path.join(root, "billing.py")
src = open(p).read().split("\n")
src[12] = "    return subtotal + tax"
open(p, "w").write("\n".join(src))
print("\nPARTITION step 1 applied (billing.py:13 <- the search's own "
      "strict reducer):", suite())

rc, out, s = guard()
print(f"GUARD PASS 2 on the residue (exit {rc}, {s:.1f}s):")
print("   " + "\n   ".join(out.splitlines()[:4]))
print("after pass 2:", suite())
print("\ninventory.py:11 is now:",
      repr(open(os.path.join(root, "inventory.py")).read().split("\n")[10]))
