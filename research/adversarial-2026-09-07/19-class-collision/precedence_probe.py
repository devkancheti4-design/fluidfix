"""Corollary: teaching ANY class in the reserved user slots 4-7 silently
pre-empts shipped classes 8-12 on every line where both signals match.
No suite is run here -- this is the EMIT order loop.py:297 will use."""
import re
from fluidfix.acts import KINDS, ACTS, register
from fluidfix.lanes import mask_of, EMIT, ADVANCE, HALT, kind_of

line = '    return max(a, b) if enabled else min(a, b)'
def order(l):
    ks = [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(l)]
    m, out = mask_of(ks), []
    while not HALT(m):
        out.append(kind_of(EMIT(m))); m = ADVANCE(m)
    return ks, out

print("line:", line)
print("\nBEFORE teaching anything:")
ks, o = order(line)
print("   kinds", ks, "-> tried in order", [f"{k}:{KINDS[k][0]}" for k in o])

register(4, "toy-taught-class", "any user class at all",
         re.compile(r"\breturn\b"), lambda l, o: [l])
print("\nAFTER one register(4, ...) -- the taught class did nothing but exist:")
ks, o = order(line)
print("   kinds", ks, "-> tried in order", [f"{k}:{KINDS[k][0]}" for k in o])
print("\n   every shipped kind >= 8 now runs AFTER the taught class on this line,")
print("   and loop.py ships greens[0] -- the FIRST green found.")
