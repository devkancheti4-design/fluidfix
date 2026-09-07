"""The observation bytes the brief asks for, printed not asserted."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS, ACTS

print("BITS:", BITS)
print("ACTS:", ACTS)
print()
cases = {
 "BOM  -- byte AS DELIVERED (REFUTED)":        situation(REFUTED=True),
 "BOM  -- byte AS IT SHOULD HAVE BEEN":        situation(BUILT=True, AMB=False, CAPPED=False),
 "SPAN -- byte at ship time (BUILT only)":     situation(BUILT=True),
}
for name, b in cases.items():
    print(f"{name:<44} byte=0x{b:02x} ({b:>3})  decide -> {decide(b)}")
