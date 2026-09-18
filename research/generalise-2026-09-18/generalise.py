#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Does knowledge GENERALISE, and does the free share rise as it accumulates? Both, measured.

The claim under test is the one that decides whether this replaces an agent or merely assists one:

    as the vocabulary grows, the fraction of incidents handled with no model call rises, and what is left
    for a model is only the genuinely open-ended minority.

That claim has a load-bearing half and a decorative one. The decorative half is "it gets better with use",
which any cache can say. The load-bearing half is **generalisation**: a taught shape must repair instances
it was never shown -- different names, different values, different surrounding code -- or the vocabulary is
a lookup table with extra steps and the curve flattens the moment the exact lines stop recurring.

So every instance in the stream is DISTINCT: its own function name, its own variables, its own literals, its
own shell. Nothing a shape repairs here was ever shown to it. Two arms face the same stream:

    LINE TABLE   remembers the exact broken line -> the exact fixed line. Grows one row per repair.
    SHAPES       a fixed handful of taught classes, judged by each instance's own test.

and the curve is drawn over K, the number of TAUGHT classes loaded: K=0 is the shipped vocabulary alone,
K=4 is every dictionary slot filled. Two of those four were written from the edit-budget ladder's own
output this afternoon (../kindof-2026-09-18), so this also measures whether shapes learned from real
model-written faults carry to code nobody has seen.

  PYTHONPATH=<fluidfix>/src python3 generalise.py --taught K [--per-shape 30]
"""
from __future__ import annotations

import argparse, hashlib, json, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "life-fluidfix-2026-09-18"))
from life_fluidfix import run_test, shapes_repair                          # noqa: E402

NAMES = ["total","count","items","rows","values","scores","budget","limit","width","depth","size",
         "offset","cursor","weight","height","span","window","batch","chunk","stride","bucket","tally"]
FUNCS = ["compute","measure","tally","resize","collect","bound","advance","shrink","expand","fit","pack",
         "trim","scale","align","settle","balance","reduce","sample","gather","render"]
METHODS = ["append", "insert", "add", "update", "extend"]
WORDS = ["alpha","bravo","delta","echo","foxtrot","golf","hotel","india","juliet","kilo"]


def gen(shape, rng):
    """One DISTINCT instance of a shape, with a test that catches it. Never a line any example contained."""
    f = rng.choice(FUNCS) + str(rng.randint(10, 99))
    a, b = rng.sample(NAMES, 2)

    # ---- shipped classes
    if shape == "strictness":
        lim = rng.randint(2, 40)
        return (f"def {f}({a}, {b}):\n    if {a} > {b}:\n        return 'over'\n    return 'ok'\n",
                f"assert {f}({lim}, {lim}) == 'over' and {f}({lim-1}, {lim}) == 'ok'")
    if shape == "additive":
        x, y, z = rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 9)
        return (f"def {f}({a}, {b}, c):\n    return {a} * {b} - c\n", f"assert {f}({x}, {y}, {z}) == {x*y+z}")
    if shape == "literal":
        n = rng.randint(2, 6)
        return (f"def {f}(xs):\n    return xs[{n+1}:]\n",
                f"assert {f}(list(range(10))) == list(range({n}, 10))")
    if shape == "augmented":
        vals = [rng.randint(1, 9) for _ in range(3)]
        return (f"def {f}(xs):\n    {a} = 0\n    for v in xs:\n        {a} -= v\n    return {a}\n",
                f"assert {f}({vals}) == {sum(vals)}")
    # ---- taught slots 6 and 7 (examples/taught-2026-09-16)
    if shape == "lenm1":
        n = rng.randint(2, 7)
        return (f"def {f}({a}):\n    return len({a})\n", f"assert {f}({list(range(n))}) == {n-1}")
    if shape == "ifnot":
        return (f"def {f}({a}):\n    if {a}:\n        return None\n    return {a}[0]\n",
                f"assert {f}([]) is None and {f}([7]) == 7")
    # ---- taught slots 4 and 5, written from the ladder's own output (../kindof-2026-09-18)
    if shape == "separator":
        k = rng.randint(1, 3)
        tok = rng.choice(["...", ">>", "--", "etc"])
        ws = rng.sample(WORDS, k + 2)
        kept = " ".join(ws[:k])
        return (f"def {f}(text, limit):\n"
                f"    parts = text.split()\n"
                f"    if len(parts) <= limit:\n"
                f"        return text\n"
                f"    return ' '.join(parts[:limit]) + '{tok}'\n",
                f"assert {f}({' '.join(ws)!r}, {k}) == {kept + ' ' + tok!r}")
    if shape == "mutating":
        meth = rng.choice(METHODS)
        v = rng.randint(1, 9)
        if meth in ("append", "add"):
            call, start, want = f"{a}.append({b})", [rng.randint(1, 9)], None
            want = start + [v]
        elif meth == "extend":
            call, start = f"{a}.extend([{b}])", [rng.randint(1, 9)]
            want = start + [v]
        elif meth == "insert":
            call, start = f"{a}.insert(0, {b})", [rng.randint(1, 9)]
            want = [v] + start
        else:
            call, start = f"{a}.append({b})", [rng.randint(1, 9)]
            want = start + [v]
        return (f"def {f}({a}, {b}):\n    {call}\n", f"assert {f}({start}, {v}) == {want}")
    raise ValueError(shape)


SHIPPED_SHAPES = ["strictness", "additive", "literal", "augmented"]
TAUGHT_ORDER = ["mutating", "separator", "ifnot", "lenm1"]     # slots 4, 5, 6, 7 in that order


def broken_line(code):
    for l in code.split("\n"):
        s = l.strip()
        if s and not s.startswith("def ") and not s.startswith("for ") and s != "return None":
            if any(t in s for t in (" > ", " - ", "[", " -= ", "len(", "if ", ".", "+")):
                return l
    return code.split("\n")[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taught", type=int, required=True, help="how many taught classes are loaded (0-4)")
    ap.add_argument("--per-shape", type=int, default=30); ap.add_argument("--seed", type=int, default=20260918)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    shapes = SHIPPED_SHAPES + TAUGHT_ORDER          # the stream always contains all eight
    dict_path = HERE / f"dict_{a.taught}.py"

    stream, seen = [], set()
    while len(stream) < a.per_shape * len(shapes):
        sh = shapes[len(stream) % len(shapes)]
        code, test = gen(sh, rng)
        key = hashlib.md5(code.encode()).hexdigest()
        if key in seen or run_test(code, test):     # distinct, and the test must catch the bug
            continue
        seen.add(key)
        stream.append({"shape": sh, "code": code, "test": test})
    rng.shuffle(stream)

    line_table, rows, t0 = {}, [], time.time()
    hold = 32
    free = table_hits = 0
    per_shape = {}
    for i, item in enumerate(stream):
        got = shapes_repair(item["code"], item["test"], str(dict_path) if a.taught else None)
        free += bool(got)
        g, t = per_shape.get(item["shape"], (0, 0))
        per_shape[item["shape"]] = (g + bool(got), t + 1)
        # the table arm: it may only replay a line it has literally stored
        bl = broken_line(item["code"]).strip()
        fix = line_table.get(bl)
        if fix is not None and run_test(item["code"].replace(bl, fix, 1), item["test"]):
            table_hits += 1
        if got:
            line_table[got["before"]] = got["after"]
    out = {"taught": a.taught, "bugs": len(stream), "free": free, "table": table_hits,
           "table_rows": len(line_table), "per_shape": {k: list(v) for k, v in sorted(per_shape.items())},
           "seconds": round(time.time() - t0, 1)}
    (HERE / f"generalise_{a.taught}.json").write_text(json.dumps(out, indent=1))
    print(f"taught={a.taught}  free {free}/{len(stream)} ({free/len(stream):.0%})  "
          f"line-table {table_hits}/{len(stream)} ({table_hits/len(stream):.0%}, {len(line_table)} rows)  "
          f"{out['seconds']}s")
    for k, (g, t) in sorted(per_shape.items()):
        print(f"    {k:11} {g:>3}/{t:<3} {'free' if g else '-- every one needs a model'}")


if __name__ == "__main__":
    main()
