"""Reproduce the BOM denial in isolation and print WHY each candidate died.

    ./rt 300 ../../../.venv/bin/python repro_bom.py

Two identical repos, one with a UTF-8 BOM as its first three bytes. The
same defect (`>=` that should be `>`), the same suite, the same act.
"""
import os
import shutil
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from fluidfix import MechanicalObserver, Oracle, guard_once   # noqa: E402

PY = os.path.join(ROOT, ".venv", "bin", "python")
GOOD = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
        "        if x > t:\n            n += 1\n    return n\n")
BAD = GOOD.replace("x > t", "x >= t")
TEST = ("from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")


def run(tag, bom):
    d = os.path.join(HERE, "work", tag)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    pre = "\ufeff" if bom else ""
    open(os.path.join(d, "mod.py"), "wb").write((pre + BAD).encode())
    open(os.path.join(d, "test_mod.py"), "w").write(TEST)
    # the DEFECTIVE file imports and runs fine — the BOM is not a syntax error
    rc = os.system(f"{PY} -c \"import sys; sys.path.insert(0,'{d}'); "
                   f"import mod; print('   import ok:', mod.count_above([1,5,5,9],5))\"")
    report = guard_once(Oracle(d, python=PY, timeout=45), MechanicalObserver())
    print(f"[{tag}] status={report.status} suite_runs="
          f"{getattr(report.result, 'suite_runs', None)}")
    print(f"[{tag}] summary: {report.summary()[:300]}")
    for a in report.attempts[:6]:
        print(f"    tried {a['tried']!r:48} why={a['why'][:90]!r}")
    on_disk = open(os.path.join(d, "mod.py"), "rb").read()
    print(f"[{tag}] file == pristine-correct? "
          f"{on_disk == (pre + GOOD).encode()}")
    print()


run("repro-nobom", False)
run("repro-bom", True)
