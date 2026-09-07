#!/usr/bin/env python3
"""Why the body's search never reaches the second fault, and what a truly
COMPLETED single-edit search over both fault files measures.

Report-only; every experiment runs in a throwaway copy under ./work2/.

    nice -n 15 .venv/bin/python measure2.py            # enumeration only
    nice -n 15 .venv/bin/python measure2.py --pairs    # + cross-site pair sweep
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/kanchetidevieswar/neo/fluidfix"
PY = os.path.join(REPO, ".venv", "bin", "python")
sys.path.insert(0, os.path.join(REPO, "src"))

from fluidfix.acts import KINDS, Observation, SpanEdit, act_for, candidates  # noqa: E402
from fluidfix.localize import build_packet                     # noqa: E402
from fluidfix.oracle import Oracle                             # noqa: E402
from fluidfix.pair import ACTS, BITS, observe_bits, pair_law    # noqa: E402

FILES = ["billing.py", "inventory.py"]
FAULT_LINE = {"billing.py": 13, "inventory.py": 11}
WORK = os.path.join(HERE, "work2")
_FAILED = re.compile(r"^FAILED (\S+)", re.M)


def fresh(tag: str) -> str:
    root = os.path.join(WORK, tag)
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(WORK, exist_ok=True)
    shutil.copytree(os.path.join(HERE, "fixture"), root)
    return root


def run_suite(root: str) -> tuple[int, set[str]]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([PY, "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider", "--tb=no"],
                       cwd=root, capture_output=True, text=True, timeout=120,
                       env=env)
    return p.returncode, set(_FAILED.findall(p.stdout + p.stderr))


def put_lines(root: str, edits) -> None:
    """edits: [(rel, lineno, text), ...] applied together."""
    by_file: dict[str, list] = {}
    for rel, ln, text in edits:
        by_file.setdefault(rel, []).append((ln, text))
    for rel, es in by_file.items():
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8", newline="") as f:
            raw = f.read().split("\n")
        for ln, text in es:
            raw[ln - 1] = text
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(raw))


def enumerate_space(root: str, rel: str):
    """Every single-edit candidate the SHIPPED vocabulary proposes for every
    line of `rel` — the space the PAIR law's EXHAUSTED bit is about."""
    src = open(os.path.join(root, rel), encoding="utf-8", newline="").read()
    raw = src.split("\n")
    out, seen = [], set()
    for i, body in enumerate(raw):
        line = body.rstrip("\r")
        kinds = [k for k, (_n, _d, sig) in sorted(KINDS.items())
                 if sig.search(line)]
        for kind in kinds:                       # EMIT order = ascending bit
            obs = Observation(lineno=i + 1, kinds=kinds)
            obs.file, obs.root = rel, root
            obs.all_lines = [l.rstrip("\r") for l in raw]
            for cand in candidates(line, act_for(kind), obs):
                if isinstance(cand, SpanEdit) or cand == line:
                    continue
                key = (i + 1, cand)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"file": rel, "line": i + 1, "kind": kind,
                            "text": cand})
    return out


def main() -> None:
    do_pairs = "--pairs" in sys.argv
    log: dict = {}

    print("=" * 72)
    print("STEP A  why the body never opens the second fault file")
    root = fresh("packets")
    oracle = Oracle(root, python=PY, timeout=120)
    fails, out = oracle.failing_output()
    named = sorted(set(_FAILED.findall(out)))
    print(f"  oracle.failing_output() runs pytest with -x; failing tests it "
          f"names: {named}")
    print(f"  (the suite actually has 3 failing tests — see measure.out STEP 1)")
    log["failing_output_names"] = named
    for rel in FILES:
        p = build_packet(oracle, rel)
        has = p is not None and FAULT_LINE[rel] in (p.lines or [])
        print(f"  build_packet({rel:<13}) -> "
              f"{'None' if p is None else f'mode={p.mode} anchor_lines={p.lines}'}"
              f"   fault line {FAULT_LINE[rel]} in packet: {has}")
        log.setdefault("packets", {})[rel] = {
            "lines": None if p is None else p.lines,
            "mode": None if p is None else p.mode,
            "fault_line_in_packet": has}

    print("=" * 72)
    print("STEP B  the COMPLETE single-edit space over both fault files")
    space = []
    for rel in FILES:
        s = enumerate_space(root, rel)
        print(f"  {rel:<13} {len(s):3d} candidates "
              f"({len({c['line'] for c in s})} distinct lines)")
        space += s
    print(f"  TOTAL single-edit candidates: {len(space)}")
    log["space_size"] = len(space)

    print("=" * 72)
    print("STEP C  run every one of them (this is 'EXHAUSTED', measured)")
    base_root = fresh("base")
    _, base_fail = run_suite(base_root)
    print(f"  baseline failing: {len(base_fail)}")
    results, t0 = [], time.time()
    for c in space:
        r = fresh("cand")
        put_lines(r, [(c["file"], c["line"], c["text"])])
        try:
            rc, fails_ = run_suite(r)
        except subprocess.TimeoutExpired:
            rc, fails_ = 1, set(base_fail) | {"TIMEOUT"}
        rec = dict(c, n_failing=len(fails_), green=(rc == 0),
                   fixed=sorted(base_fail - fails_),
                   new=sorted(fails_ - base_fail))
        results.append(rec)
        flag = ("GREEN" if rec["green"] else
                "REDUCES" if rec["n_failing"] < len(base_fail) else "")
        if flag:
            print(f"    {c['file']}:{c['line']:<3} kind {c['kind']:<2} "
                  f"{c['text'].strip()[:40]:<42} {len(base_fail)} -> "
                  f"{rec['n_failing']}  {flag} {rec['fixed']}")
    secs = time.time() - t0
    greens = [r for r in results if r["green"]]
    reducers = [r for r in results if not r["green"]
                and r["n_failing"] < len(base_fail)]
    print(f"  {len(results)} candidates run in {secs:.1f}s "
          f"({secs / max(1, len(results)):.2f}s each)")
    print(f"  greens (a single edit that repairs the suite): {len(greens)}")
    print(f"  strict reducers: {len(reducers)} at sites "
          f"{sorted({(r['file'], r['line']) for r in reducers})}")
    log["completed_search"] = {"n": len(results), "seconds": secs,
                               "greens": len(greens),
                               "reducers": [(r["file"], r["line"], r["text"],
                                             r["n_failing"], r["fixed"])
                                            for r in reducers]}

    exhausted = len(greens) == 0
    partial = len(reducers) > 0
    sites = sorted({(r["file"], r["line"]) for r in reducers})
    fixed_sets = {}
    for r in reducers:
        fixed_sets.setdefault((r["file"], r["line"]), set()).update(r["fixed"])
    print(f"  tests each reducing site repairs: "
          f"{ {f'{f}:{l}': sorted(v) for (f, l), v in fixed_sets.items()} }")
    unreached = sorted(set(base_fail) - set().union(*fixed_sets.values()))
    print(f"  failing tests NO single edit anywhere repairs: {unreached}")
    log["fixed_sets"] = {f"{f}:{l}": sorted(v) for (f, l), v in fixed_sets.items()}
    log["unreached"] = unreached

    n = len(results)
    print("=" * 72)
    print("STEP D  cost of the two answers, measured")
    per = secs / max(1, n)
    print(f"  PARTITION (linear): {n} single-edit runs = {secs:.1f}s measured")
    print(f"  naive PAIR (quadratic): {n * (n - 1) // 2} combinations "
          f"~ {n * (n - 1) // 2 * per:.0f}s at the measured {per:.2f}s/run")
    by_file = {f: [r for r in results if r["file"] == f] for f in FILES}
    cross = len(by_file[FILES[0]]) * len(by_file[FILES[1]])
    print(f"  cross-site pairs only: {cross} combinations "
          f"~ {cross * per:.0f}s")
    log["cost"] = {"single_runs": n, "single_seconds": secs,
                   "naive_pairs": n * (n - 1) // 2, "cross_pairs": cross,
                   "seconds_per_run": per}

    if do_pairs:
        print("=" * 72)
        print("STEP E  cross-site pair sweep: how many pairs are GREEN, and")
        print("        is any of them CANCELING (members reduce nothing)?")
        alone = {(r["file"], r["line"], r["text"]): r for r in results}
        green_pairs, canceling_pairs, t1 = [], [], time.time()
        for a in by_file[FILES[0]]:
            for b in by_file[FILES[1]]:
                r = fresh("pair")
                put_lines(r, [(a["file"], a["line"], a["text"]),
                              (b["file"], b["line"], b["text"])])
                rc, fails_ = run_suite(r)
                if rc == 0:
                    ra = alone[(a["file"], a["line"], a["text"])]
                    rb = alone[(b["file"], b["line"], b["text"])]
                    red = (ra["n_failing"] < len(base_fail),
                           rb["n_failing"] < len(base_fail))
                    green_pairs.append((a["text"].strip(), b["text"].strip(), red))
                    if not any(red):
                        canceling_pairs.append((a["text"].strip(),
                                                b["text"].strip()))
        print(f"  swept {cross} cross-site pairs in {time.time() - t1:.1f}s")
        print(f"  green pairs: {len(green_pairs)}")
        for x in green_pairs:
            print(f"    {x[0]:<38} + {x[1]:<38} members reduce alone: {x[2]}")
        print(f"  CANCELING pairs (green jointly, neither member reduces): "
              f"{len(canceling_pairs)} {canceling_pairs}")
        log["pair_sweep"] = {"cross": cross, "green": green_pairs,
                             "canceling": canceling_pairs}
        canceling = bool(canceling_pairs)
    else:
        canceling = False
        print("  (pair sweep not run: pass --pairs)")

    print("=" * 72)
    print("STEP F  the byte from the COMPLETED search, and the ruling")
    # DISJOINT is DERIVED, never asserted: the failing tests repaired by each
    # reducing site must form pairwise disjoint groups, and there must be
    # more than one group. COUPLED is the one-group case.
    keys = sorted(fixed_sets)
    pairwise_disjoint = all(not (fixed_sets[keys[i]] & fixed_sets[keys[j]])
                            for i in range(len(keys))
                            for j in range(i + 1, len(keys)))
    covered = set().union(*fixed_sets.values()) if fixed_sets else set()
    disjoint = len(keys) > 1 and pairwise_disjoint
    coupled = len(keys) == 1
    byte = observe_bits(exhausted=exhausted, partial=partial,
                        disjoint=disjoint, coupled=coupled, cheap=True,
                        taught=False, canceling=canceling, capped=False)
    on = [b for k, b in enumerate(BITS) if byte >> k & 1]
    print(f"  EXHAUSTED={exhausted} (no single edit anywhere greens the suite)")
    print(f"  PARTIAL={partial} ({len(reducers)} single edits strictly reduce)")
    print(f"  DISJOINT={disjoint} ({len(keys)} reducing sites {keys}; groups "
          f"pairwise disjoint={pairwise_disjoint}; together they repair "
          f"{len(covered)} of the {len(base_fail)} failing tests; "
          f"unrepaired-by-any-single-edit: {unreached})")
    print(f"  COUPLED={coupled}, CANCELING={canceling}, CAPPED=False, "
          f"TAUGHT=False")
    print(f"  byte={byte} (0b{byte:08b}) {'|'.join(on)} -> "
          f"{pair_law(byte)} {ACTS[pair_law(byte)]}")
    log["byte"] = byte
    log["act"] = ACTS[pair_law(byte)]

    with open(os.path.join(HERE, "measured2.json"), "w") as f:
        json.dump(log, f, indent=2)
    print(f"wrote {os.path.join(HERE, 'measured2.json')}")


if __name__ == "__main__":
    main()
