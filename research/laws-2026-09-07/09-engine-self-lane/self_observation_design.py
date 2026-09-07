#!/usr/bin/env python
"""DESIGN ONLY (report artefact, src/ untouched): a mechanical SELF observation.

SELF in the authoring table is "the job IS the worker". For fluidfix that is
the case where the thing under repair and the thing doing the repairing are
the same artefact. Three disjoint, purely mechanical predicates cover it, all
computable from values guard_once() already holds at its own call site
(oracle.root, the candidate file path, the target's test files):

  S1 SELF_TARGET  the repo under repair CONTAINS the running fluidfix package
                  -> the guard may edit the code that is currently executing.
  S2 SELF_ORACLE  the candidate file is part of the suite that judges it
                  (a test file / conftest.py of the target) -> the repair can
                  green the suite by editing the checker.
  S3 SELF_LAW     the candidate file is one of the six vendored law modules
                  -> the guard would be editing its own decider.

This script COMPUTES the predicate on real inputs and prints the observation
byte the body would then hand the law, plus the ruling with and without SELF.
It repairs nothing and edits nothing outside this directory.

Rerun: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python self_observation_design.py
"""
import os
import sys
import tempfile

FF_SRC = "/Users/kanchetidevieswar/neo/fluidfix/src"
sys.path.insert(0, FF_SRC)

import fluidfix
from fluidfix.engine import BITS, decide, situation

PKG_DIR = os.path.dirname(os.path.abspath(fluidfix.__file__))
LAW_MODULES = {"engine.py", "rank.py", "sight.py", "pair.py", "router.py",
               "lanes.py"}


def _inside(path, root):
    path, root = os.path.abspath(path), os.path.abspath(root)
    return path == root or path.startswith(root + os.sep)


def self_target(root):
    """S1: does the tree under repair contain the fluidfix package that is
    doing the repairing?"""
    return _inside(PKG_DIR, root)


def self_oracle(root, candidate_file):
    """S2: is the candidate file part of the suite that adjudicates it?"""
    base = os.path.basename(candidate_file)
    if not _inside(candidate_file, root):
        return False
    return base == "conftest.py" or base.startswith("test_") or \
        base.endswith("_test.py")


def self_law(candidate_file):
    """S3: is the candidate file one of the running law modules?"""
    p = os.path.abspath(candidate_file)
    return _inside(p, PKG_DIR) and os.path.basename(p) in LAW_MODULES


def SELF(root, candidate_file):
    return bool(self_target(root) or self_oracle(root, candidate_file)
                or self_law(candidate_file))


def name(byte):
    return "+".join(b for i, b in enumerate(BITS) if byte >> i & 1) or "(none)"


# --------------------------------------------------------------- cases ----
tmp = tempfile.mkdtemp(prefix="selfdesign-",
                       dir=os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(tmp, "pkg"), exist_ok=True)
plain_mod = os.path.join(tmp, "pkg", "mod.py")
plain_test = os.path.join(tmp, "test_mod.py")
for p in (plain_mod, plain_test):
    open(p, "w").write("# fixture\n")

FF_ROOT = "/Users/kanchetidevieswar/neo/fluidfix"

cases = [
    ("ordinary repo, source file",      tmp,     plain_mod),
    ("ordinary repo, its OWN test file", tmp,    plain_test),
    ("fluidfix pointed at itself, src", FF_ROOT, os.path.join(PKG_DIR, "loop.py")),
    ("fluidfix pointed at itself, LAW", FF_ROOT, os.path.join(PKG_DIR, "engine.py")),
    ("Box2D-style repo (no fluidfix inside)", "/private/tmp/nonexistent-repo",
     "/private/tmp/nonexistent-repo/src/contact_solver.c"),
]

print("package dir under test:", PKG_DIR)
print()
print(f"{'case':<40} {'S1':>3} {'S2':>3} {'S3':>3} {'SELF':>5}")
for label, root, cand in cases:
    print(f"{label:<40} {int(self_target(root)):>3} "
          f"{int(self_oracle(root, cand)):>3} {int(self_law(cand)):>3} "
          f"{int(SELF(root, cand)):>5}")

# ------------------- what the ruling would be, on the bytes the body builds --
# The eleven bytes guard.py/loop.py/cli.py can actually construct today
# (measured in constructible_bytes.out).
CONSTRUCTIBLE = [0, 1, 2, 3, 4, 16, 32, 33, 35, 64, 96]
print()
print("If SELF were measured and OR-ed into every byte the body can build today:")
print(f"{'byte':>5}  {'bits':<24} {'ruling':<24} {'ruling|SELF':<24} changed")
changed = 0
for b in CONSTRUCTIBLE:
    r0 = decide(situation(**{k: bool(b >> i & 1) for i, k in enumerate(BITS)}))
    r1 = decide(situation(**{k: bool((b | 128) >> i & 1)
                             for i, k in enumerate(BITS)}))
    changed += r0 != r1
    print(f"{b:>5}  {name(b):<24} {r0:<24} {r1:<24} {'YES' if r0 != r1 else 'no'}")
print(f"rulings changed: {changed} of {len(CONSTRUCTIBLE)}")

# --------------------- the two bytes on which SELF is the deciding bit -----
print()
print("The only two bytes where SELF changes the ruling, and what the body")
print("would additionally have to observe to construct each:")
for b, need in ((7, "BUILT and AMB and UNREAD in ONE situation() call "
                    "(no call site sets all three today)"),
                (8, "NOTWIN — measured nowhere in src/")):
    r0 = decide(situation(**{k: bool(b >> i & 1) for i, k in enumerate(BITS)}))
    r1 = decide(situation(**{k: bool((b | 128) >> i & 1)
                             for i, k in enumerate(BITS)}))
    print(f"  byte {b:>3} {name(b):<20} {r0} -> {r1}   needs: {need}")

import shutil
shutil.rmtree(tmp, ignore_errors=True)
