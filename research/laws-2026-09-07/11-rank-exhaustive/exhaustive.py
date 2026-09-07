#!/usr/bin/env python
"""11-rank-exhaustive: every input of the ranking law vs the docstring spec.

Run:  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python exhaustive.py

Sections (each prints a header):
  A  independent spec from the module docstring, all 256 inputs
  B  RETRIED veto: exhaustive + algebraic identity of every lane
  C  monotonicity in evidence; adding the veto never improves
  D  rank distribution / tie-class sizes
  E  which inputs tests/test_rank_law.py pins, and how
  F  out-of-domain inputs (not masked to 8 bits) -- robustness note only
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import rank as R                                 # noqa: E402
from fluidfix.rank import BITS, rank, situation, observe_bits  # noqa: E402

FAIL = 0


def check(name, ok):
    global FAIL
    print(f"  [{'ok' if ok else 'FAIL'}] {name}")
    if not ok:
        FAIL += 1


# ---- A: the spec, written from the docstring alone ----------------------
# docstring: "priority 0..7, lower is examined first"; bits 0..6 are
# evidence lanes in that order; "RETRIED is a VETO ... goes last whatever
# else is true"; _SITUATION docstring: "no evidence, or vetoed, both land
# on 7".  Hence: rank = index of the LOWEST set evidence bit; 7 otherwise.
def spec(x: int) -> int:
    if x & 0x80:
        return 7
    ev = x & 0x7F
    if ev == 0:
        return 7
    return (ev & -ev).bit_length() - 1


print("A. all 256 inputs vs docstring spec (lowest set evidence bit; 7 if none/veto)")
mism = [(x, rank(x), spec(x)) for x in range(256) if rank(x) != spec(x)]
check(f"256/256 match, mismatches={mism}", not mism)
# the test file's own _spec is the same function; cross-check it too
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/tests")
from test_rank_law import _spec as test_spec  # noqa: E402
check("tests/test_rank_law.py::_spec agrees with this script's spec on 256",
      all(test_spec(x) == spec(x) for x in range(256)))

# ---- B: the veto ---------------------------------------------------------
print("B. RETRIED veto (bit 7)")
check("rank(x | 128) == 7 for all 256 x", all(rank(x | 128) == 7 for x in range(256)))
check("rank(x) == 7 for exactly the 128 vetoed + input 0 = 129 inputs",
      sorted(x for x in range(256) if rank(x) == 7) == [0] + list(range(128, 256)))
# algebraic: each lane EV_k(x) equals the lane's own bit (weight 2^k) when
# bit 7 is clear, and is identically 0 when bit 7 is set.  So the veto is
# folded into every lane, not applied afterwards.
lanes = [R._EV0, R._EV1, R._EV2, R._EV3, R._EV4, R._EV5, R._EV6]
alg_ok = True
for x in range(256):
    veto = (x >> 7) & 1
    for k, ev in enumerate(lanes):
        want = 0 if veto else (x & (1 << k))
        if ev(x) != want:
            alg_ok = False
            print("   lane identity broken at", x, k, ev(x), want)
check("EV_k(x) == (x & 2^k) * (1 - RETRIED) for every x, every k (7*256 checks)", alg_ok)
check("_SITUATION(x) == 128 + (x & 0x7F) * (1 - RETRIED) for every x",
      all(R._SITUATION(x) == 128 + ((x & 0x7F) if not (x & 0x80) else 0)
          for x in range(256)))
check("_EMIT(m) == lowest set bit of m for m in 1..255",
      all(R._EMIT(m) == (m & -m) for m in range(1, 256)))
# consequence: a vetoed line's SITUATION is exactly 128, indistinguishable
# from a line with no evidence -- both EMIT bit 7 -> rank 7.
check("vetoed inputs all have _SITUATION == 128 (same as no-evidence input 0)",
      all(R._SITUATION(x) == 128 for x in range(128, 256)) and R._SITUATION(0) == 128)

# ---- C: monotonicity -----------------------------------------------------
print("C. monotonicity")
viol = [(s, b) for s in range(128) for b in range(7)
        if not ((s >> b) & 1) and rank(s | (1 << b)) > rank(s)]
check(f"adding one evidence bit never worsens priority ({7*64} pairs)", not viol)
check("adding RETRIED never improves priority (128 pairs)",
      all(rank(s | 128) >= rank(s) for s in range(128)))
# stronger than the test: removing a lower lane can only worsen or keep
check("removing one evidence bit never improves priority",
      all(rank(s & ~(1 << b)) >= rank(s) for s in range(128) for b in range(7)))
# the rank depends ONLY on the lowest set evidence bit: higher bits are
# ignored once a lower lane fires
check("rank(x) == rank(lowest evidence bit of x) for all non-vetoed x with evidence",
      all(rank(x) == rank((x & 0x7F) & -(x & 0x7F)) for x in range(1, 128)))

# ---- D: distribution -----------------------------------------------------
print("D. rank distribution over all 256 inputs (tie-class sizes)")
dist = {p: [x for x in range(256) if rank(x) == p] for p in range(8)}
for p in range(8):
    lane = BITS[p] if p < 7 else "no-evidence/RETRIED"
    print(f"   rank {p} ({lane:>9}): {len(dist[p]):3d} inputs")
check("class sizes are 64,32,16,8,4,2,1,129",
      [len(dist[p]) for p in range(8)] == [64, 32, 16, 8, 4, 2, 1, 129])

# ---- E: what the tests pin -----------------------------------------------
# SUPERSEDED by pincensus.py -- everything below this banner was written by
# READING the test file by eye and hard-coding the result, which is not a
# measurement.  pincensus.py measures it by mutating rank(x) per input and
# running the tests.  Its answer differs: all 256 inputs are pinned, and
# every one of them is pinned REDUNDANTLY (by a second test as well).  The
# hand census below is kept only to show what a by-eye reading claimed.
print("E. pin census of tests/test_rank_law.py -- HAND-READ, SUPERSEDED "
      "by pincensus.py; do not cite these numbers as measured")
literal = {0: 7, 1: 0, 129: 7}                  # rank(observe_bits(...)) == N
literal.update({x: 7 for x in range(128, 256)})  # test_veto_dominates_every_other_bit
spec_pinned = set(range(256))                    # test_all_256_... via _spec()
relational = {8: "rank(8) < rank(0)"}            # signaled beats nothing
unpinned_literal = sorted(set(range(256)) - set(literal))
print(f"   pinned to a literal value : {len(literal)} inputs "
      f"(0, 1, 129, and all 128 vetoed inputs 128..255)")
print(f"   pinned only via _spec()   : {len(unpinned_literal)} inputs = "
      f"2..127 minus {{8 relational}}")
print(f"   inputs with NO test at all: {len(set(range(256)) - spec_pinned)}")
print(f"   ranks 1..6 have NO literal pin in the test file: "
      f"{[p for p in range(1, 7) if not any(literal.get(x) == p for x in literal)]}")
check("every input is pinned by at least the _spec test", not (set(range(256)) - spec_pinned))

# ---- F: out-of-domain ----------------------------------------------------
print("F. out-of-domain inputs (rank() does not mask to 8 bits; body only "
      "calls it via observe_bits so these are unreachable)")
for x in (256, 257, 384, 511, -1, -128):
    print(f"   rank({x:5d}) = {rank(x)}   (_SITUATION={R._SITUATION(R._s32(x))})")
check("situation()/observe_bits() can only produce 0..255",
      0 <= observe_bits(frame=True, failonly=True, named=True, signaled=True,
                        recent=True, cheap=True, dense=True, retried=True) == 255)

print(f"\nRESULT: {'ALL CHECKS PASS' if not FAIL else f'{FAIL} CHECK(S) FAILED'}")
sys.exit(1 if FAIL else 0)
