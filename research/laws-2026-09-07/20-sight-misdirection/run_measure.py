#!/usr/bin/env python
"""Measure, on one fixture, (1) what the body feeds the SIGHT law per file
and the order it returns, and (2) what guard_once does next.

    .venv/bin/python run_measure.py named            # ranking only
    .venv/bin/python run_measure.py named --guard    # + a full guard pass
    .venv/bin/python run_measure.py named --guard --budget 8

Report-only: never edits src/. The SIGHT byte per file is captured by
wrapping fluidfix.sight.observe_bits and reading the caller's `rel` local
(guard.find_candidate_files.file_priority2) — a debugging hook, not a
behaviour change: the wrapper returns exactly what the real function does.
Each run works on a FRESH copy of the fixture under work/, so a repair or a
leftover mutation never leaks into the next run.
"""
import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fluidfix.sight as sight_mod                       # noqa: E402
from fluidfix import MechanicalObserver, Oracle            # noqa: E402
from fluidfix.guard import find_candidate_files, guard_once  # noqa: E402
from fluidfix.sight import BITS, sight                      # noqa: E402

RECORDED: dict[str, int] = {}
_real_observe_bits = sight_mod.observe_bits


def _recording_observe_bits(**kw):
    byte = _real_observe_bits(**kw)
    rel = sys._getframe(1).f_locals.get("rel")
    if rel is not None:
        RECORDED[rel] = byte
    return byte


def bits_of(byte):
    return "|".join(b for i, b in enumerate(BITS) if byte >> i & 1) or "-"


def fresh_copy(name, tag):
    src = os.path.join(HERE, "fixtures", name)
    dst = os.path.join(HERE, "work", f"{name}-{tag}")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", choices=["named", "framed"])
    ap.add_argument("--guard", action="store_true")
    ap.add_argument("--budget", type=int, default=None)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    tag = args.tag or ("guard" if args.guard else "rank")
    if args.budget:
        tag += f"-b{args.budget}"
    root = fresh_copy(args.fixture, tag)
    oracle = Oracle(root, python=sys.executable)

    print(f"# fixture {args.fixture} -> {root}")
    fails, out = oracle.failing_output()
    print(f"# failing: {fails}")
    print("# failing output (tail, ANSI stripped by the body; shown raw here):")
    for line in out.splitlines()[-25:]:
        print("   |", line)

    # ---- (1) the ranking, with the byte the body built per file ----
    sight_mod.observe_bits = _recording_observe_bits
    try:
        ev: dict = {}
        order = find_candidate_files(oracle, out, evidence=ev)
    finally:
        sight_mod.observe_bits = _real_observe_bits
    print("\n# find_candidate_files order (what guard_once's first pass walks):")
    for i, rel in enumerate(order, 1):
        b = RECORDED.get(rel)
        if b is None:
            print(f"   {i}. {rel:<18} SIGHT NOT CONSULTED (traceback-frame branch)")
        else:
            print(f"   {i}. {rel:<18} byte=0x{b:02x} {bits_of(b):<32} priority={sight(b)}")
    print(f"# evidence: {json.dumps(ev)}")
    print(f"# SIGHT consulted for {len(RECORDED)} file(s)")

    if not args.guard:
        return 0

    # ---- (2) what the body does next ----
    # per-file ledger: wrap the two calls guard_once makes per file (a
    # repaired GuardReport drops `attempts`, so this is the only way to see
    # what the wrong files cost). Wrappers return exactly what the real
    # functions return.
    import fluidfix.guard as guard_mod
    _real_repair, _real_packet = guard_mod.repair, guard_mod.build_packet
    ledger: list[dict] = []
    packet_secs: dict[str, float] = {}

    def _rec_packet(oracle_, rel, *a, **kw):
        t = time.time()
        p = _real_packet(oracle_, rel, *a, **kw)
        packet_secs[rel] = packet_secs.get(rel, 0.0) + (time.time() - t)
        return p

    def _rec_repair(oracle_, rel, observations, **kw):
        t = time.time()
        r = _real_repair(oracle_, rel, observations, **kw)
        ledger.append({"file": rel, "suite_runs": r.suite_runs,
                       "repair_s": round(time.time() - t, 1),
                       "packet_s": round(packet_secs.get(rel, 0.0), 1),
                       "acts": r.acts_tried,
                       "rejected": len(r.tried_log) + r.tried_more,
                       "repaired": r.repaired, "reason": r.reason[:70]})
        return r

    guard_mod.repair, guard_mod.build_packet = _rec_repair, _rec_packet
    t0 = time.time()
    try:
        report = guard_once(oracle, MechanicalObserver(), budget=args.budget)
    finally:
        guard_mod.repair, guard_mod.build_packet = _real_repair, _real_packet
    dt = time.time() - t0
    print("\n# per-file ledger (order walked):")
    for e in ledger:
        print("   ", json.dumps(e))
    print(f"# suite runs on WRONG files: "
          f"{sum(e['suite_runs'] for e in ledger if not e['repaired'])}, "
          f"on the repaired file: "
          f"{sum(e['suite_runs'] for e in ledger if e['repaired'])}")
    print(f"\n# guard_once(budget={args.budget}) -> status={report.status} "
          f"file={report.file} seconds={dt:.1f}")
    print(f"# candidates: {report.candidates}")
    per_file: dict[str, int] = {}
    for a in report.attempts:
        at = str(a.get("at", "?"))
        f = at.split(":")[0]
        per_file[f] = per_file.get(f, 0) + 1
    print(f"# rejected candidates by file (tried_log, capped at 64/file): "
          f"{json.dumps(per_file)}")
    if report.attempts:
        print(f"# first rejected candidate record: {json.dumps(report.attempts[0])}")
    if report.result is not None:
        r = report.result
        print(f"# result: lineno={r.lineno} old={r.old_line.strip()!r} "
              f"new={r.new_line.strip()!r} suite_runs={r.suite_runs} "
              f"reason={r.reason!r}")
    print(f"# hint: {report.hint!r}")
    print("# summary():")
    for line in report.summary().splitlines():
        print("   |", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
