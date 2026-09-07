#!/bin/sh
# Reproduce every claim fluidfix makes about its own laws, on your machine.
#   ./docs/verify.sh            (needs only the venv; ~10 min for the suite)
# Every number printed below is produced by the command above it.
set -e
PY="${PY:-.venv/bin/python}"
FF="${FF:-.venv/bin/fluidfix}"
echo "=============================================================="
echo " fluidfix verification — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo " version: $($PY -c 'import fluidfix;print(fluidfix.__version__)')"
echo "=============================================================="

echo
echo "== 1. THE SIX LAWS RE-DERIVE FROM THEIR OWN SPECIFICATIONS =="
echo "   Not a test of fluidfix against itself: each kernel is re-derived"
echo "   exhaustively over its ENTIRE input space and compared to the"
echo "   authored specification."
$FF selfcheck

echo
echo "== 2. THE LAW RULES ON EVERY EXIT =="
echo "   Before 0.15.0 a refusal could not carry a ruling: the loop returned"
echo "   before asking whenever nothing went green. Every situation below is"
echo "   one that used to end in a hardcoded sentence."
$PY - <<'PY'
from fluidfix.engine import decide, situation
rows = [
    ("a green, nothing blocking",            dict(BUILT=True)),
    ("a green, search cut short",            dict(BUILT=True, CAPPED=True)),
    ("two programs, one input",              dict(BUILT=True, AMB=True)),
    ("candidates generated, ALL rejected",   dict(REFUTED=True)),
    ("cut short before exhausting",          dict(CAPPED=True)),
    ("the vocabulary named nothing",         dict(UNREAD=True)),
]
for label, bits in rows:
    b = situation(**bits)
    print(f"   {label:36s} byte {b:>4} -> {decide(b)}")
PY

echo
echo "== 3. AMB IS MEASURED ON PROGRAM IDENTITY =="
echo "   The law asks whether ONE INPUT CARRIES TWO OUTPUTS. Until 0.15.0 the"
echo "   body asked where the greens came from instead, and shipped 12 of 12"
echo "   with 6 wrong. Both cases below run with NO ground truth."
$PY - <<'PY'
import sys, shutil, tempfile, pathlib
from fluidfix.differ import programs_differ
def case(label, body, test, cands, expect):
    d = pathlib.Path(tempfile.mkdtemp())
    (d/"mod.py").write_text(body); (d/"test_mod.py").write_text(test)
    ans, rec = programs_differ(str(d), "mod.py", 2, cands, python=sys.executable)
    ok = "OK " if ans is expect else "!! "
    print(f"   {ok}{label:34s} -> {str(ans):5s} {rec.get('witness_call','')}")
    shutil.rmtree(d, ignore_errors=True)
    return ans is expect
a = case("two DIFFERENT programs", 
    "def alarm(readings, limit):\n    return readings[0] > limit\n",
    "from mod import alarm\ndef test_a():\n    assert alarm([1, 9], 5) is True\n",
    [(2, "    return readings[1] >= limit"), (2, "    return readings[0] > limit")], True)
b = case("ONE program spelled twice",
    "def over(units):\n    return units >= 10\n",
    "from mod import over\ndef test_b():\n    assert over(10) is True\n    assert over(9) is False\n",
    [(2, "    return units >= 10"), (2, "    return units > 9")], False)
print("   (a witness proves two programs; no witness proves one; and a probe")
print("    that cannot read the language says UNKNOWN, never 'no')")
raise SystemExit(0 if (a and b) else 1)
PY

echo
echo "== 4. A REAL REPAIR, AND A REAL REFUSAL, END TO END =="
$PY - <<'PY'
import sys, shutil, tempfile, pathlib, json
from fluidfix.oracle import Oracle
from fluidfix.guard import guard_once, write_refusal
from fluidfix.observers import MechanicalObserver

def repo(body, test):
    d = pathlib.Path(tempfile.mkdtemp())
    (d/"mod.py").write_text(body); (d/"test_mod.py").write_text(test)
    return d

# 4a: an unambiguous defect -> repaired, byte-exact
d = repo("def add(a, b):\n    return a - b\n",
         "from mod import add\ndef test_add():\n    assert add(2, 3) == 5\n")
r = guard_once(Oracle(str(d), python=sys.executable), MechanicalObserver(), budget=120)
print(f"   repair : {r.status}  ruling={getattr(r.result,'ruling','')}"
      f"  runs={getattr(r.result,'suite_runs','?')}")
print(f"            file now: {(d/'mod.py').read_text().splitlines()[1].strip()!r}")
shutil.rmtree(d, ignore_errors=True)

# 4b: the shape that shipped 6 wrong repairs -> refused, with the test written
d = repo('def alarm(readings, limit):\n    return readings[1] > limit\n',
         "from mod import alarm\n"
         "def test_1():\n    assert alarm([7, 3], 3) is True\n"
         "def test_2():\n    assert alarm([1, 0], 5) is False\n"
         "def test_3():\n    assert alarm([9, 8], 2) is True\n")
r = guard_once(Oracle(str(d), python=sys.executable), MechanicalObserver(), budget=120)
res = r.result
print(f"   refuse : {r.status}  ruling={getattr(res,'ruling','')}"
      f"  greens={len(getattr(res,'greens',[]) or [])}")
if res is not None and getattr(res, "pinning_test", ""):
    write_refusal(str(d), r)
    pin = (d/".fluidfix"/"pin_me_test.py").read_text()
    print("            .fluidfix/pin_me_test.py written:")
    for ln in pin.splitlines():
        if ln.strip().startswith("# assert"):
            print(f"              {ln.strip()}")
print(f"            file UNCHANGED: "
      f"{(d/'mod.py').read_text().splitlines()[1].strip()!r}")
shutil.rmtree(d, ignore_errors=True)
PY

echo
echo "== 5. THE WHOLE TEST SUITE =="
$PY -m pytest -q --tb=line -p no:randomly

echo
echo "=============================================================="
echo " Everything above was produced by the commands shown."
echo "=============================================================="
