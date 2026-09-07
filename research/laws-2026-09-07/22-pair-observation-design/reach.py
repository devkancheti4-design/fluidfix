"""Which PAIR acts are reachable given which bits the body can measure."""
import sys, collections
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.pair import ACTS, BITS, pair_law

EXH, PAR, DIS, COU, CHE, TAU, CAN, CAP = (1 << i for i in range(8))

def reach(free_mask, label):
    hit = collections.Counter()
    for x in range(256):
        if x & ~free_mask:            # bits the body cannot set must be 0
            continue
        hit[ACTS[pair_law(x)]] += 1
    missing = [a for a in ACTS if a not in hit]
    print(f"{label}\n  reachable: {dict(hit)}\n  UNREACHABLE: {missing}\n")

reach(EXH | CHE | TAU | CAP, "TODAY (loop.py measures EXHAUSTED/CHEAP/TAUGHT/CAPPED only)")
reach(EXH | CHE | TAU | CAP | PAR | DIS | COU,
      "WITH the failing-count + failing-set measurement (CANCELING still unobservable)")
reach(255, "ALL EIGHT BITS")
print("acts reachable ONLY when CANCELING can be set:",
      sorted({ACTS[pair_law(x)] for x in range(256) if x & CAN} -
             {ACTS[pair_law(x)] for x in range(256) if not (x & CAN)}))
print("byte count per act, all 256:",
      dict(collections.Counter(ACTS[pair_law(x)] for x in range(256))))
