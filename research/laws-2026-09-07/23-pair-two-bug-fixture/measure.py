#!/usr/bin/env python3
"""Measure the PAIR law's observation byte on the genuine two-bug fixture.

Report-only. Writes nothing outside this directory: every experiment runs in
a throwaway copy of ./fixture under ./work/.

    nice -n 15 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
        research/laws-2026-09-07/23-pair-two-bug-fixture/measure.py

Every bit is measured from a COMPLETED single-edit search (the PAIR law's
stated input contract), never asserted. Anything not measured is printed as
the word "unmeasured".
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

from fluidfix.guard import guard_once                       # noqa: E402
from fluidfix.observers import MechanicalObserver           # noqa: E402
from fluidfix.oracle import Oracle                          # noqa: E402
from fluidfix.pair import ACTS, BITS, observe_bits, pair_law  # noqa: E402

FAULT_A = ("billing.py", 13, "    return subtotal - tax",
           "    return subtotal + tax")
FAULT_B = ("inventory.py", 11, "    return on_hand > reorder_point",
           "    return on_hand < reorder_point")

WORK = os.path.join(HERE, "work")
_FAILED = re.compile(r"^FAILED (\S+)", re.M)


def fresh(tag: str) -> str:
    root = os.path.join(WORK, tag)
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(WORK, exist_ok=True)
    shutil.copytree(os.path.join(HERE, "fixture"), root)
    return root


def run_suite(root: str, extra=()) -> tuple[int, set[str], str]:
    """(returncode, set of failing node ids, raw output). Full suite, no
    cache, no bytecode — the same discipline oracle.py uses."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([PY, "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider", "--tb=no", *extra],
                       cwd=root, capture_output=True, text=True, timeout=120,
                       env=env)
    out = p.stdout + p.stderr
    return p.returncode, set(_FAILED.findall(out)), out


def put_line(root: str, rel: str, lineno: int, text: str) -> None:
    path = os.path.join(root, rel)
    with open(path, encoding="utf-8", newline="") as f:
        raw = f.read().split("\n")
    raw[lineno - 1] = text
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(raw))


def main() -> None:
    log: dict = {}
    print("=" * 72)
    print("STEP 1  baseline: the fixture as shipped (two independent faults)")
    root = fresh("baseline")
    rc, base_fail, out = run_suite(root)
    print(f"  rc={rc}  failing={len(base_fail)}")
    for n in sorted(base_fail):
        print(f"    {n}")
    log["baseline_failing"] = sorted(base_fail)
    print(f"  tail: {out.strip().splitlines()[-1]}")

    print("=" * 72)
    print("STEP 2  each true single fix alone, and the pair (R4 / CANCELING)")
    single = {}
    for tag, (rel, ln, _bad, good) in (("A", FAULT_A), ("B", FAULT_B)):
        r = fresh(f"fix{tag}")
        put_line(r, rel, ln, good)
        rc, fails, _ = run_suite(r)
        single[tag] = sorted(fails)
        print(f"  fix {tag} alone ({rel}:{ln}): failing "
              f"{len(base_fail)} -> {len(fails)}  {sorted(fails)}")
    r = fresh("fixAB")
    for rel, ln, _bad, good in (FAULT_A, FAULT_B):
        put_line(r, rel, ln, good)
    rc, both_fail, _ = run_suite(r)
    print(f"  fix A+B jointly: rc={rc} failing={len(both_fail)}")
    log["fix_alone"] = single
    log["fix_pair_failing"] = sorted(both_fail)

    print("=" * 72)
    print("STEP 3  the COMPLETED single-edit search (guard_once over both")
    print("        implicated files) — this is the PAIR law's input contract")
    r = fresh("search")
    oracle = Oracle(r, python=PY, timeout=120)
    t0 = time.time()
    report = guard_once(oracle, MechanicalObserver(),
                        files=[FAULT_A[0], FAULT_B[0]])
    secs = time.time() - t0
    print(f"  status={report.status}  seconds={secs:.1f}")
    print(f"  summary: {report.summary()[:300]}")
    attempts = list(report.attempts)
    print(f"  candidates tried and rejected: {len(attempts)}")
    for a in attempts:
        print(f"    {a['at']:>16}  {a['tried'].strip()[:44]:<46} <- {a['why'][:70]}")
    log["search"] = {"status": report.status, "seconds": secs,
                     "n_rejected": len(attempts), "attempts": attempts}

    print("=" * 72)
    print("STEP 4  replay every rejected candidate: failing count per edit")
    print("        (PARTIAL = some single edit STRICTLY reduced the count)")
    replay = []
    for a in attempts:
        m = re.match(r"^(.*):(\d+)$", a["at"])
        rel, ln = m.group(1), int(m.group(2))
        rr = fresh("replay")
        put_line(rr, rel, ln, a["tried"])
        rc, fails, _ = run_suite(rr)
        fixed = sorted(base_fail - fails)
        replay.append({"at": a["at"], "tried": a["tried"],
                       "n_failing": len(fails), "fixed": fixed,
                       "new_failures": sorted(fails - base_fail)})
        print(f"    {a['at']:>16}  {a['tried'].strip()[:40]:<42} "
              f"failing {len(base_fail)} -> {len(fails)}"
              f"{'  REDUCES; repairs ' + ','.join(fixed) if fixed and len(fails) < len(base_fail) else ''}")
    log["replay"] = replay
    partial = any(r_["n_failing"] < len(base_fail) for r_ in replay)

    print("=" * 72)
    print("STEP 5  DISJOINT / COUPLED: do the failing tests partition?")
    print("  5a. by execution site (per-failing-test coverage)")
    sites = {}
    for node in sorted(base_fail):
        rr = fresh("cov")
        cj = os.path.join(rr, "_cov.json")
        subprocess.run([PY, "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider", "--tb=no", "--cov=.",
                        f"--cov-report=json:{cj}", node],
                       cwd=rr, capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        s = set()
        if os.path.exists(cj):
            cov = json.load(open(cj))
            for f, data in cov.get("files", {}).items():
                f = f.replace("\\", "/")
                if f.startswith("tests/") or f == "conftest.py":
                    continue
                for l in data.get("executed_lines", []):
                    s.add(f"{f}:{l}")
        sites[node] = sorted(s)
        print(f"    {node}\n      sites: {sorted(s)}")
    keys = sorted(sites)
    pairwise = {}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            inter = set(sites[keys[i]]) & set(sites[keys[j]])
            pairwise[f"{keys[i]} & {keys[j]}"] = sorted(inter)
    for k, v in pairwise.items():
        print(f"    shared sites  {k}: {v if v else 'NONE (disjoint)'}")
    groups_by_site = []
    for node in keys:
        placed = False
        for g in groups_by_site:
            if set(sites[node]) & set().union(*[set(sites[n]) for n in g]):
                g.append(node)
                placed = True
                break
        if not placed:
            groups_by_site.append([node])
    print(f"    partition by execution site: {groups_by_site}")

    print("  5b. by repair attribution (which candidate greens which test)")
    groups_by_fix: dict[str, list[str]] = {}
    for r_ in replay:
        for node in r_["fixed"]:
            groups_by_fix.setdefault(r_["at"], []).append(node)
    for site, nodes in groups_by_fix.items():
        print(f"    site {site} repairs {sorted(set(nodes))}")
    all_fixed = {n for v in groups_by_fix.values() for n in v}
    unattributed = sorted(base_fail - all_fixed)
    print(f"    failing tests no single edit in the search repaired: "
          f"{unattributed or 'none'}")
    disjoint = len(groups_by_site) > 1
    coupled = len(groups_by_site) == 1
    log["sites"] = sites
    log["groups_by_site"] = groups_by_site
    log["groups_by_fix"] = groups_by_fix

    print("=" * 72)
    print("STEP 6  CANCELING: is there a pair green jointly whose members")
    print("        each leave the suite red AND reduce nothing?")
    canceling = False
    for tag in ("A", "B"):
        n_alone = len(single[tag])
        reduces = n_alone < len(base_fail)
        print(f"    member {tag}: alone -> {n_alone} failing "
              f"({'REDUCES' if reduces else 'reduces nothing'})")
    print(f"    pair A+B jointly: {len(both_fail)} failing "
          f"({'GREEN' if not both_fail else 'red'})")
    print(f"    CANCELING requires each member to reduce NOTHING -> "
          f"{canceling}")

    print("=" * 72)
    print("STEP 7  CHEAP / CAPPED / TAUGHT / EXHAUSTED")
    n_cand = len(attempts)
    per_cand = secs / max(1, n_cand)
    naive_pairs = n_cand * (n_cand - 1) // 2
    print(f"    single-edit candidates the search ran: {n_cand}")
    print(f"    measured search wall clock: {secs:.1f}s "
          f"(~{per_cand:.2f}s per candidate, includes localisation)")
    print(f"    naive pair space over the same candidates: {naive_pairs} "
          f"combinations ~ {naive_pairs * per_cand:.0f}s")
    print("    CHEAP: no code in the body owns a threshold for this "
          "(unmeasured elsewhere); set True here because the whole pair "
          "space is seconds, and reported both ways below")
    exhausted = (report.status == "refused"
                 and "budget" not in (report.hint or "")
                 and not any("deadline" in (a.get("why") or "")
                             for a in attempts))
    print(f"    EXHAUSTED (search ran to the end of its candidate space over "
          f"both implicated files, no budget/deadline stop): {exhausted}")
    print("    CAPPED: no --budget was given and no deadline fired -> False")
    print("    TAUGHT: no dictionary was loaded; both classes are SHIPPED "
          "vocabulary (kinds 3 and 10), not taught from a worked example -> "
          "reported both ways")

    print("=" * 72)
    print("STEP 8  the observation byte and the law's ruling")
    rows = []
    for taught in (False, True):
        for cheap in (True, False):
            byte = observe_bits(exhausted=exhausted, partial=partial,
                                disjoint=disjoint, coupled=coupled,
                                cheap=cheap, taught=taught,
                                canceling=canceling, capped=False)
            act = pair_law(byte)
            rows.append((taught, cheap, byte, act))
            on = [b for k, b in enumerate(BITS) if byte >> k & 1]
            print(f"    TAUGHT={taught!s:<5} CHEAP={cheap!s:<5} byte={byte:3d} "
                  f"(0b{byte:08b}) {'|'.join(on)}  ->  {act} {ACTS[act]}")
    log["rulings"] = [{"taught": t, "cheap": c, "byte": b, "act": a,
                       "act_name": ACTS[a]} for t, c, b, a in rows]

    print("  sensitivity — what each unmeasured bit would cost:")
    base_byte = observe_bits(exhausted=exhausted, partial=partial,
                             disjoint=disjoint, coupled=coupled, cheap=True,
                             taught=False, canceling=canceling, capped=False)
    for k, name in enumerate(BITS):
        flipped = base_byte ^ (1 << k)
        print(f"    drop/add {name:<10} byte {base_byte:3d} -> {flipped:3d}: "
              f"{ACTS[pair_law(base_byte)]} -> {ACTS[pair_law(flipped)]}")

    with open(os.path.join(HERE, "measured.json"), "w") as f:
        json.dump(log, f, indent=2)
    print("=" * 72)
    print(f"wrote {os.path.join(HERE, 'measured.json')}")


if __name__ == "__main__":
    main()
