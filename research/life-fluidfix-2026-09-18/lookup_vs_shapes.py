#!/usr/bin/env python3
"""Is it a lookup table? Measure it: three arms, the same stream of bugs, the same judge.

A lookup table answers what it has been shown. A shape is a signal plus a transform, so it answers lines it
has never seen. The difference is not rhetorical, it is a curve, and this draws it.

Three arms face the same stream of distinct, generated bugs, each with a test that catches it:

  FILE TABLE   remembers whole programs: key = the exact program text -> the fixed program
  LINE TABLE   remembers broken lines:   key = the exact broken line  -> the fixed line
               (a fairer table: it hits whenever the identical line recurs anywhere)
  SHAPES       fluidfix's vocabulary: a fixed handful of rules, judged by the same test

For each arm: how many entries it must store, and what fraction of the NEXT, unseen bugs it repairs. Every
repair in every arm is accepted only because the instance's own test passed.

  PYTHONPATH=<fluidfix>/src python3 lookup_vs_shapes.py [--per-shape 40] [--seed 20260918]
"""
import argparse, hashlib, json, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from life_fluidfix import run_test, shapes_repair                         # noqa: E402

DICT = str(HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py")

NAMES = ["total", "count", "items", "rows", "values", "scores", "budget", "limit", "width", "depth",
         "size", "offset", "cursor", "weight", "height", "span", "window", "batch", "chunk", "stride"]
FUNCS = ["compute", "measure", "tally", "resize", "collect", "bound", "advance", "shrink", "expand",
         "fit", "pack", "trim", "scale", "align", "settle", "balance", "reduce", "sample"]


def gen(shape, rng):
    """One distinct instance of a shape: its own names, values and shell, with a test that catches it."""
    f = rng.choice(FUNCS) + str(rng.randint(10, 99))
    a, b = rng.sample(NAMES, 2)          # two distinct names: `def f(total, total)` is a syntax error
    if shape == "strictness":
        lim = rng.randint(2, 40)
        # the branches must DIFFER at the boundary, or no flip of the comparison changes behaviour
        code = f"def {f}({a}, {b}):\n    if {a} > {b}:\n        return 'over'\n    return 'ok'\n"
        return code, f"assert {f}({lim}, {lim}) == 'over' and {f}({lim - 1}, {lim}) == 'ok'"
    if shape == "additive":
        x, y, z = rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 9)
        code = f"def {f}({a}, {b}, c):\n    return {a} * {b} - c\n"
        return code, f"assert {f}({x}, {y}, {z}) == {x * y + z}"
    if shape == "literal":
        n = rng.randint(2, 6)
        code = f"def {f}(xs):\n    return xs[{n + 1}:]\n"
        return code, f"assert {f}(list(range(10))) == list(range({n}, 10))"
    if shape == "augmented":
        code = f"def {f}(xs):\n    {a} = 0\n    for v in xs:\n        {a} -= v\n    return {a}\n"
        vals = [rng.randint(1, 9) for _ in range(3)]
        return code, f"assert {f}({vals}) == {sum(vals)}"
    if shape == "lenm1":
        code = f"def {f}({a}):\n    return len({a})\n"
        n = rng.randint(2, 7)
        return code, f"assert {f}({list(range(n))}) == {n - 1}"
    if shape == "ifnot":
        code = f"def {f}({a}):\n    if {a}:\n        return None\n    return {a}[0]\n"
        return code, f"assert {f}([]) is None and {f}([7]) == 7"
    raise ValueError(shape)


SHAPES = ["strictness", "additive", "literal", "augmented", "lenm1", "ifnot"]


def broken_line(code):
    """The line a table would key on: the one the fix has to change."""
    for l in code.split("\n"):
        s = l.strip()
        if s and not s.startswith("def ") and not s.startswith("for ") and s != "return None":
            if any(t in s for t in (" > ", " - ", "[", " -= ", "len(", "if ")):
                return l
    return code.split("\n")[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-shape", type=int, default=40); ap.add_argument("--seed", type=int, default=20260918)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    stream, seen_keys = [], set()
    while len(stream) < a.per_shape * len(SHAPES):
        shape = SHAPES[len(stream) % len(SHAPES)]
        code, test = gen(shape, rng)
        key = hashlib.md5(code.encode()).hexdigest()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if run_test(code, test):        # the test must actually catch the bug
            continue
        stream.append({"shape": shape, "code": code, "test": test})
    rng.shuffle(stream)
    print(f"{len(stream)} distinct bugs over {len(SHAPES)} shapes, each with a test that catches it", flush=True)

    file_table, line_table = {}, {}
    rows, t0 = [], time.time()
    checkpoints = list(range(0, len(stream) + 1, max(1, len(stream) // 10)))
    holdout = 24                                  # the next unseen bugs each arm is scored on

    for i, item in enumerate(stream):
        if i in checkpoints and i + holdout <= len(stream):
            nxt = stream[i:i + holdout]
            hit_file = sum(1 for n in nxt if hashlib.md5(n["code"].encode()).hexdigest() in file_table)
            hit_line = 0
            for n in nxt:
                fix = line_table.get(broken_line(n["code"]).strip())
                if fix is None:
                    continue
                cand = n["code"].replace(broken_line(n["code"]).strip(), fix, 1)
                if run_test(cand, n["test"]):
                    hit_line += 1
            per_shape, hit_shape = {}, 0
            for n in nxt:
                ok = bool(shapes_repair(n["code"], n["test"], DICT))
                hit_shape += ok
                got, tot = per_shape.get(n["shape"], (0, 0))
                per_shape[n["shape"]] = (got + ok, tot + 1)
            rows.append({"seen": i, "file_rows": len(file_table), "line_rows": len(line_table),
                         "shape_rows": len(SHAPES),
                         "file_hit": hit_file / len(nxt), "line_hit": hit_line / len(nxt),
                         "shape_hit": hit_shape / len(nxt),
                         "per_shape": {k: list(v) for k, v in sorted(per_shape.items())}})
            print(f"  after {i:>3} bugs: table-of-programs {hit_file}/{len(nxt)} "
                  f"({len(file_table)} rows) · table-of-lines {hit_line}/{len(nxt)} ({len(line_table)} rows) "
                  f"· shapes {hit_shape}/{len(nxt)} ({len(SHAPES)} rules)", flush=True)
        got = shapes_repair(item["code"], item["test"], DICT)
        if got:                                    # whatever is repaired is what a table would remember
            file_table[hashlib.md5(item["code"].encode()).hexdigest()] = got["code"]
            line_table[got["before"]] = got["after"]

    out = {"bugs": len(stream), "shapes": len(SHAPES), "holdout": holdout, "seconds": round(time.time() - t0, 1),
           "final_file_rows": len(file_table), "final_line_rows": len(line_table), "rules": len(SHAPES),
           "points": rows}
    (HERE / "lookup_vs_shapes.json").write_text(json.dumps(out, indent=1))
    last = rows[-1]
    print(f"\nafter {last['seen']} bugs: a table of programs holds {last['file_rows']} rows and repairs "
          f"{last['file_hit']:.0%} of the next ones; a table of lines holds {last['line_rows']} rows and "
          f"repairs {last['line_hit']:.0%}; {len(SHAPES)} shapes repair {last['shape_hit']:.0%}.")
    print(f"LOOKUP_DONE in {out['seconds']}s")


if __name__ == "__main__":
    main()
