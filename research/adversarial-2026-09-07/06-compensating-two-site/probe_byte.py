import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS, ACTS
b_ship = situation(BUILT=True, AMB=False, CAPPED=False)
b_true = situation(BUILT=True, AMB=True,  CAPPED=False)
print(f"byte AS MEASURED  = {b_ship} (0x{b_ship:03x})  bits={{BUILT}}          -> {decide(b_ship)}")
print(f"byte AS IT WAS    = {b_true} (0x{b_true:03x})  bits={{BUILT,AMB}}      -> {decide(b_true)}")
