#!/usr/bin/env python
"""REPORT-ONLY. Compute the PAIR law's observation byte from a COMPLETED
single-edit search, using only data the body already has (or already
receives and discards).

Nothing here edits src/. It replays loop.py's single-edit enumeration with
the SAME public pieces (acts.candidates, acts.act_for, acts.candidate_cap,
Oracle.run) and records, per candidate, the two things loop.py currently
throws away:

    - the FAILING COUNT      (oracle.check() already has the run output; it
                              keeps only the first FAILED line)
    - the FAILING NODE SET   (same output, same run, same cost)

Everything else the byte needs is already a field of RepairResult or a
module-level fact of acts.py.

Usage:
    python observe_pair.py <fixture-dir> <defect-file> [budget-seconds]

Run under `nice -n 15`. `timeout(1)` is absent on this host; every suite run
goes through Oracle.run's own subprocess timeout instead.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.acts import ACTS as APPLIERS, Observation, SpanEdit  # noqa: E402
from fluidfix.acts import act_for, candidate_cap, candidates       # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of   # noqa: E402
from fluidfix.localize import build_packet                         # noqa: E402
from fluidfix.observers import MechanicalObserver                  # noqa: E402
from fluidfix.oracle import Oracle                                 # noqa: E402
from fluidfix.pair import ACTS as PAIR_ACTS                        # noqa: E402
from fluidfix.pair import BITS, observe_bits, pair_law             # noqa: E402

# oracle.py already compiles this exact regex (_SUMMARY_FAIL) and uses it
# only to catch a suite that exits 0 while reporting failures. The same
# match on the same output is the failing COUNT.
_SUMMARY_FAIL = re.compile(r"\b(\d+) (failed|error(?:s|ed)?)\b")
_FAILED_LINE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)")


def read_failures(out: str) -> tuple[int, frozenset]:
    """(failing count, failing node ids) from ONE pytest run's output.

    Zero extra suite runs: `Oracle.check()` already holds this string.
    """
    nodes = set()
    for line in out.splitlines():
        m = _FAILED_LINE.match(line.strip())
        if m:
            nodes.add(m.group(1))
    n = 0
    for line in reversed(out.strip().splitlines()[-25:]):
        m = _SUMMARY_FAIL.search(line)
        if m:
            n = int(m.group(1))
            break
    return (max(n, len(nodes)), frozenset(nodes))


class Search:
    """A completed single-edit search, with everything the PAIR law needs."""

    def __init__(self):
        self.baseline_n = 0
        self.baseline_nodes = frozenset()
        self.tried = []          # {site, text, green, n, nodes}
        self.greens = []
        self.acts_tried = []
        self.kinds_seen = []
        self.enumerated = 0      # candidates the space contains
        self.completed = False   # ran to the end of the enumeration
        self.deadline_hit = False
        self.run_seconds = []
        self.budget = 0.0
        self.elapsed = 0.0


def _widened(raw: list) -> list:
    """What the WIDEN act would hand the search: every line of the defect
    file that any taught class's signal regex matches, not only the lines
    the localiser put in the packet."""
    from fluidfix.acts import KINDS
    obs = []
    for l, line in enumerate(raw, 1):
        line = line.rstrip("\r")
        kinds = [k for k, (_, _, sig) in sorted(KINDS.items())
                 if sig.search(line)]
        if kinds:
            obs.append(Observation(lineno=l, kinds=kinds))
    return obs


def run_search(root: str, defect_file: str, budget: float = 300.0,
               widen: bool = False) -> Search:
    s = Search()
    oracle = Oracle(root, python=sys.executable, timeout=120)
    t0 = time.time()
    s.budget = budget
    deadline = t0 + budget

    rc, out = oracle.run(["--tb=no"])
    s.baseline_n, s.baseline_nodes = read_failures(out)
    if s.baseline_n == 0:
        s.completed = True
        return s

    packet = build_packet(oracle, defect_file)
    if packet is None:
        s.completed = True
        return s
    observations = MechanicalObserver().observe([packet])[0]

    path = os.path.join(root, defect_file)
    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()
    raw = src.split("\n")
    if widen:
        observations = _widened(raw)
    seen = set()
    try:
        for obs in observations:
            i = obs.lineno - 1
            if not (0 <= i < len(raw)):
                continue
            body = raw[i].rstrip("\r")
            ending = raw[i][len(body):]
            mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
            while not HALT(mask):
                kind = kind_of(EMIT(mask))
                mask = ADVANCE(mask)
                s.kinds_seen.append(kind)
                act = act_for(kind)
                obs.file, obs.root = defect_file, root
                obs.all_lines = [l.rstrip("\r") for l in raw]
                counted = False
                for cand in candidates(body, act, obs):
                    if isinstance(cand, SpanEdit):
                        continue          # span edits: not exercised here
                    if cand == body:
                        continue
                    key = (i, cand)
                    if key in seen:
                        continue
                    seen.add(key)
                    s.enumerated += 1
                    if not counted:
                        s.acts_tried.append(act)
                        counted = True
                    if time.time() > deadline:
                        s.deadline_hit = True
                        return s
                    new = raw[:]
                    new[i] = cand + ending
                    content = "\n".join(new)
                    try:
                        compile(content, path, "exec")
                    except SyntaxError:
                        continue
                    with open(path, "w", encoding="utf-8", newline="") as fh:
                        fh.write(content)
                    r0 = time.time()
                    oracle.clear_pyc()
                    rc, out = oracle.run(["--tb=no"])
                    s.run_seconds.append(time.time() - r0)
                    n, nodes = read_failures(out)
                    green = (rc == 0 and n == 0)
                    rec = {"site": obs.lineno, "text": cand, "green": green,
                           "n": n, "nodes": sorted(nodes)}
                    s.tried.append(rec)
                    if green:
                        s.greens.append(rec)
                    with open(path, "w", encoding="utf-8", newline="") as fh:
                        fh.write(src)
        s.completed = True
    finally:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(src)
        oracle.clear_pyc()
        s.elapsed = time.time() - t0
    return s


# ---------------------------------------------------------- THE BYTE ------
def pair_byte(s: Search) -> tuple[int, dict]:
    """The eight observations, each with its provenance."""
    prov = {}

    # bit 0 EXHAUSTED -- loop.py already knows this exactly: it passes
    # `capped=` to _rule() at every exit. It is never stored on RepairResult.
    # NOTE: an EMPTY enumerated space is exhausted too. Requiring
    # enumerated>0 was this script's own first draft and it sent the
    # out-of-vocabulary fixture to SINGLE ("keep going") when there was
    # nothing left to go on. See REPORT.md finding 6.
    exhausted = bool(s.completed and not s.greens)
    prov["EXHAUSTED"] = (
        f"completed={s.completed} enumerated={s.enumerated} "
        f"greens={len(s.greens)} -> {exhausted} "
        "[available today: loop.py's `capped` argument + res.acts_tried]")

    # bit 1 PARTIAL -- the ONLY new measurement. Same run, same output.
    reducers = [t for t in s.tried if not t["green"] and t["n"] < s.baseline_n]
    partial = bool(reducers)
    prov["PARTIAL"] = (
        f"baseline={s.baseline_n} failing; {len(reducers)} of {len(s.tried)} "
        f"candidates strictly reduced it -> {partial} "
        "[NEW: failing count, parsed from the output Oracle.check() already "
        "receives; zero extra suite runs]")

    # bits 2/3 DISJOINT / COUPLED -- from the same per-candidate failing SET.
    # site(t) = the sites at which some single edit made failing test t pass.
    fixers = {}
    for t in s.tried:
        if t["green"]:
            for node in s.baseline_nodes:
                fixers.setdefault(node, set()).add(t["site"])
            continue
        for node in s.baseline_nodes - frozenset(t["nodes"]):
            fixers.setdefault(node, set()).add(t["site"])
    covered = {n: v for n, v in fixers.items() if v}
    sites_union = set().union(*covered.values()) if covered else set()
    disjoint = bool(
        len(s.baseline_nodes) >= 2
        and len(covered) == len(s.baseline_nodes)
        and all(a.isdisjoint(b)
                for i, a in enumerate(covered.values())
                for b in list(covered.values())[i + 1:]))
    coupled = bool(covered and len(sites_union) == 1
                   and len(covered) == len(s.baseline_nodes))
    prov["DISJOINT"] = (
        f"failing tests {sorted(s.baseline_nodes)}; repairing sites per test "
        f"{ {k: sorted(v) for k, v in covered.items()} } -> {disjoint} "
        "[derivable today from per-candidate failing SETS, same runs]")
    prov["COUPLED"] = f"union of repairing sites {sorted(sites_union)} -> {coupled}"

    # bit 4 CHEAP -- every ingredient is already in RepairResult/guard.py.
    n = s.enumerated
    pairs = n * (n - 1) // 2
    mean = (sum(s.run_seconds) / len(s.run_seconds)) if s.run_seconds else 0.0
    remaining = max(0.0, s.budget - s.elapsed)
    cost = pairs * mean
    cheap = bool(pairs and cost <= remaining)
    prov["CHEAP"] = (
        f"n={n} singles -> {pairs} pairs x {mean:.3f}s = {cost:.1f}s vs "
        f"{remaining:.1f}s remaining -> {cheap} "
        "[available today: res.suite_runs, res.seconds, guard.py's deadline; "
        "the <= threshold is a CODE decision, owned by nobody]")

    # bit 5 TAUGHT -- a static fact of acts.py, no suite run at all.
    kinds = sorted(set(s.kinds_seen))
    untaught = [k for k in kinds if act_for(k) not in APPLIERS]
    taught = bool(kinds) and not untaught
    prov["TAUGHT"] = (
        f"kinds {kinds}; without an applier {untaught} -> {taught} "
        "[available today: acts.act_for + acts.ACTS, zero cost]")

    # bit 6 CANCELING -- NOT observable from a completed SINGLE-edit search.
    canceling = False
    prov["CANCELING"] = (
        "unmeasurable before a pair is tried: it is defined on a pair that is "
        "green JOINTLY. Reported False. Post-pair predicate, computable from "
        "this same log: green(a+b) and not green(a) and not green(b) and "
        "n(a) >= baseline and n(b) >= baseline.")

    # bit 7 CAPPED -- loop.py computes it exactly today and discards it
    # into prose whenever there are no greens.
    capped = bool(s.deadline_hit)
    prov["CAPPED"] = (
        f"deadline_hit={s.deadline_hit} -> {capped} "
        "[available today: loop.py's `capped` arg / guard.py total_deadline]")

    byte = observe_bits(exhausted=exhausted, partial=partial,
                        disjoint=disjoint, coupled=coupled, cheap=cheap,
                        taught=taught, canceling=canceling, capped=capped)
    return byte, prov


def main():
    argv = [a for a in sys.argv[1:] if a != "--widen"]
    widen = "--widen" in sys.argv
    root = os.path.abspath(argv[0])
    defect = argv[1]
    budget = float(argv[2]) if len(argv) > 2 else 300.0
    s = run_search(root, defect, budget, widen=widen)
    byte, prov = pair_byte(s)
    ruling = pair_law(byte)
    print(f"fixture           {root}")
    print(f"defect file       {defect}")
    print(f"baseline failing  {s.baseline_n} {sorted(s.baseline_nodes)}")
    print(f"candidates tried  {len(s.tried)} (enumerated {s.enumerated}), "
          f"greens {len(s.greens)}, {s.elapsed:.1f}s")
    print("observations:")
    for b in BITS:
        on = bool(byte >> BITS.index(b) & 1)
        print(f"  {b:<10} {int(on)}  {prov[b]}")
    print(f"BYTE              {byte} (0b{byte:08b})")
    print(f"pair_law RULING   {ruling} = {PAIR_ACTS[ruling]}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           f"search-{os.path.basename(root)}"
                           f"{'-widen' if widen else ''}.json"), "w") as f:
        json.dump({"baseline_n": s.baseline_n,
                   "baseline_nodes": sorted(s.baseline_nodes),
                   "tried": s.tried, "enumerated": s.enumerated,
                   "byte": byte, "ruling": PAIR_ACTS[ruling],
                   "cap": candidate_cap()}, f, indent=1)


if __name__ == "__main__":
    main()
