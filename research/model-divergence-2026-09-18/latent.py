#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Is there STABLE structure in how writers resolve undefined inputs, or does the grouping shuffle?

The behavioural probe (`diverge.py`) shows that writers passing the same tests still disagree on inputs the
prose never defined. The interesting follow-up is whether those choices are a stable signature — the same
writers agreeing with each other again and again, which is what you would expect if the choice were read
out of something shared and structured — or whether each ambiguous input partitions the writers a different
way, which is what you would expect from a local, per-task coin flip.

That distinction is testable from behaviour alone, and this tests it.

  observed   for each pair of writers, the fraction of undefined inputs where they gave the SAME answer
  null       the same partitions with writer labels shuffled independently per input, 20000 times --
             so the null preserves how many writers agree on each input and destroys only WHO

A pair sitting above its null means a stable alliance. Every pair inside its null means the agreements are
real but unaligned: structure per input, none across inputs.

  PYTHONPATH=<fluidfix>/src python3 latent.py
"""
from __future__ import annotations

import ast, itertools, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "certify-2026-09-18"))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import certify as C                                                    # noqa: E402
from fluidfix import differ                                            # noqa: E402
from diverge import load, WORK                                         # noqa: E402

TRIALS = 20000


def main():
    by = load()
    WORK.mkdir(parents=True, exist_ok=True)
    inputs = []                      # one entry per undefined input: {writer: answer}

    for (which, spec), rows in sorted(by.items()):
        any_row = next(iter(rows.values()))
        root = WORK / f"{which}_{spec}"
        C.build_repo(root, any_row["code"], any_row["tests"])
        try:
            arity = len(ast.parse(any_row["code"]).body[0].args.args)
        except Exception:
            continue
        pool = differ.build_pool(differ.harvest_seeds(str(root), spec, arity), arity)
        if not pool:
            continue
        vals = {}
        for who, r in sorted(rows.items()):
            if not r["passed"]:
                continue             # a broken implementation's answers are not a convention
            res = differ.evaluate(str(root), C.MODULE, r["code"], "pkg", spec, pool)
            if "values" in res:
                vals[who] = res["values"]
        if len(vals) < 2:
            continue
        for i in range(len(pool)):
            answers = {w: v[i] for w, v in vals.items() if i < len(v)}
            if len(set(answers.values())) > 1:          # the prose did not decide this input
                inputs.append({"spec": spec, "input": pool[i], "answers": answers})

    writers = sorted({w for e in inputs for w in e["answers"]})
    print(f"{len(inputs)} undefined inputs across {len({e['spec'] for e in inputs})} specifications, "
          f"writers: {', '.join(writers)}\n")

    # ---- how fragmented is each undefined input?
    spread = {}
    for e in inputs:
        k = len(set(e["answers"].values()))
        spread[k] = spread.get(k, 0) + 1
    print("distinct answers per undefined input: " +
          ", ".join(f"{k} answers x{v}" for k, v in sorted(spread.items())))

    # ---- observed pairwise agreement
    def agreement(assignments):
        agree, total = {}, {}
        for e, amap in zip(inputs, assignments):
            for a, b in itertools.combinations(sorted(amap), 2):
                total[(a, b)] = total.get((a, b), 0) + 1
                if amap[a] == amap[b]:
                    agree[(a, b)] = agree.get((a, b), 0) + 1
        return {p: agree.get(p, 0) / total[p] for p in total}, total

    obs, total = agreement([e["answers"] for e in inputs])

    rng = random.Random(20260918)
    null = {p: [] for p in obs}
    for _ in range(TRIALS):
        shuffled = []
        for e in inputs:
            ws = list(e["answers"]); vs = list(e["answers"].values())
            rng.shuffle(vs)                       # keep the partition shape, destroy WHO
            shuffled.append(dict(zip(ws, vs)))
        a, _ = agreement(shuffled)
        for p in null:
            null[p].append(a.get(p, 0.0))

    print(f"\n{'pair':26} {'n':>4} {'observed':>9} {'null mean':>10} {'null 95th':>10}   verdict")
    rows = []
    for p in sorted(obs, key=lambda q: -obs[q]):
        d = sorted(null[p]); mean = sum(d) / len(d); p95 = d[int(0.95 * len(d))]
        above = obs[p] > p95
        rows.append({"pair": list(p), "n": total[p], "observed": round(obs[p], 3),
                     "null_mean": round(mean, 3), "null_p95": round(p95, 3), "above_null": above})
        print(f"{p[0] + ' / ' + p[1]:26} {total[p]:>4} {obs[p]:>9.0%} {mean:>10.0%} {p95:>10.0%}   "
              f"{'ABOVE CHANCE' if above else 'inside chance'}")

    (HERE / "latent.json").write_text(json.dumps(
        {"undefined_inputs": len(inputs), "trials": TRIALS, "spread": spread, "pairs": rows,
         "detail": [{"spec": e["spec"], "input": e["input"], "answers": e["answers"]} for e in inputs]},
        indent=1, default=str))
    n_above = sum(r["above_null"] for r in rows)
    print(f"\n{n_above} of {len(rows)} pairs agree more often than label-shuffling predicts.")
    print("LATENT_DONE")


if __name__ == "__main__":
    main()
