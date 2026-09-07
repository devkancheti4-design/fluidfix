import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of

def body_order(kinds):
    """Exactly what loop.py:283-298 does with obs.kinds."""
    mask = mask_of(k for k in kinds if 0 <= k <= 15)
    out = []
    while not HALT(mask):
        out.append(kind_of(EMIT(mask)))
        mask = ADVANCE(mask)
    return out

print("acts.py:60 contract: Observation.kinds is 'most specific first'.")
print("loop.py:283 collapses that list to a bitmask; lanes.EMIT then takes the LOWEST LIVE BIT.\n")
for kinds in ([3, 1], [1, 3], [12, 0], [0, 12], [10, 0, 1], [8, 3], [3, 8]):
    print(f"  observer said kinds={str(kinds):<12} -> body tries kinds in order {body_order(kinds)}")
print("\n  duplicate-insensitive too:", body_order([3,3,1]), "==", body_order([1,3]))
print("\n  => the observer's stated priority is NOT preserved; order is ascending kind number.")
print("     Kind numbers come from the KINDS dict literal in acts.py:74-114 (a code decision),")
print("     not from any law. lanes.EMIT rules the TRAVERSAL of the mask, not the priority.")
