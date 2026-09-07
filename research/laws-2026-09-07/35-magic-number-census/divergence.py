#!/usr/bin/env python
"""Outcome-divergence probes for the constants whose STATED intent and
MEASURED behaviour differ.  Pure simulation of the arithmetic in the body;
no repo is touched, no suite is run.
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.sight import observe_bits as sb, sight            # noqa: E402
from fluidfix.rank import observe_bits as rb, rank              # noqa: E402

print("=" * 72)
print("D1  guard.py:591-592 -- is 'one file gets at most half the escalation")
print("    budget' true?  Replay the exact expression at 591-597.")
print("=" * 72)
ESC = 600.0                       # guard_once default escalate_budget
print("  no --budget  (total_deadline is None; file_share = escalate_budget/2)")
print(f"  {'t (s into escalation)':<24}{'clock left':>11}"
      f"{'file_share':>12}{'ACTUAL slice = min(deadline, now+share)':>42}")
for t in (0, 100, 299, 300, 301, 450, 599):
    left = ESC - t
    share = ESC / 2
    actual = min(left, share)
    half = left / 2
    flag = "" if abs(actual - half) < 1e-9 else "   <- NOT half of what is left"
    print(f"  {t:<24}{left:>11.0f}{share:>12.0f}{actual:>42.0f}{flag}")
print("  with --budget (total_deadline set; file_share = (deadline-now)/2)")
for t in (0, 300, 450, 599):
    left = ESC - t
    share = left / 2
    print(f"  {t:<24}{left:>11.0f}{share:>12.0f}{min(left, share):>42.0f}")
print("  => the starvation cap is EXACTLY half only while >= escalate_budget/2")
print("     of the clock remains.  After the halfway point the *next* file")
print("     takes the entire remainder, which is the starvation the comment")
print("     at 588-590 says it prevents.  --budget mode does not have this.")

print()
print("=" * 72)
print("D2  SIGHT circumstantial thresholds -- guard.py:284, 287, 288.")
print("    Which of them can change the law's ruling, and by how much?")
print("=" * 72)
print(f"  {'situation':<46}{'byte':>6}{'sight()':>9}")
rows = [
    ("nothing set (specificity 0.5, 300 lines)", dict()),
    ("FAILONLY only (specificity >= 0.9)", dict(failonly=True)),
    ("SMALL only (0 < n_fail < 80)", dict(small=True)),
    ("NAMED only", dict(named=True)),
    ("TOUCHED only (last 40 commits)", dict(touched=True)),
    ("UBIQUITOUS only (specificity < 0.25)", dict(ubiquitous=True)),
    ("FAILONLY+NAMED+TOUCHED+SMALL", dict(failonly=True, named=True,
                                          touched=True, small=True)),
    ("all circumstantial + UBIQUITOUS", dict(failonly=True, named=True,
                                             touched=True, small=True,
                                             ubiquitous=True)),
    ("FRAMED only (POINTING)", dict(framed=True)),
    ("FRAMED + UBIQUITOUS", dict(framed=True, ubiquitous=True)),
]
for label, kw in rows:
    b = sb(**kw)
    print(f"  {label:<46}{b:>6}{sight(b):>9}")
print("  => every circumstantial threshold moves a file by at most one")
print("     priority class, and none of them can beat a POINTING bit (R1).")
print("     The 0.9 / 0.25 / 80 numbers therefore reorder files only WITHIN")
print("     the circumstantial tier -- but that tier is the whole search")
print("     order whenever no POINTING lane fired (guard.py:82-91's third")
print("     refusal cause).")

print()
print("=" * 72)
print("D3  RANK thresholds -- guard.py:403 (CHEAP < 8) and :412 (DENSE >= 8).")
print("    rank.py:19 SPECIFIES '< 8' for CHEAP; rank.py:20 specifies NO")
print("    number for DENSE.  Do they change the ruling?")
print("=" * 72)
for label, kw in [("nothing", {}),
                  ("CHEAP only", dict(cheap=True)),
                  ("DENSE only", dict(dense=True)),
                  ("SIGNALED", dict(signaled=True)),
                  ("SIGNALED+CHEAP", dict(signaled=True, cheap=True)),
                  ("SIGNALED+DENSE", dict(signaled=True, dense=True)),
                  ("FRAME+DENSE", dict(frame=True, dense=True)),
                  ("FRAME+RETRIED (veto)", dict(frame=True, retried=True))]:
    b = rb(**kw)
    print(f"  {label:<28}byte={b:>4}  rank()={rank(b)}")
print("  => DENSE alone never changes a rank in these situations, but it is")
print("     an input the law reads; its threshold (>= 8) exists ONLY in")
print("     guard.py:412 and is pinned by no spec line and no test.")
print("  => the '[:2]' at guard.py:402 is a THIRD hidden constant: CHEAP is")
print("     computed from the first two kinds only, so a line whose third")
print("     kind explodes the candidate set still measures as CHEAP.")
