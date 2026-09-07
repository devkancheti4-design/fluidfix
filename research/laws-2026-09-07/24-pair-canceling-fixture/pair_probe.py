#!/usr/bin/env python
"""Report-only probe: measure the PAIR law's observation byte on a fixture.

Nothing here edits fluidfix. It reuses fluidfix's OWN localizer, observer,
act vocabulary and oracle to run a complete single-edit search, then (only
because pair.py is never called by the body) enumerates the pairs itself so
that CANCELING can be measured against its docstring definition:

    bit 6  CANCELING  a pair is green JOINTLY while each member alone leaves
                      the suite red AND reduces nothing

Usage:  python pair_probe.py FIXTURE_DIR [--no-pairs]
Writes: work/<fixture>/ (a scratch copy) and prints every measurement.
"""
from __future__ import annotations

import itertools
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"

from fluidfix import MechanicalObserver, Oracle, build_packet   # noqa: E402
from fluidfix.acts import SpanEdit, act_for, candidates          # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402
from fluidfix.pair import ACTS, BITS, observe_bits, pair_law      # noqa: E402

FAILED = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)")


def failing_set(oracle: Oracle) -> set:
    """The set of failing test node ids. (Oracle.check gives a verdict, not a
    set; the PARTIAL/DISJOINT bits need the set.)"""
    oracle.clear_pyc()
    rc, out = oracle.run(["--tb=no", "-rf"])
    if rc == 0:
        return set()
    ids = {m.group(1) for m in (FAILED.match(l) for l in out.splitlines()) if m}
    return ids or {"<unparsed-failure>"}


def enumerate_single_edits(oracle, defect_file, observations, raw):
    """Exactly loop.py's candidate enumeration, without its accept/stop logic."""
    out, tried = [], set()
    for obs in observations:
        i = obs.lineno - 1
        if not (0 <= i < len(raw)):
            continue
        body = raw[i].rstrip("\r")
        mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
        while not HALT(mask):
            kind = kind_of(EMIT(mask))
            mask = ADVANCE(mask)
            act = act_for(kind)
            obs.file, obs.root = defect_file, oracle.root
            obs.all_lines = [l.rstrip("\r") for l in raw]
            for cand in candidates(body, act, obs):
                if isinstance(cand, SpanEdit):
                    continue                    # span edits: not probed here
                if cand == body:
                    continue                    # NOPROGRESS
                key = (i, cand)
                if key in tried:
                    continue
                tried.add(key)
                out.append({"line": obs.lineno, "kind": kind, "act": act,
                            "old": body, "new": cand})
    return out


def apply_edits(raw, edits):
    new = raw[:]
    for e in edits:
        i = e["line"] - 1
        ending = raw[i][len(raw[i].rstrip("\r")):]
        new[i] = e["new"] + ending
    return "\n".join(new)


def property_ok(root):
    """A property the SUITE DOES NOT CONTAIN: vector addition is still
    componentwise addition. Used only to classify a jointly-green pair as
    honest or corrupting; never consulted by any law."""
    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from vec import Vec3, project_on_plane\n"
        "assert (Vec3(1.0,2.0,3.0) + Vec3(4.0,5.0,6.0)).c == (5.0,7.0,9.0), 'add'\n"
        "assert project_on_plane(Vec3(1.0,4.0,2.0), Vec3(0.0,1.0,0.0)).c "
        "== (1.0,0.0,2.0), 'project'\n" % root)
    p = subprocess.run([VENV, "-c", script], capture_output=True, text=True,
                       cwd=root, timeout=60)
    return p.returncode == 0, (p.stderr.strip().splitlines() or [""])[-1]


def main():
    fixture = os.path.abspath(sys.argv[1])
    do_pairs = "--no-pairs" not in sys.argv
    name = os.path.basename(fixture.rstrip("/"))
    work = os.path.join(HERE, "work", name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.dirname(work), exist_ok=True)
    shutil.copytree(fixture, work)

    oracle = Oracle(work, python=VENV)
    path = os.path.join(work, "vec.py")
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()
    raw = src.split("\n")

    base_fail = failing_set(oracle)
    print(f"== fixture {name}")
    print(f"baseline failing tests ({len(base_fail)}): {sorted(base_fail)}")
    ok, why = property_ok(work)
    print(f"baseline hidden property (not in the suite): "
          f"{'holds' if ok else 'VIOLATED: ' + why}")

    packet = build_packet(oracle, "vec.py", coverage_target="vec")
    if packet is None:
        print("build_packet returned None (suite green) — nothing to observe")
        return 1
    observations = MechanicalObserver().observe([packet])[0]
    print(f"observations: {len(observations)} "
          f"{[(o.lineno, o.kinds) for o in observations]}")

    singles = enumerate_single_edits(oracle, "vec.py", observations, raw)
    print(f"single-edit candidates: {len(singles)}")

    try:
        for k, e in enumerate(singles):
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(apply_edits(raw, [e]))
            e["fail"] = failing_set(oracle)
            e["green"] = not e["fail"]
            # STRICTLY reduced: a PROPER SUBSET of the baseline failures.
            # Counting alone is wrong — a candidate that breaks collection
            # reports one ERROR line and looks like progress (measured on
            # fixture D, first run: `class Vec3` -> `class Vec2` scored
            # "REDUCES" while it had in fact broken every test).
            e["reduces"] = (0 < len(e["fail"]) < len(base_fail)
                            and e["fail"] < base_fail)
            print(f"  [{k:2d}] line {e['line']:3d} kind {e['kind']:2d} "
                  f"{'GREEN' if e['green'] else 'red  '} "
                  f"fail={len(e['fail'])}{' REDUCES' if e['reduces'] else ''} "
                  f"| {e['new'].strip()[:70]}")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(src)

        pairs_green = []
        pair_runs = 0
        if do_pairs:
            for a, b in itertools.combinations(range(len(singles)), 2):
                ea, eb = singles[a], singles[b]
                if ea["line"] == eb["line"]:
                    continue                     # not simultaneously applicable
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(apply_edits(raw, [ea, eb]))
                pair_runs += 1
                if not failing_set(oracle):
                    okp, whyp = property_ok(work)
                    pairs_green.append((a, b, okp, whyp))
                    print(f"  PAIR GREEN [{a},{b}] lines {ea['line']}+{eb['line']} "
                          f"| {ea['new'].strip()[:40]} || {eb['new'].strip()[:40]} "
                          f"| hidden property {'holds' if okp else 'VIOLATED'}")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(src)
            print(f"pair suite runs: {pair_runs}; jointly green: {len(pairs_green)}")
    finally:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(src)
        oracle.clear_pyc()

    # ------------------------------------------------------- the byte ----
    exhausted = all(not e["green"] for e in singles)
    partial = any(e["reduces"] for e in singles)
    # which lines can move which failing test
    moves = {t: set() for t in base_fail}
    for e in singles:
        for t in base_fail - e["fail"]:
            moves.setdefault(t, set()).add(e["line"])
    disjoint = (len(base_fail) > 1 and all(
        not (moves[x] & moves[y])
        for x, y in itertools.combinations(sorted(base_fail), 2)))
    coupled = (len(base_fail) >= 1 and bool(set.intersection(*moves.values()))
               if moves and all(moves.values()) else False)
    canceling = any(
        not singles[a]["green"] and not singles[b]["green"]
        and not singles[a]["reduces"] and not singles[b]["reduces"]
        for a, b, _o, _w in pairs_green) if do_pairs else None
    print("\n-- measured observation byte --")
    for nm, val in (("EXHAUSTED", exhausted), ("PARTIAL", partial),
                    ("DISJOINT", disjoint), ("COUPLED", coupled),
                    ("CANCELING", canceling)):
        print(f"  {nm:<10} {val}")
    print("  CHEAP      unmeasured (no threshold exists in the body); "
          f"singles={len(singles)}, distinct-line pairs={pair_runs}")
    print("  TAUGHT     unmeasured (no body code sets it); kinds used = "
          f"{sorted({e['kind'] for e in singles})} (all shipped classes)")
    print("  CAPPED     False (no budget given to this probe)")

    for cheap in (False, True):
        for taught in (False, True):
            byte = observe_bits(exhausted=exhausted, partial=partial,
                                disjoint=disjoint, coupled=bool(coupled),
                                cheap=cheap, taught=taught,
                                canceling=bool(canceling), capped=False)
            no_can = byte & ~(1 << 6)
            print(f"  CHEAP={int(cheap)} TAUGHT={int(taught)}  byte={byte:3d} "
                  f"-> {ACTS[pair_law(byte)]:<9} | without CANCELING: "
                  f"byte={no_can:3d} -> {ACTS[pair_law(no_can)]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
