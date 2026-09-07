#!/usr/bin/env python
"""47-reshape-actuation, part 2: is `restored_original` a sound NOTWIN?

Runs the REAL src/fluidfix/loop.py repair() on five git scenarios and records
what restored_original says, what the shipped program actually is (judged by a
pin the oracle never saw), and what the engine law would rule if NOTWIN were
read as `restored_original is False`.

Nothing in src/ is edited. Fixtures live under ./work/.
Run:  .venv/bin/python notwin_probe.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fixtures                                            # noqa: E402
from fluidfix import repair                                # noqa: E402
from fluidfix.engine import decide, situation              # noqa: E402

rows = []
for name in fixtures.SCENARIOS:
    root, oracle, obs, pin, blurb = fixtures.build(name)
    res = repair(oracle, "mod.py", obs)
    ro = res.restored_original
    correct = fixtures.pin_ok(root, pin) if res.repaired else "n/a (refused)"
    # THE PROPOSED READING: NOTWIN <=> the shipped repair differs from HEAD.
    notwin = (ro is False)
    now = decide(situation(BUILT=res.repaired, AMB=res.ambiguous))
    prop = decide(situation(BUILT=res.repaired, AMB=res.ambiguous,
                            NOTWIN=notwin))
    print("=" * 74)
    print(f"{name}   -- {blurb}")
    print("=" * 74)
    print(f"  HEAD line 2                : {fixtures.head_line(root, 2)!r}")
    print(f"  repaired                   : {res.repaired}   "
          f"suite_runs={res.suite_runs}  {res.seconds:.1f}s")
    print(f"  shipped line               : {(res.new_line or '').strip()!r}")
    print(f"  all greens found           : {[g.strip() for g in res.greens]}")
    print(f"  ambiguous (body's AMB)     : {res.ambiguous}")
    print(f"  restored_original          : {ro}")
    print(f"  pin says the program is    : "
          f"{'CORRECT' if correct is True else correct}")
    print(f"  law today   BUILT={int(res.repaired)} AMB={int(res.ambiguous)}"
          f"              -> {now}")
    print(f"  law proposed  + NOTWIN={int(notwin)}"
          f"                      -> {prop}")
    verdict = ("agrees" if (prop == "SHIP") == (correct is True)
               else "DISAGREES with the pin")
    print(f"  proposed reading vs the pin : {verdict}")
    print()
    rows.append((name, ro, correct, now, prop, verdict))

print("=" * 74)
print("SUMMARY")
print("=" * 74)
print(f"{'scenario':26} {'rest_orig':10} {'program':9} {'today':13} "
      f"{'proposed':10} {'verdict'}")
for name, ro, correct, now, prop, verdict in rows:
    c = "CORRECT" if correct is True else ("WRONG" if correct is False
                                           else str(correct))
    print(f"{name:26} {str(ro):10} {c:9} {now:13} {prop:10} {verdict}")

good_now = sum(1 for _, _, c, now, _, _ in rows if (now == "SHIP") == (c is True))
good_prop = sum(1 for _, _, c, _, p, _ in rows if (p == "SHIP") == (c is True))
print()
print(f"scenarios where TODAY's ruling matches the pin    : {good_now}/{len(rows)}")
print(f"scenarios where the PROPOSED ruling matches the pin: {good_prop}/{len(rows)}")
