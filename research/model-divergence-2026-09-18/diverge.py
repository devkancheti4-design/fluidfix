#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Where do two models that BOTH pass the tests still disagree? The witness is the interesting artefact.

`differ` exists to answer one question for the engine law: are two green candidates two different programs?
Point the same machinery across AUTHORS instead of across candidates and it answers a different one — given
one English specification, what did each model actually implement?

A passing test says only that two implementations agree on the handful of inputs someone wrote down. A
WITNESS — a concrete input on which they disagree — is the place where the prose was ambiguous and each
model's prior filled the gap its own way. That is recoverable without any access to weights, training data
or logits: it is a black-box behavioural probe, and its subject is the specification each model inferred,
not the model's internals.

Three readings, all mechanical:

  DIVERGENCE   among implementations that all PASS: the spec was ambiguous, and here is exactly where
  AGREEMENT    a spec on which everyone agrees everywhere the pool can see: the prose pinned it down
  STRUCTURE    AST fingerprints — comprehension vs loop, math module vs integer arithmetic, slice vs index

  PYTHONPATH=<fluidfix>/src python3 diverge.py
"""
from __future__ import annotations

import ast, itertools, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "certify-2026-09-18"))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import certify as C                                                    # noqa: E402
from fluidfix import differ                                            # noqa: E402

BUGS = HERE.parent / "model-bugs-2026-09-18"
WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "08d7e720-11a1-4c61-9902-ed128ff506ec/scratchpad/diverge")


def load():
    """(set, spec) -> {author: row}. Every model's answer to the same prose."""
    by = {}
    for f in sorted(BUGS.glob("written_*.json")):
        d = json.load(open(f))
        who = d["author"].replace("-hard", "")
        which = "boundary" if d["author"].endswith("-hard") else "ordinary"
        for r in d["rows"]:
            by.setdefault((which, r["name"]), {})[who] = r
    return by


# ------------------------------------------------------------------ STRUCTURE
FEATURES = {
    "comprehension": (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
    "while_loop": (ast.While,),
    "for_loop": (ast.For,),
}


def fingerprint(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}
    fp = {k: any(isinstance(n, t) for n in ast.walk(tree)) for k, t in FEATURES.items()}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    fp["math_module"] = bool({"ceil", "floor", "sqrt", "math"} & (names | attrs))
    fp["min_max"] = bool({"min", "max"} & names)
    fp["slice"] = any(isinstance(n, ast.Slice) for n in ast.walk(tree))
    fp["floordiv"] = any(isinstance(n, ast.FloorDiv) for n in ast.walk(tree))
    fp["early_return"] = sum(isinstance(n, ast.Return) for n in ast.walk(tree)) > 1
    fp["guard_clause"] = any(isinstance(n, ast.If) for n in ast.walk(tree))
    body = [l for l in code.split("\n") if l.strip() and not l.strip().startswith(('"""', "#"))]
    fp["lines"] = len(body)
    return fp


def main():
    by, out, t0 = load(), [], time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    print(f"{len(by)} specifications, each answered independently by every writer\n", flush=True)

    for n, ((which, spec), rows) in enumerate(sorted(by.items()), 1):
        any_row = next(iter(rows.values()))
        root = WORK / f"{which}_{spec}"
        C.build_repo(root, any_row["code"], any_row["tests"])
        try:
            name, arity = spec, len(ast.parse(any_row["code"]).body[0].args.args)
        except Exception:
            continue
        seeds = differ.harvest_seeds(str(root), name, arity)
        pool = differ.build_pool(seeds, arity)
        if not pool:
            print(f"[{n:>2}] {which:8} {spec:16} no in-domain inputs harvested — skipped", flush=True)
            continue

        vals, fps = {}, {}
        for who, r in sorted(rows.items()):
            res = differ.evaluate(str(root), C.MODULE, r["code"], "pkg", name, pool)
            if "values" in res:
                vals[who] = res["values"]
            fps[who] = fingerprint(r["code"])

        passing = sorted(w for w, r in rows.items() if r["passed"] and w in vals)
        rec = {"set": which, "spec": spec, "pool": len(pool), "passing": passing,
               "failing": sorted(w for w, r in rows.items() if not r["passed"]),
               "fingerprints": fps, "divergences": []}
        for a, b in itertools.combinations(passing, 2):
            va, vb = vals[a], vals[b]
            w = next((i for i in range(min(len(va), len(vb))) if va[i] != vb[i]), None)
            if w is not None:
                rec["divergences"].append({"a": a, "b": b, "input": pool[w],
                                           "a_says": va[w], "b_says": vb[w]})
        out.append(rec)
        if rec["divergences"]:
            d = rec["divergences"][0]
            print(f"[{n:>2}] {which:8} {spec:16} pool {len(pool):>3}  "
                  f"{len(rec['divergences'])} divergence(s) among {len(passing)} passing implementations"
                  f"\n      {d['a']} vs {d['b']} on {d['input']!r}: {d['a_says']}  vs  {d['b_says']}",
                  flush=True)
        else:
            print(f"[{n:>2}] {which:8} {spec:16} pool {len(pool):>3}  "
                  f"{len(passing)} passing implementations agree everywhere the pool can see", flush=True)

    (HERE / "divergence.json").write_text(json.dumps(out, indent=1))

    # ------------------------------------------------------------- the readings
    print("\n" + "=" * 92)
    amb = [r for r in out if r["divergences"]]
    print(f"AMBIGUOUS SPECIFICATIONS: {len(amb)} of {len(out)} — passing implementations that disagree "
          f"somewhere the tests never looked")
    for r in amb:
        for d in r["divergences"]:
            print(f"  {r['spec']:16} {d['a']:10} vs {d['b']:10} on {str(d['input'])[:34]:34} "
                  f"{str(d['a_says'])[:18]:18} vs {str(d['b_says'])[:18]}")

    print("\nWHO BREAKS WHAT — a spec everyone breaks is a hard spec; one model alone is a weak model")
    fails = {}
    for r in out:
        if r["failing"]:
            fails.setdefault(len(r["failing"]), []).append((r["spec"], r["failing"]))
    for k in sorted(fails, reverse=True):
        for spec, who in fails[k]:
            print(f"  {k} writer(s) broke {spec:16} {', '.join(who)}")

    print("\nSTRUCTURE — how often each writer reaches for a construct, across every spec it answered")
    keys = ["comprehension", "while_loop", "for_loop", "math_module", "min_max", "slice", "floordiv",
            "early_return", "guard_clause"]
    authors = sorted({w for r in out for w in r["fingerprints"]})
    print(f"  {'writer':12} " + " ".join(f"{k[:9]:>9}" for k in keys) + f" {'median lines':>13}")
    for w in authors:
        fps = [r["fingerprints"][w] for r in out if r["fingerprints"].get(w)]
        if not fps:
            continue
        line = " ".join(f"{sum(f.get(k, False) for f in fps) / len(fps):>9.0%}" for k in keys)
        med = sorted(f["lines"] for f in fps)[len(fps) // 2]
        print(f"  {w:12} {line} {med:>13}")
    print(f"\n{round(time.time() - t0, 1)}s  DIVERGE_DONE")


if __name__ == "__main__":
    main()
