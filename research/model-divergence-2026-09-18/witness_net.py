#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A net that GROWS the input space until it finds a witness — the pool's documented blind spot, attacked.

`differ` builds its pool once: the suite's own literals, plus local mutations, plus midpoints between them.
That is a plan fixed before any work is done, and it has a measured blind spot — a disagreement far from
anything the tests mention is unreachable by construction (`../certify-2026-09-18`: 0 of 14 found), which
differ's own docstring warns about with `w > 20` against `w > 120`.

The net's growth rule fits this exactly, and it is the SAME rule `../lake-2026-09-18/net.py` uses to hunt a
fault across a repository, reading rulings rather than a plan:

    REFUTED   no input in this region separates the two programs -> grow WIDER: the next magnitude out,
              the next argument position
    WITNESS   they disagree in this region -> grow DEEPER: bisect to localise where the boundary sits

and a Life memory over region SHAPES, so the second search of the same shape starts where the first one
finished instead of crawling out from the suite again.

Two arms, same rivals, same judge:

    FIXED   differ.build_pool -- today's behaviour
    NET     ruling-driven growth, bounded by an evaluation budget

  PYTHONPATH=<fluidfix>/src python3 witness_net.py [--cases 12] [--budget 24] [--cold]
"""
from __future__ import annotations

import argparse, ast, json, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "certify-2026-09-18"))
sys.path.insert(0, str(HERE.parent / "model-bugs-2026-09-18"))
sys.path.insert(0, str(HERE.parent / "lake-2026-09-18"))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import certify as C                                                    # noqa: E402
from fluidfix import differ                                            # noqa: E402
from life import Life                                                  # noqa: E402
import specs as S_ORD, specs_hard as S_HARD                            # noqa: E402

WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "79a458ef-6d23-4133-bc16-eb60d3ddd08d/scratchpad/witness")
MEMORY = HERE / "witness_memory.json"
K = 6                       # sample points per region-node


def rival(correct: str, name: str, arg: int, thresh: int) -> str:
    """A rival that agrees with `correct` everywhere except beyond a threshold the suite never mentions.

    This is the realistic shape, not a contrived point defect: a drifted bound, a clamp someone removed, a
    branch that only fires at scale. The disagreement occupies a REGION, which is what a search can find."""
    return (correct.rstrip("\n") + f"\n\n_ff_inner = {name}\n\n\n"
            f"def {name}(*a, **k):\n"
            f"    if len(a) > {arg} and isinstance(a[{arg}], (int, float)) "
            f"and not isinstance(a[{arg}], bool) and a[{arg}] > {thresh}:\n"
            "        return '**drifted**'\n"
            "    return _ff_inner(*a, **k)\n")


def probe(root: Path, name: str, a: str, b: str, pool: list[list]) -> tuple[list | None, int]:
    """Run both programs over these inputs. Returns (witness, evaluations paid)."""
    if not pool:
        return None, 0
    ra = differ.evaluate(str(root), C.MODULE, a, "pkg", name, pool)
    rb = differ.evaluate(str(root), C.MODULE, b, "pkg", name, pool)
    if "values" not in ra or "values" not in rb:
        return None, len(pool)
    va, vb = ra["values"], rb["values"]
    for i in range(min(len(va), len(vb))):
        if va[i] != vb[i]:
            return pool[i], len(pool)
    return None, len(pool)


def numeric_positions(seeds: list[list]) -> list[int]:
    if not seeds:
        return []
    return [i for i in range(len(seeds[0]))
            if all(isinstance(s[i], (int, float)) and not isinstance(s[i], bool) for s in seeds)]


def net_search(root: Path, name: str, a: str, b: str, seeds: list[list], budget: int,
               life: Life, rng: random.Random):
    """Grow the input region by the ruling, remembered shapes first. Returns (witness, evals, nodes)."""
    base = seeds[0] if seeds else None
    if base is None:
        return None, 0, 0, "no-seeds"
    positions = numeric_positions(seeds)
    if not positions:
        return None, 0, 0, "no-numeric-argument"

    remembered = [v for v, _c in reversed(life.history("regions")) if v.startswith("mag:")]
    start_mag = int(remembered[0].split(":")[1]) if remembered else 1

    frontier = []
    for pos in positions:                       # magnitude ladder, remembered rung first
        mag = start_mag
        for _ in range(9):
            frontier.append((pos, mag, mag * 10))
            mag *= 10
    if remembered:                              # a remembered magnitude is evidence about the RUNG
        frontier.sort(key=lambda n: abs(n[1] - start_mag))

    evals = nodes = 0
    for pos, lo, hi in frontier:
        if nodes >= budget:
            break
        nodes += 1
        pool = []
        for _ in range(K):
            cand = list(base)
            cand[pos] = rng.randint(int(lo), int(hi))
            pool.append(cand)
        w, e = probe(root, name, a, b, pool)
        evals += e
        if w is not None:                       # WITNESS -> deeper: bisect to LOCALISE the boundary
            # The first witness is only proof that a boundary exists somewhere below it. Bisecting says
            # WHERE, and that is the answer worth returning -- the smallest input that still separates the
            # two programs. Returning the first hit instead would make this whole branch decorative.
            # `lo` is only the rung's floor and was never shown to be a NON-witness, so bisecting from it
            # reports the rung boundary and calls it the answer. Start instead from a value the suite
            # itself exercises: both programs pass those tests, so they demonstrably agree there.
            anchor_w, anchor_e = probe(root, name, a, b, [list(base)])
            evals += anchor_e
            if anchor_w is not None:
                # The anchor itself separates them, so this rival is visible on a suite input -- it is
                # not the out-of-range blind spot this file exists to test. Say so rather than bisecting
                # a range whose lower end was never shown to agree.
                life.learn("regions", f"mag:{lo}"); life.save()
                return w, evals, nodes, "in-domain"
            left, right = base[pos], w[pos]     # left: VERIFIED same, right: known different
            probes = 0
            while nodes < budget and right - left > 1 and probes < 24:
                nodes += 1; probes += 1
                mid = (left + right) // 2
                cand = list(base); cand[pos] = mid
                w2, e2 = probe(root, name, a, b, [cand])
                evals += e2
                if w2 is not None:
                    right = mid
                else:
                    left = mid
            best = list(base); best[pos] = right
            life.learn("regions", f"mag:{lo}"); life.save()
            return best, evals, nodes, "localised"
        # REFUTED -> wider: the ladder's next rung, then the next argument position
    return None, evals, nodes, "exhausted"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=12); ap.add_argument("--budget", type=int, default=24)
    ap.add_argument("--cold", action="store_true"); ap.add_argument("--seed", type=int, default=20260918)
    a = ap.parse_args()
    if a.cold:
        MEMORY.unlink(missing_ok=True)
    life, rng = Life(str(MEMORY)), random.Random(a.seed)
    WORK.mkdir(parents=True, exist_ok=True)

    good = json.load(open(HERE.parent / "model-bugs-2026-09-18" / "written_haiku-hard.json"))
    good2 = json.load(open(HERE.parent / "model-bugs-2026-09-18" / "written_haiku.json"))
    allspecs = {n: (s, t) for n, s, t in list(S_ORD.SPECS) + list(S_HARD.SPECS)}
    correct = {r["name"]: r["code"] for r in good["rows"] + good2["rows"] if r["passed"]}

    rows, t0 = [], time.time()
    print(f"{'spec':16} {'threshold':>10} {'FIXED pool':>22} {'NET (grows by ruling)':>34}", flush=True)
    picked = 0
    for spec_name in sorted(correct):
        if picked >= a.cases:
            break
        code = correct[spec_name]
        _spec, tests = allspecs[spec_name]
        root = WORK / spec_name
        C.build_repo(root, code, tests)
        arity = len(ast.parse(code).body[0].args.args)
        seeds = differ.harvest_seeds(str(root), spec_name, arity)
        if not seeds or not numeric_positions(seeds):
            continue
        pos = numeric_positions(seeds)[0]
        # Above every value the suite mentions at this position, so the rival still PASSES the tests.
        # A rival that fails them is an ordinary bug the fixed pool already sees; the blind spot under
        # test is a divergence that lives entirely outside the suite's range.
        ceiling = max(abs(s[pos]) for s in seeds)
        thresh = rng.choice([500, 5000, 50000])
        while thresh <= ceiling:
            thresh *= 10
        b = rival(code, spec_name, pos, thresh)
        picked += 1

        fixed_pool = differ.build_pool(seeds, arity)
        wf, ef = probe(root, spec_name, code, b, fixed_pool)
        wn, en, nn, how = net_search(root, spec_name, code, b, seeds, a.budget, life, rng)
        rows.append({"spec": spec_name, "arg": pos, "threshold": thresh,
                     "fixed_found": wf is not None, "fixed_evals": ef,
                     "net_found": wn is not None, "net_evals": en, "net_nodes": nn, "net_how": how,
                     "net_witness": wn})
        print(f"{spec_name:16} {thresh:>10} "
              f"{('FOUND' if wf else 'missed') + f' ({ef} evals)':>22} "
              f"{('FOUND at ' + str(wn[pos]) if wn else 'missed') + f' ({en} evals, {nn} nodes, {how})':>46}",
              flush=True)

    (HERE / f"witness_net{'_cold' if a.cold else '_warm'}.json").write_text(json.dumps(
        {"cases": len(rows), "budget": a.budget, "memory": "cold" if a.cold else "warm",
         "rows": rows}, indent=1, default=str))
    f_ok = sum(r["fixed_found"] for r in rows); n_ok = sum(r["net_found"] for r in rows)
    print(f"\nFIXED pool  {f_ok}/{len(rows)} witnesses, {sum(r['fixed_evals'] for r in rows)} evaluations")
    print(f"NET         {n_ok}/{len(rows)} witnesses, {sum(r['net_evals'] for r in rows)} evaluations, "
          f"{sum(r['net_nodes'] for r in rows)} nodes")
    print(f"{round(time.time() - t0, 1)}s  WITNESS_DONE")


if __name__ == "__main__":
    main()
