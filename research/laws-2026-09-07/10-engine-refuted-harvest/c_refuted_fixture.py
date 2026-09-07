"""Does the C path actuate REFUTED -> HARVEST_COUNTEREXAMPLE the way the
Python path does?

Builds a minimal C project inside this directory whose defect is REAL but
whose true fix is outside the taught vocabulary, so candidates ARE generated
and the suite rejects EVERY one.  That is the exact shape of the recorded
Box2D contact_solver.c refusal.  Then prints:

  * what cguard_once() returned (status, attempts, hint)
  * report.summary()            -- the wording the user sees
  * .fluidfix/last_refusal.json -- what was harvested

usage: c_refuted_fixture.py
"""
import json, os, shutil, subprocess, sys, tempfile, time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, cguard_once
from fluidfix.guard import write_refusal
from fluidfix.observers import MechanicalObserver
from fluidfix.engine import decide, situation

here = os.path.dirname(os.path.abspath(__file__))
root = tempfile.mkdtemp(prefix="crefuted_", dir=here)
os.makedirs(os.path.join(root, "build"), exist_ok=True)

# The defect: `x * 3` where the truth is `x * x`.  A literal/off-by-one
# vocabulary generates many candidates at this line; none of them is right.
open(os.path.join(root, "scale.c"), "w").write(
    "int scale(int x)\n{\n\treturn x * 3;\n}\n")
open(os.path.join(root, "scale.h"), "w").write("int scale(int x);\n")
open(os.path.join(root, "test_scale.c"), "w").write(
    '#include <stdio.h>\n#include "scale.h"\n\n'
    'int main(void)\n{\n'
    '\tif (scale(5) != 25) {\n'
    '\t\tprintf("condition false: scale(5) == 25\\n");\n'
    '\t\tprintf("test failed: ScaleTest\\n");\n'
    '\t\treturn 1;\n\t}\n'
    '\tprintf("All tests passed!\\n");\n\treturn 0;\n}\n')

oracle = COracle(root,
                 build_cmd="cc -O0 -I. -o build/test scale.c test_scale.c",
                 test_cmd="./build/test", build_dir="build", timeout=120)
print("build:", oracle.build_cmd)
print("test :", oracle.test_cmd)

t0 = time.time()
report = cguard_once(oracle, MechanicalObserver(), budget=180)
dt = time.time() - t0
print(f"\nstatus={report.status}  seconds={dt:.1f}")
print("candidate files:", report.candidates)
print("attempts (harvested rejections):", len(report.attempts))
print("hint:", repr(report.hint))
print("\n--- report.summary() (what the user is told) ---")
print(report.summary())

p = write_refusal(root, report)
j = json.load(open(p))
print("\n--- .fluidfix/last_refusal.json ---")
print("hint:", repr(j["hint"]))
print("rejected_candidates:", len(j["rejected_candidates"]))
for e in j["rejected_candidates"][:6]:
    print("  ", e)

print("\n--- what the engine law rules on this situation ---")
print("decide(situation(REFUTED=True)) =",
      decide(situation(REFUTED=True)))
print("Python-path wording for the same ruling is set in guard.py:611-621;")
print("grep for it in coracle.cguard_once:",
      subprocess.run(["grep", "-c", "HARVEST_COUNTEREXAMPLE",
                      "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/coracle.py"],
                     capture_output=True, text=True).stdout.strip())
print("\nfixture root kept at:", root)
