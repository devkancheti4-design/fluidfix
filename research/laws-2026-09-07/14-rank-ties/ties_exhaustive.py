"""Exhaustive tie analysis of the ranking law (src/fluidfix/rank.py).

Pure law, no suite runs. Run:
  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python ties_exhaustive.py
"""
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.rank import BITS, rank  # noqa: E402

FRAME, FAILONLY, NAMED, SIGNALED, RECENT, CHEAP, DENSE, RETRIED = (1 << i for i in range(8))


def names(x):
    return "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "(none)"


print("== 1. all 256 bytes: size of each priority (tie) class ==")
cls = defaultdict(list)
for x in range(256):
    cls[rank(x)].append(x)
for p in range(8):
    print(f"  priority {p}: {len(cls[p]):3d} bytes tie")
n_pairs = sum(len(v) * (len(v) - 1) // 2 for v in cls.values())
print(f"  distinct bytes that tie pairwise: {n_pairs} of {256*255//2} pairs")

print("\n== 2. the law discards every bit above the lowest set evidence bit ==")
# For each x (not vetoed, with evidence), rank(x) == rank(lowest set bit of x)
low_only = all(rank(x) == rank(x & -x) for x in range(128) if x)
print(f"  rank(x) == rank(x & -x) for all 1<=x<128: {low_only}")
discarded = sum(bin(x).count('1') - 1 for x in range(128) if x)
print(f"  evidence bits set but not read across the 127 evidenced bytes: {discarded}")

print("\n== 3. bytes the BODY can construct today (guard.rank_observations) ==")
print("  FAILONLY never measured (docstring), RETRIED never passed by a caller")
body = [x for x in range(256) if not (x & FAILONLY) and not (x & RETRIED)]
c = Counter(rank(x) for x in body)
print(f"  reachable bytes: {len(body)}; priorities reachable: {sorted(c)}")
for p in sorted(c):
    print(f"  priority {p}: {c[p]:3d} reachable bytes tie")
print("  priority 1 (FAILONLY) reachable:", 1 in c)
print("  priority 7 reachable only by the all-zero byte:", c[7] == 1)

print("\n== 4. bytes under the MechanicalObserver (SIGNALED always 1) ==")
print("  observers.py:39-40 emits an Observation only `if kinds:` -> SIGNALED=1")
mech = [x for x in body if x & SIGNALED]
c2 = Counter(rank(x) for x in mech)
print(f"  reachable bytes: {len(mech)}; priorities reachable: {sorted(c2)}")
for p in sorted(c2):
    print(f"  priority {p}: {c2[p]:3d} bytes tie")
masked = all(rank(x) == rank(x & (FRAME | NAMED | SIGNALED)) for x in mech)
print(f"  RECENT/CHEAP/DENSE never change the priority when SIGNALED=1: {masked}")
# show one concrete pair per priority class
print("  concrete ties (same priority, different evidence):")
for p in sorted(c2):
    xs = [x for x in mech if rank(x) == p]
    print(f"    p={p}: {names(min(xs))}  ==  {names(max(xs))}")

print("\n== 5. monotone but not strict: adding evidence can only tie or improve ==")
strict_improve = sum(1 for x in range(128) for b in range(7)
                     if not (x >> b & 1) and rank(x | 1 << b) < rank(x))
tie_keep = sum(1 for x in range(128) for b in range(7)
               if not (x >> b & 1) and rank(x | 1 << b) == rank(x))
print(f"  bit additions that improve priority: {strict_improve}")
print(f"  bit additions that leave it tied:    {tie_keep}")

print("\n== 6. the tie-break the body uses is not in the byte ==")
print("  guard.py:411-427 key = (rank(byte), -shared_name_tokens, incoming index)")
print("  shared_name_tokens is a DEGREE of NAMED; the law reads NAMED as 0/1 only")
print("  incoming index = Packet.lines order = ascending line number (localize.py:38)")
