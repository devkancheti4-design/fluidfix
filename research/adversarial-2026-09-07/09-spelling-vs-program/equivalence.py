"""Ground truth for the 2x2: are the two GREENS one program or two?

Reads each fixture's fluidfix JSON result, rebuilds a module per green line,
and differential-tests the function on inputs the suite never used.  This is
the observation fluidfix does NOT make -- and it needs zero suite runs.

    /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python equivalence.py
"""
import itertools
import json
import os
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))

FIX = {
    "A1-same-set-one-program":  ("frame_bytes", 1),
    "A2-cross-set-one-program": ("should_ship", 1),
    "B1-same-set-two-programs": ("balance",     3),
    "B2-cross-set-two-programs": ("total_due",  2),
}
DOMAIN = [-97, -3, -1, 0, 1, 2, 3, 7, 9, 10, 11, 50, 1000, 2**40]
WIDE = list(range(-500, 501)) + [10**9, -10**9, 2**63, -(2**63)]


def load(fixture, green_line):
    src = open(os.path.join(HERE, "fixtures", fixture, "mod.py")).read()
    lines = src.split("\n")
    lines[5] = green_line                        # mod.py:6 in every fixture
    mod = types.ModuleType("v")
    exec(compile("\n".join(lines), "<green>", "exec"), mod.__dict__)
    return mod


def main():
    for fixture, (fn, arity) in FIX.items():
        res = json.load(open(os.path.join(HERE, "logs", fixture + ".json")))
        greens = res["greens"]
        print(f"\n=== {fixture}")
        for g in greens:
            print(f"    green: {g.strip()}")
        if len(greens) != 2:
            print("    (expected exactly two greens)")
            continue
        a, b = (getattr(load(fixture, g), fn) for g in greens)
        n, bad = 0, None
        t0 = time.time()
        space = (((v,) for v in WIDE) if arity == 1
                 else itertools.product(DOMAIN, repeat=arity))
        for args in space:
            n += 1
            if a(*args) != b(*args):
                bad = (args, a(*args), b(*args))
                break
        if bad:
            args, va, vb = bad
            print(f"    VERDICT: TWO PROGRAMS  -- {fn}{args} = {va!r} vs {vb!r}")
        else:
            print(f"    VERDICT: ONE PROGRAM   -- identical on all {n} inputs")
        print(f"    probe cost: {time.time() - t0:.4f}s, {n} evaluations, 0 suite runs")
        print(f"    fluidfix said: "
              f"{'REPAIRED (shipped greens[0])' if res['repaired'] else 'REFUSED as AMBIGUOUS'}")


if __name__ == "__main__":
    main()
