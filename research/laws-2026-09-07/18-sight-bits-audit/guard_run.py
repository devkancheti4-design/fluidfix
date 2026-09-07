#!/usr/bin/env python
"""Run one guard pass on a fixture COPY and report the order files were
opened and how many candidates each consumed.

Usage:  run300.sh .venv/bin/python guard_run.py <fixture_root>

The fixture is copied to <fixture_root>_run first so the original stays
broken for re-runs. Nothing in src/ is edited; `fluidfix.sight.sight` is
wrapped only to log the bytes, exactly as sight_probe.py does.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fluidfix.sight as sight_mod                           # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402
from fluidfix.sight import BITS                              # noqa: E402

REAL = sight_mod.sight
LOG: list = []


def recorder(obs):
    loc = sys._getframe(1).f_locals
    LOG.append((loc.get("rel"), obs))
    return REAL(obs)


def names(obs):
    return "|".join(b for i, b in enumerate(BITS) if obs >> i & 1) or "-"


def main():
    src = os.path.abspath(sys.argv[1].rstrip("/"))
    root = src + "_run"
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(src, root)
    oracle = Oracle(root, python=sys.executable)
    sight_mod.sight = recorder
    t0 = time.time()
    try:
        rep = guard_once(oracle, MechanicalObserver(), budget=240)
    finally:
        sight_mod.sight = REAL
    print(f"status={rep.status} file={rep.file} seconds={time.time() - t0:.1f}")
    print("candidates (first-pass order):", rep.candidates)
    print("evidence:", rep.evidence)
    seen = {}
    for rel, obs in LOG:
        seen.setdefault(rel, obs)
    print("bytes handed to the law (first call per file):")
    for rel, obs in seen.items():
        print(f"   {rel:22} {obs:3d} prio {REAL(obs)}  {names(obs)}")
    print(f"attempts logged: {len(rep.attempts)}")
    for a in rep.attempts[:40]:
        print("   ", repr(a)[:160])
    if rep.result is not None:
        print("result:", rep.result.summary()[:300])
    print("summary:", rep.summary()[:400])


if __name__ == "__main__":
    main()
