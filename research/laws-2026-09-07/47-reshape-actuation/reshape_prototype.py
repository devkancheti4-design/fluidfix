#!/usr/bin/env python
"""47-reshape-actuation, part 3: an actuated RESHAPE, prototyped.

RESHAPE has no definition in the engine docstring. The law's own same-index
pairing makes it NOTWIN's act, and the sense the vocabulary carries is
"the material is right, the SHAPE is not — re-form it, do not spend more
budget and do not change granularity".

So the actuation prototyped here is:

    when the law rules RESHAPE, do NOT ship greens[0]; re-form at the SAME
    SITE — ship instead the already-green candidate whose shape matches the
    wanted shape. If no green has the wanted shape, refuse and say so.

The only "wanted shape" fluidfix can read today is git HEAD's line, which is
also the only NOTWIN datum available (RepairResult.restored_original).
Everything this prototype can do, it does with candidates the search ALREADY
proved green, so it costs one confirming suite run and no new search.

Nothing in src/ is edited. Run:  .venv/bin/python reshape_prototype.py
"""
import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fixtures                                            # noqa: E402
from fluidfix import repair                                # noqa: E402
from fluidfix.engine import decide, situation              # noqa: E402


def read_line(root, lineno):
    return open(os.path.join(root, "mod.py")).read().split("\n")[lineno - 1]


def write_line(root, lineno, text):
    p = os.path.join(root, "mod.py")
    lines = open(p, encoding="utf-8", newline="").read().split("\n")
    lines[lineno - 1] = text
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))


rows = []
for name in fixtures.SCENARIOS:
    root, oracle, obs, pin, blurb = fixtures.build(name)
    res = repair(oracle, "mod.py", obs)
    base_runs = res.suite_runs
    base_correct = fixtures.pin_ok(root, pin) if res.repaired else None
    base_line = res.new_line

    # ---- the observation, then the law, then the actuation. In that order.
    notwin = (res.restored_original is False)
    ruling = decide(situation(BUILT=res.repaired, AMB=res.ambiguous,
                              NOTWIN=notwin))

    extra_runs = 0
    if ruling == "RESHAPE":
        want = fixtures.head_line(root, res.lineno)
        match = [g for g in res.greens if g == want]
        if match:
            write_line(root, res.lineno, match[0])
            ok, why = oracle.check()
            extra_runs = 1
            outcome = "RESHAPED+SHIP" if ok else "RESHAPE re-check RED"
            new_line = match[0]
        else:
            # re-form impossible: no green has the wanted shape. Refuse and
            # put the tree back exactly as the search found it.
            write_line(root, res.lineno,
                       fixtures.SCENARIOS[name][1].split("\n")[res.lineno - 1])
            outcome = "REFUSED (no green has the wanted shape)"
            new_line = None
    else:
        outcome = ruling
        new_line = base_line

    proto_correct = (fixtures.pin_ok(root, pin)
                     if outcome in ("SHIP", "RESHAPED+SHIP") else None)

    print("=" * 74)
    print(f"{name}   -- {blurb}")
    print("=" * 74)
    print(f"  greens the search proved   : {[g.strip() for g in res.greens]}")
    print(f"  wanted shape (HEAD line)   : "
          f"{(fixtures.head_line(root, res.lineno) or 'unavailable').strip()!r}")
    print(f"  BASELINE (fluidfix today)  : ship {(base_line or '').strip()!r}"
          f"  -> {'CORRECT' if base_correct is True else base_correct}"
          f"  ({base_runs} suite runs)")
    print(f"  ruling with NOTWIN={int(notwin)}       : {ruling}")
    print(f"  PROTOTYPE                  : {outcome}"
          + (f" {(new_line or '').strip()!r}" if new_line else ""))
    print(f"  prototype program          : "
          f"{'CORRECT' if proto_correct is True else proto_correct}"
          f"  ({base_runs + extra_runs} suite runs)")
    delta = ("RESCUED a wrong repair" if base_correct is False
             and proto_correct is True else
             "DESTROYED a correct repair" if base_correct is True
             and proto_correct is not True else
             "no change")
    print(f"  net effect                 : {delta}")
    print()
    rows.append((name, base_correct, proto_correct, base_runs,
                 base_runs + extra_runs, delta))

print("=" * 74)
print("SUMMARY — 5 scenarios")
print("=" * 74)
print(f"{'scenario':26} {'baseline':10} {'prototype':10} {'runs':9} {'net'}")
for n, b, p, br, pr, d in rows:
    f = lambda v: "CORRECT" if v is True else ("WRONG" if v is False else "refused")
    print(f"{n:26} {f(b):10} {f(p):10} {br}->{pr:<6} {d}")
ok_b = sum(1 for _, b, _, _, _, _ in rows if b is True)
ok_p = sum(1 for _, _, p, _, _, _ in rows if p is True)
print()
print(f"correct programs on disk, fluidfix today : {ok_b}/5")
print(f"correct programs on disk, with RESHAPE   : {ok_p}/5")
print(f"total suite runs today / with RESHAPE    : "
      f"{sum(r[3] for r in rows)} / {sum(r[4] for r in rows)}")
