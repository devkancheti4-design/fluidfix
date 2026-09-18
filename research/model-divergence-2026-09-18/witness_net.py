#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A net over input space: the frontier GROWS from rulings, and the memory holds a SHAPE, not a coordinate.

`differ` builds its pool once -- the suite's literals, local mutations, midpoints -- and its blind spot is
measured: a divergence far from anything the tests mention is unreachable by construction
(`../certify-2026-09-18`: 0 of 14). The same rule `../lake-2026-09-18/net.py` uses to hunt a fault across a
repository applies here, and it has two halves that must BOTH be respected:

  GROWTH IS NOT A PLAN. The search starts as ONE node -- the smallest region worth trying, just beyond what
  the suite exercises -- and every later node is spawned by a ruling:

      REFUTED   nothing in this region separates the two programs  -> WIDER: one rung further out in this
                argument, and this same rung in the other arguments
      WITNESS   they disagree here                                  -> DEEPER: bisect between a point the
                suite proves they agree on and the witness, until the boundary is exact

    Enumerating the rungs in advance would make this waves again, which is the thing the net replaced.

  THE MEMORY HOLDS A SHAPE. `mag:1000000` is a coordinate: it cannot transfer to a function whose inputs
  live at a different scale. What transfers is the RATIO to the suite's own range -- "the divergence lives
  about a hundred times beyond what the tests exercise" -- which is the analogue of `kind:7` carrying from
  rich to arrow. That is what is learned, and a remembered ratio seeds the first node.

A remembered shape is worth what its scarcity is worth, so both corpora are measured:

    --varied     each rival's threshold at an unrelated ratio  (no recurring shape: memory should not pay)
    --recurring  thresholds in one ratio band                  (a recurring shape: memory should pay)

  PYTHONPATH=<fluidfix>/src python3 witness_net.py [--cases 12] [--budget 40] [--recurring] [--cold]
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
K = 5                       # sample points per region-node
FIRST_RATIO = 2.0           # the seed node: just beyond what the suite exercises


def rival(correct: str, name: str, arg: int, thresh: int) -> str:
    """Agrees everywhere the suite looks, disagrees only beyond a threshold outside its range."""
    return (correct.rstrip("\n") + f"\n\n_ff_inner = {name}\n\n\n"
            f"def {name}(*a, **k):\n"
            f"    if len(a) > {arg} and isinstance(a[{arg}], (int, float)) "
            f"and not isinstance(a[{arg}], bool) and a[{arg}] > {thresh}:\n"
            "        return '**drifted**'\n"
            "    return _ff_inner(*a, **k)\n")


def probe(root, name, a, b, pool):
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


def numeric_positions(seeds):
    return [i for i in range(len(seeds[0]))
            if all(isinstance(s[i], (int, float)) and not isinstance(s[i], bool) for s in seeds)] \
        if seeds else []


def net_search(root, name, a, b, seeds, budget, life, rng):
    """One seed node; every other node is spawned by the ruling of the node before it."""
    base, positions = seeds[0], numeric_positions(seeds)
    if not positions:
        return None, 0, 0, "no-numeric-argument", None, 0, 0
    ceiling = max(max(abs(s[p]) for s in seeds) for p in positions) or 1

    remembered = [float(v.split(":")[1]) for v, _c in reversed(life.history("ratio"))
                  if v.startswith("ratio:")]
    seed_ratio = remembered[0] if remembered else FIRST_RATIO

    seen, evals, nodes = set(), 0, 0
    search_nodes = bisect_nodes = 0

    # ---- REPLAY: a remembered boundary is checked DIRECTLY, in two probes, before any search.
    # Bisection is logarithmic, so a memory that merely narrows the bracket saves ONE node -- measured.
    # The only way a memory beats a log search is to skip it, and that needs the boundary itself, proved
    # here rather than trusted: the remembered point must separate the programs and the point below it
    # must not. If either check fails, nothing is assumed and the ordinary search runs.
    for r in remembered[:3]:
        cand_hi = list(base); cand_hi[positions[0]] = int(ceiling * r)
        cand_lo = list(base); cand_lo[positions[0]] = int(ceiling * r) - 1
        whi, e1 = probe(root, name, a, b, [cand_hi]); evals += e1; nodes += 1
        if whi is None:
            continue
        wlo, e2 = probe(root, name, a, b, [cand_lo]); evals += e2; nodes += 1
        if wlo is None:
            return cand_hi, evals, nodes, "replayed", round(r, 3), 0, nodes

    frontier = [(positions[0], seed_ratio)]          # ONE node. Not a ladder.

    while frontier and nodes < budget:
        pos, ratio = frontier.pop(0)
        if (pos, round(ratio, 6)) in seen:
            continue
        seen.add((pos, round(ratio, 6)))
        nodes += 1; search_nodes += 1
        lo, hi = ceiling * ratio, ceiling * ratio * 10
        pool = [list(base) for _ in range(K)]
        for cand in pool:
            cand[pos] = rng.randint(int(lo) + 1, max(int(hi), int(lo) + 2))
        w, e = probe(root, name, a, b, pool)
        evals += e

        if w is not None:                            # WITNESS -> DEEPER
            anchor_w, ae = probe(root, name, a, b, [list(base)]); evals += ae
            if anchor_w is not None:
                return w, evals, nodes, "in-domain", None, search_nodes, bisect_nodes
            # SPEND THE MEMORY ON THE RIGHT HALF. Measured: the wider search costs ~1 node per case and
            # the bisection ~13, so seeding the SEARCH saves nothing and starting further out makes the
            # bracket wider, which costs more. A remembered ratio is evidence about WHERE THE BOUNDARY
            # SITS, so it belongs in the bracket. It is never assumed: the remembered point is probed,
            # and whichever side it falls on is the side it tightens.
            left, right, hops = base[pos], w[pos], 0
            if remembered:
                guess = int(ceiling * remembered[0])
                if left < guess < right:
                    cand = list(base); cand[pos] = guess
                    gw, ge = probe(root, name, a, b, [cand]); evals += ge; nodes += 1; bisect_nodes += 1
                    if gw is not None:
                        right = guess           # the boundary is at or below the remembered place
                    else:
                        left = guess            # it is above it
            while nodes < budget and right - left > 1 and hops < 32:
                nodes += 1; hops += 1; bisect_nodes += 1
                mid = (left + right) // 2
                cand = list(base); cand[pos] = mid
                w2, e2 = probe(root, name, a, b, [cand]); evals += e2
                left, right = (left, mid) if w2 is not None else (mid, right)
            learned = round(right / ceiling, 3)      # the SHAPE: how far out, relative to the suite
            life.learn("ratio", f"ratio:{learned}"); life.save()
            best = list(base); best[pos] = right
            return best, evals, nodes, "localised", learned, search_nodes, bisect_nodes

        # REFUTED -> WIDER, and the successors are spawned HERE, by this refusal
        frontier.append((pos, ratio * 10))                       # further out, same argument
        for other in positions:                                  # this same rung, other arguments
            if other != pos:
                frontier.append((other, ratio))
    return None, evals, nodes, "exhausted", None, search_nodes, bisect_nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=12); ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--recurring", action="store_true",
                    help="plant every threshold in ONE ratio band, so a shape recurs")
    ap.add_argument("--exact", action="store_true",
                    help="the SAME ratio every time: exact recurrence, which a memory can replay")
    ap.add_argument("--cold", action="store_true"); ap.add_argument("--seed", type=int, default=20260918)
    a = ap.parse_args()
    kind = "exact" if a.exact else "recurring" if a.recurring else "varied"
    tag = kind + ("_cold" if a.cold else "_warm")
    memory = HERE / f"witness_memory_{kind}.json"
    if a.cold:
        memory.unlink(missing_ok=True)
    life, rng = Life(str(memory)), random.Random(a.seed)
    WORK.mkdir(parents=True, exist_ok=True)

    rows_src = (json.load(open(HERE.parent / "model-bugs-2026-09-18" / "written_haiku-hard.json"))["rows"]
                + json.load(open(HERE.parent / "model-bugs-2026-09-18" / "written_haiku.json"))["rows"])
    correct = {r["name"]: r["code"] for r in rows_src if r["passed"]}
    allspecs = {n: (s, t) for n, s, t in list(S_ORD.SPECS) + list(S_HARD.SPECS)}

    rows, t0, picked = [], time.time(), 0
    print(f"[{tag}] seed node at {FIRST_RATIO}x the suite's range; every other node spawned by a ruling",
          flush=True)
    print(f"{'spec':16} {'ratio planted':>14} {'FIXED':>16} {'NET':>40}", flush=True)
    for spec_name in sorted(correct):
        if picked >= a.cases:
            break
        code = correct[spec_name]
        _spec, tests = allspecs[spec_name]
        root = WORK / spec_name
        C.build_repo(root, code, tests)
        arity = len(ast.parse(code).body[0].args.args)
        seeds = differ.harvest_seeds(str(root), spec_name, arity)
        pos_list = numeric_positions(seeds)
        if not seeds or not pos_list:
            continue
        pos = pos_list[0]
        ceiling = max(max(abs(s[p]) for s in seeds) for p in pos_list) or 1
        # the RATIO is the planted shape; absolute thresholds differ wildly between specs either way
        ratio = (100.0 if a.exact else
                 rng.uniform(80, 120) if a.recurring else rng.choice([3, 30, 300, 3000]))
        thresh = int(ceiling * ratio)
        b = rival(code, spec_name, pos, thresh)
        picked += 1

        wf, ef = probe(root, spec_name, code, b, differ.build_pool(seeds, arity))
        wn, en, nn, how, learned, sn, bn = net_search(
            root, spec_name, code, b, seeds, a.budget, life, rng)
        rows.append({"spec": spec_name, "arg": pos, "ceiling": ceiling, "ratio": round(ratio, 2),
                     "threshold": thresh, "fixed_found": wf is not None, "fixed_evals": ef,
                     "net_found": wn is not None, "net_evals": en, "net_nodes": nn, "net_how": how,
                     "learned_ratio": learned, "boundary": wn[pos] if wn else None,
                     "search_nodes": sn, "bisect_nodes": bn})
        print(f"{spec_name:16} {round(ratio, 1):>13}x {('FOUND' if wf else 'missed'):>16} "
              f"{(('boundary ' + str(wn[pos])) if wn else 'missed') + f'  {nn} nodes, {en} evals':>40}",
              flush=True)

    (HERE / f"witness_net_{tag}.json").write_text(json.dumps(
        {"mode": tag, "budget": a.budget, "cases": len(rows), "rows": rows}, indent=1, default=str))
    print(f"\nFIXED  {sum(r['fixed_found'] for r in rows)}/{len(rows)}")
    print(f"NET    {sum(r['net_found'] for r in rows)}/{len(rows)}  "
          f"{sum(r['net_nodes'] for r in rows)} nodes, {sum(r['net_evals'] for r in rows)} evals")
    print(f"exact boundary: {sum(1 for r in rows if r['boundary'] == r['threshold'] + 1)}/{len(rows)}")
    rep = sum(1 for r in rows if r["net_how"] == "replayed")
    print(f"  replayed straight from memory: {rep}/{len(rows)}")
    print(f"  of those nodes: {sum(r['search_nodes'] for r in rows)} were the WIDER search "
          f"(what memory can shorten), {sum(r['bisect_nodes'] for r in rows)} were the DEEPER bisection")
    print(f"{round(time.time() - t0, 1)}s  WITNESS_DONE")


if __name__ == "__main__":
    main()
