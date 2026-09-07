#!/usr/bin/env python
"""Every observation byte the BODY can construct today, from its seven
situation() call sites (read from src, not executed), and whether OR-ing
SELF into each would change the ruling.

Call sites (grep -n "situation(" src/fluidfix/*.py, 2026-09-07):
  loop.py:217   situation(BUILT=True, AMB=<bool>, CAPPED=<bool>)
  loop.py:391   situation(HIDDEN=True)
  guard.py:491  situation(UNREAD=True)
  guard.py:539  situation(CAPPED=<bool>, REFUTED=<bool>)
  guard.py:612  situation(REFUTED=True)
  guard.py:618  situation(REFUTED=True)
  cli.py:474    situation(<one bit>) for BUILT/AMB/UNREAD/CAPPED/REFUTED
Rerun: .venv/bin/python constructible_bytes.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS

sites = {
    "loop.py:217": [dict(BUILT=True, AMB=a, CAPPED=c) for a in (0, 1) for c in (0, 1)],
    "loop.py:391": [dict(HIDDEN=True)],
    "guard.py:491": [dict(UNREAD=True)],
    "guard.py:539": [dict(CAPPED=c, REFUTED=r) for c in (0, 1) for r in (0, 1)],
    "guard.py:612/618": [dict(REFUTED=True)],
    "cli.py:474": [dict(**{b: True}) for b in ("BUILT", "AMB", "UNREAD", "CAPPED", "REFUTED")],
}
def name(byte):
    return "+".join(b for i, b in enumerate(BITS) if byte >> i & 1) or "(none)"

seen = {}
for site, obs_list in sites.items():
    for obs in obs_list:
        byte = situation(**obs) & 0xFF
        seen.setdefault(byte, set()).add(site)

print(f"{'byte':>4}  {'bits':<22} {'ruling':<24} {'ruling with SELF':<24} sites")
changed = 0
for byte in sorted(seen):
    r0 = decide(situation(**{b: bool(byte >> i & 1) for i, b in enumerate(BITS)}))
    r1 = decide(situation(**{b: bool((byte | 128) >> i & 1) for i, b in enumerate(BITS)}))
    changed += r0 != r1
    print(f"{byte:>4}  {name(byte):<22} {r0:<24} {r1:<24} {', '.join(sorted(seen[byte]))}"
          f"{'   <-- CHANGES' if r0 != r1 else ''}")
print()
print(f"constructible bytes today: {len(seen)}; rulings SELF would change: {changed}")
print("bytes on which SELF is live (from algebra_check): 7 (BUILT+AMB+UNREAD) and 8 (NOTWIN)")
print(f"  byte 7 constructible today: {7 in seen}   byte 8 constructible today: {8 in seen}")
