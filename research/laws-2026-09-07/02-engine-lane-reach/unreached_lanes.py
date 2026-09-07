#!/usr/bin/env python
"""What, exactly, would make each unreached engine-law lane reachable?

The body constructs 9 of 256 situations (enumerate_reach.py). This script
asks the complementary question for the two acts the body can never obtain
-- RESHAPE and AUTHOR_SUCCESSOR -- and for the two bits it never sets,
NOTWIN and SELF:

  * Is RESHAPE obtainable without NOTWIN?  Is AUTHOR_SUCCESSOR obtainable
    without SELF?  (If not, the missing OBSERVATION is the whole blocker,
    and no new actuation or if-statement is needed to reach the lane.)
  * How much of the law's ruling surface does each unset bit gate?
  * Given the 9 situations the body DOES construct, which new situations
    would appear if one bit became measurable -- i.e. the marginal value of
    each observation, counted in situations and in newly-available acts.

Pure arithmetic over all 256 inputs. Run:
    ./run.sh 300 <venv>/bin/python unreached_lanes.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide  # noqa: E402

JOB = 2 << 8            # fluidfix always runs as the DEBUG job


def rule(x):
    return decide(x | JOB)


def bits(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "<empty>"


BIT = {b: 1 << i for i, b in enumerate(BITS)}

# what the body constructs today, from enumerate_reach.py (static) and
# confirmed dynamically by reach_dynamic.py / reach_unread.py
REACHABLE = [0, 1, 3, 4, 16, 32, 33, 64, 96]

print("=== 1. is either unreached act obtainable WITHOUT the unset bit? ===")
for act, need in (("RESHAPE", "NOTWIN"), ("AUTHOR_SUCCESSOR", "SELF")):
    xs = [x for x in range(256) if rule(x) == act]
    without = [x for x in xs if not (x & BIT[need])]
    print(f"  {act:18} rules {len(xs):3d}/256; of those, {len(without)} have "
          f"{need} CLEAR -> {'obtainable without it' if without else 'REQUIRES ' + need}")
    if without:
        print(f"      e.g. {[(x, bits(x)) for x in without[:6]]}")

print("\n=== 2. ruling surface each never-set bit gates ===")
for b in ("NOTWIN", "SELF"):
    m = BIT[b]
    base = [x for x in range(256) if not (x & m)]
    flips = [x for x in base if rule(x) != rule(x | m)]
    acts_only_with = sorted({rule(x | m) for x in base} - {rule(x) for x in base})
    print(f"  {b:7} flips the ruling on {len(flips):3d} of 128 base situations; "
          f"acts reachable ONLY once {b} can be set: {acts_only_with or 'none'}")
    if len(flips) <= 8:
        for x in flips:
            print(f"      x={x:3d} {bits(x):24} {rule(x):22} -> with {b}: {rule(x | m)}")

print("\n=== 3. marginal value of making one bit measurable, from today's 9 ===")
print("  (new situations = today's 9 with the bit added, minus the 9)")
today_acts = {rule(x) for x in REACHABLE}
print(f"  today: {len(REACHABLE)} situations -> acts {sorted(today_acts)}")
for b in BITS:
    m = BIT[b]
    grown = sorted(set(REACHABLE) | {x | m for x in REACHABLE})
    new_x = [x for x in grown if x not in REACHABLE]
    new_acts = sorted({rule(x) for x in grown} - today_acts)
    print(f"  +{b:8} -> +{len(new_x):2d} situations, new acts: {new_acts or 'none'}")

print("\n=== 4. the 9 reachable situations, ruled ===")
for x in REACHABLE:
    print(f"  x={x:3d} {bits(x):24} -> {rule(x)}")

print("\n=== 5. coverage of the law's ruling surface ===")
per_act = {a: [x for x in range(256) if rule(x) == a] for a in ACTS}
tot_reached = 0
for a in ACTS:
    r = sorted(set(per_act[a]) & set(REACHABLE))
    tot_reached += len(r)
    print(f"  {a:22} {len(r):2d}/{len(per_act[a]):3d} situations reachable")
print(f"  TOTAL                  {tot_reached}/256 situations reachable "
      f"({tot_reached / 256 * 100:.1f}%); "
      f"{len(today_acts)}/8 acts obtainable")
