#!/usr/bin/env python
"""The RANKING LAW's side of the recurrence question.

rank.py orders LINES, not classes. The only lane that reads the class at all
is SIGNALED (bit 3), and guard.py:409 sets it as `signaled=bool(obs.kinds)` —
a boolean on non-emptiness. So:

  1. two candidate lines whose evidence differs ONLY in WHICH class matched
     pack to the SAME byte, and the law necessarily gives them the same rank;
  2. the law's input byte is FULL — all 8 lanes are named in rank.BITS, with
     bit 7 the RETRIED veto — so a RECURRENT lane is not a spare bit, it is a
     ninth lane, i.e. a re-authored law;
  3. FAILONLY (bit 1) is documented unmeasured (guard.py:352-354), so the
     body reaches only half the law's 256 situations today. Measure that.

No suite runs; pure enumeration. Usage: .venv/bin/python rank_side.py
"""
import collections
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.rank import BITS, rank, situation                    # noqa: E402
from fluidfix.acts import KINDS                                    # noqa: E402

print("rank.BITS =", BITS, f"({len(BITS)} lanes, byte is full)")

# --- 1. no lane distinguishes one class from another --------------------
print("\n[1] guard.py:409 packs the class as `signaled=bool(obs.kinds)`.")
same = collections.defaultdict(set)
for kinds in ([0], [1], [3], [10], [0, 10], [1, 3, 11], list(KINDS)):
    b = situation(SIGNALED=bool(kinds), FRAME=True, NAMED=True)
    same[b].add(tuple(kinds))
for b, ks in same.items():
    print(f"    byte={b:3} (0b{b:08b}) rank={rank(b)}  <- kind sets "
          f"{sorted(ks, key=len)}")
print(f"    distinct bytes over those {sum(len(v) for v in same.values())} "
      f"kind sets: {len(same)}  ->  class identity is not representable")

# --- 2. what a RECURRENT lane would cost -------------------------------
print("\n[2] every one of the 8 lanes is already assigned:")
for i, n in enumerate(BITS):
    print(f"    bit {i}  {n}" + ("   <- VETO" if n == "RETRIED" else ""))
print("    a RECURRENT lane is a 9th bit: rank.c would have to be re-authored,")
print("    not edited. (rank() is verified over exactly 256 inputs by")
print("    cli.py:492-495 and tests/test_rank_law.py.)")

# --- 3. how much of the law the body reaches ---------------------------
reach = [x for x in range(256) if not ((x >> 1) & 1)]   # FAILONLY never set
print(f"\n[3] FAILONLY (bit 1) is never set by guard.rank_observations, so the")
print(f"    body can construct {len(reach)} of 256 situations.")
d_all = collections.Counter(rank(x) for x in range(256))
d_rch = collections.Counter(rank(x) for x in reach)
print(f"    rank distribution, all 256      : "
      f"{dict(sorted(d_all.items()))}")
print(f"    rank distribution, reachable 128: "
      f"{dict(sorted(d_rch.items()))}")
lost = sorted({rank(x) for x in range(256)} - {rank(x) for x in reach})
print(f"    priorities unreachable with FAILONLY==0: {lost or 'none'}")

# --- 4. ties the body can actually produce ------------------------------
# The body sets FRAME, NAMED, SIGNALED, RECENT, CHEAP, DENSE, RETRIED.
# How many reachable bytes share each priority? A tie is where a recurrence
# signal COULD discriminate, if it were a lane.
by_rank = collections.defaultdict(list)
for x in reach:
    by_rank[rank(x)].append(x)
print("\n[4] reachable bytes per priority (a tie is a place a 9th lane could")
print("    discriminate; today guard.py:422-427 breaks ties on shared name")
print("    tokens, then on original index):")
for p in sorted(by_rank):
    print(f"    priority {p}: {len(by_rank[p]):3} bytes")
