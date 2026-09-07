#!/usr/bin/env python
"""Totality probe: pair_law's domain is documented as ONE BYTE. What happens
if a caller hands it something else? The Python port replaces C's
__builtin_ctz with a `while low >> 1` loop, which does not terminate on a
zero mask, so the question is whether the mask can ever be zero or negative.

The mask is computed WITHOUT calling pair_law, so a hostile input cannot
hang this probe.
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.pair as P                                        # noqa: E402
from fluidfix.pair import pair_law, situation, observe_bits      # noqa: E402


def mask_of(x):
    s = P._s32
    x = s(x)
    gr, gc = s(0 - P._READY(x)), s(P._CANCEL(x) - 1)
    gb, gp, gcp = s(P._BLOCK(x) - 1), s(0 - P._PARTIAL(x)), s(0 - P._COUPLED(x))
    pair = s(gp & gcp & P._CHEAP2(x))
    widen = s(gp & P._NOTCOUP(x))
    act = s(gr & (P._PARTITION(x) + pair + widen + P._TEACH(x) + P._BUDGET(x)))
    return s((gb & (act + P._SINGLE(x))) + (gc & P._CAPPED_L(x)) + 128)


out = []
p = out.append

p("1. the documented domain, 0..255")
zero = [x for x in range(256) if mask_of(x) == 0]
p(f"   masks equal to zero (would hang the port's ctz loop): {zero}")
p(f"   outputs outside 0..7: "
  f"{[x for x in range(256) if not 0 <= pair_law(x) <= 7]}")

p("")
p("2. outside the documented domain (a caller bypassing situation()/"
  "observe_bits())")
probe = list(range(-4096, 4097)) + [1 << 20, -(1 << 20), (1 << 31) - 1,
                                    -(1 << 31), 1 << 31, 0xFFFFFFFF]
bad_zero = [x for x in probe if mask_of(x) == 0]
p(f"   inputs probed                     : {len(probe)}")
p(f"   inputs whose mask is zero         : {len(bad_zero)} -> "
  f"{bad_zero[:12]}")
if bad_zero:
    p("   NOTE: mask==0 means the port's `while low >> 1` loop is entered with")
    p("   low==0 and exits immediately returning 0 == PARTITION; C's")
    p("   __builtin_ctz(0) is undefined behaviour on the same input.")
    for x in bad_zero[:6]:
        v = pair_law(x)
        name = P.ACTS[v] if 0 <= v < 8 else "NOT AN ACT"
        p(f"      x={x}  port returns {v} ({name})")
outs = {}
for x in probe:
    if mask_of(x) != 0:
        v = pair_law(x)
        if not 0 <= v <= 7:
            outs[x] = v
p(f"   inputs returning a NON-ACT index  : {len(outs)} -> "
  f"{list(outs.items())[:12]}")

p("")
p("3. the two documented entry points cannot leave 0..255")
p(f"   situation(**all eight bits) = "
  f"{situation(**{b: True for b in P.BITS})}")
p(f"   observe_bits(all true)      = "
  f"{observe_bits(exhausted=True, partial=True, disjoint=True, coupled=True, cheap=True, taught=True, canceling=True, capped=True)}")

text = "\n".join(out)
print(text)
with open("/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/"
          "21-pair-exhaustive/domain_output.txt", "w") as fh:
    fh.write(text + "\n")
