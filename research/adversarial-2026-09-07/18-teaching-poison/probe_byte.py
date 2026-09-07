# Prove the mechanism of the repoF S1: how many greens did the search find,
# at how many sites, and what byte did the law actually see?
# No fluidfix source is modified; guard_once is called as a library.
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, guard_once
from fluidfix.acts import load_dictionary
from fluidfix.engine import BITS, decide, situation

HERE = Path(__file__).parent
PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"


def byte_repr(b):
    on = [n for i, n in enumerate(BITS) if b >> i & 1]
    return f"0b{b:08b} ({b}) = {'+'.join(on) or 'NONE'}"


def run(label, repo, dictionary):
    saved = dict(KINDS), dict(ACTS)
    tmp = Path(tempfile.mkdtemp(prefix="poison-"))
    dst = tmp / repo
    shutil.copytree(HERE / "fixtures_pristine" / repo, dst)
    try:
        if dictionary:
            load_dictionary(str(HERE / "fixtures" / dictionary))
        rep = guard_once(Oracle(str(dst), python=PY), MechanicalObserver())
        r = rep.result
        print(f"\n### {label}")
        print(f"  status        : {rep.status}")
        print(f"  reported line : {r.lineno if r else None}")
        print(f"  new_line      : {r.new_line!r}" if r else "")
        print(f"  acts tried    : {r.acts_tried if r else None}")
        print(f"  greens found  : {len(r.greens) if r else 0} -> {r.greens if r else []}")
        if r and r.greens:
            # the loop's own AMB proxy: set_amb OR len(sites) > 1. Both greens
            # here are at ONE site, in DIFFERENT candidate sets, so set_amb is
            # False and sites == 1 -> AMB is measured FALSE.
            b = situation(BUILT=True, AMB=False, CAPPED=False)
            b_true = situation(BUILT=True, AMB=True, CAPPED=False)
            print(f"  byte AS MEASURED : {byte_repr(b)} -> decide = {decide(b)}")
            print(f"  byte IF AMB SET  : {byte_repr(b_true)} -> decide = {decide(b_true)}")
        print(f"  file after    :\n{(dst / [p.name for p in dst.glob('*.py') if not p.name.startswith('test_')][0]).read_text()}")
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])
        shutil.rmtree(tmp, ignore_errors=True)


run("repoF, NO dictionary (control)", "repoF_preempt", None)
run("repoF, poison_wrong.py loaded", "repoF_preempt", "poison_wrong.py")
run("repoC, poison_class.py loaded", "repoC_unrelated", "poison_class.py")
