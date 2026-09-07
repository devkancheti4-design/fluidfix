"""Print the exact observation byte the engine law was handed in runs A and B,
and show that class ORDER is unrepresentable in it."""
import itertools
from fluidfix.engine import decide, situation, BITS, ACTS
from fluidfix.lanes import mask_of, EMIT, ADVANCE, HALT, kind_of

print("BITS =", BITS)
print("ACTS =", ACTS)

# What loop.py:217 actually built in BOTH runs (greens=2, one site, not capped,
# set_amb False because the two greens came from two DIFFERENT candidate sets):
sit = situation(BUILT=True, AMB=False, CAPPED=False)
print(f"\nrun A byte: 0x{sit:04x} ({sit})  -> decide = {decide(sit)}")
print(f"run B byte: 0x{sit:04x} ({sit})  -> decide = {decide(sit)}   <-- IDENTICAL")

# What the law WOULD have ruled on the byte the situation actually was:
amb = situation(BUILT=True, AMB=True, CAPPED=False)
print(f"\ncorrect byte (AMB set): 0x{amb:04x} ({amb}) -> decide = {decide(amb)}")

# Class order is unrepresentable: every permutation of the observed kinds
# collapses to ONE mask at loop.py:283, and loop.py:297 then emits lowest-first.
print("\nloop.py:283  mask_of() over every permutation of kinds [4,5]:")
for p in itertools.permutations([4, 5]):
    m = mask_of(p)
    order, mm = [], m
    while not HALT(mm):
        order.append(kind_of(EMIT(mm)))
        mm = ADVANCE(mm)
    print(f"   observer said kinds={list(p)!s:<8} -> mask {bin(m):>8} -> tried {order}")
print("\nsix-kind line, all 720 permutations:")
ks = [0, 1, 3, 4, 5, 9]
masks = {mask_of(p) for p in itertools.permutations(ks)}
print(f"   distinct masks = {len(masks)} out of 720 permutations: {[bin(m) for m in masks]}")
