#!/usr/bin/env python
"""Finding 5: the byte guard.py:539 builds when repair() already ruled
BUILT+CAPPED -> RAISE_BUDGET, vs the byte the situation actually is.

engine.py:24-25 defines REFUTED as "candidates were generated AND the suite
rejected every one". guard.py:519 sets it from `bool(result.acts_tried)`,
which measures only the first half. When a green exists, REFUTED is false by
the law's own definition -- and the search was cut short, so CAPPED is true.

Run: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python defect_byte.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation  # noqa: E402

print("scenario: repair() returned repaired=False ambiguous=False")
print("          greens=['K = 1'] acts_tried=[6, 9, 10]")
print("          reason='... (engine law: BUILT+CAPPED -> RAISE_BUDGET)'")
print()
print("what repair() itself ruled, at loop.py:217:")
r_loop = decide(situation(BUILT=True, AMB=False, CAPPED=True))
print(f"  situation(BUILT=1, AMB=0, CAPPED=1) -> {r_loop}")
print()
print("what guard.py:539 builds from that same result:")
print("  capped0 = packet.truncated or len(all_files)>len(candidates)  -> False")
print("            (guard.py:508,538 -- the WALL-CLOCK cap repair() measured")
print("             is never folded in; guard.py never reads result.greens)")
print("  acts0   = bool(result.acts_tried)                             -> True")
as_measured = decide(situation(CAPPED=False, REFUTED=True))
print(f"  situation(CAPPED=0, REFUTED=1) -> {as_measured}   "
      f"=> escalation gate FALSE, pass stops")
print()
print("what the situation actually is, by the law's own definitions:")
print("  CAPPED  = True   (engine.py:22-23 'a budget truncated the search' --")
print("                    repair() hit first_deadline mid-search)")
print("  REFUTED = False  (engine.py:24-25 'the suite rejected EVERY one' --")
print("                    one candidate passed: greens=['K = 1'])")
as_true = decide(situation(CAPPED=True, REFUTED=False))
print(f"  situation(CAPPED=1, REFUTED=0) -> {as_true}   "
      f"=> escalation gate TRUE, pass retries")
print()
print(f"same law, two bytes: {as_measured} vs {as_true}")
print("the ruling was never wrong. The byte was.")
print()
print("consequence chain, all three measured in probe_builtcapped.out:")
print("  1. the green ('K = 1', the real fix) is dropped, never shipped")
print("  2. the RAISE_BUDGET ruling repair() made is discarded by guard_once")
print("     (guard.py:520-529 has branches for .repaired and .ambiguous only)")
print("  3. guard.py:617-621 then writes a hint that is FALSE:")
print("     'every generated candidate was rejected by the suite'")
print("     -- one was not. It passed.")
