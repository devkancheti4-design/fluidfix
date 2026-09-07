#!/usr/bin/env python
"""What fluidfix ACTUALLY does on these fixtures today (single-edit body).

Runs the real localizer, observer and repair loop on a scratch copy.
Usage: python body_run.py FIXTURE_DIR
"""
import os
import shutil
import sys

from fluidfix import MechanicalObserver, Oracle, build_packet, repair

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

fixture = os.path.abspath(sys.argv[1])
name = os.path.basename(fixture.rstrip("/"))
work = os.path.join(HERE, "work", "body_" + name)
shutil.rmtree(work, ignore_errors=True)
shutil.copytree(fixture, work)

oracle = Oracle(work, python=VENV)
packet = build_packet(oracle, "vec.py", coverage_target="vec")
obs = MechanicalObserver().observe([packet])[0]
res = repair(oracle, "vec.py", obs)
print(f"== {name}")
print(f"repaired={res.repaired} refused={res.refused} ambiguous={res.ambiguous}")
print(f"suite_runs={res.suite_runs} acts_tried={res.acts_tried} "
      f"seconds={res.seconds:.1f}")
print(f"greens={res.greens}")
print(f"reason: {res.reason}")
same = open(os.path.join(work, "vec.py"), encoding="utf-8").read() == \
    open(os.path.join(fixture, "vec.py"), encoding="utf-8").read()
print(f"file restored byte-exactly: {same}")
