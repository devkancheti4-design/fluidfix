"""The engine byte as measured vs the byte the truth supports, for all four cells.

    /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python law_bytes.py

No incident here is a `ruling`: on the CORRECT byte the law rules correctly in
every one of the four cells.  The defect is the AMB bit fluidfix hands it.
"""
from fluidfix.engine import ACTS, BITS, decide, situation

# fixture, greens-are-one-program?, set_amb, len(sites)
CELLS = [
    ("A1-same-set-one-program",   True,  True,  1),
    ("A2-cross-set-one-program",  True,  False, 1),
    ("B1-same-set-two-programs",  False, True,  1),
    ("B2-cross-set-two-programs", False, False, 1),
]

print("BITS =", BITS)
print("ACTS =", ACTS)
print()
hdr = (f"{'fixture':<28} {'proxy AMB':>9} {'byte':>7} {'law says':<10} "
       f"{'true AMB':>8} {'byte':>7} {'law would say':<10}  verdict")
print(hdr)
print("-" * len(hdr))
for name, one_program, set_amb, n_sites in CELLS:
    proxy = set_amb or n_sites > 1              # loop.py `_rule`, verbatim
    truth = not one_program                     # two programs == real AMB
    b_proxy = situation(BUILT=True, AMB=proxy, CAPPED=False)
    b_truth = situation(BUILT=True, AMB=truth, CAPPED=False)
    a_proxy, a_truth = decide(b_proxy), decide(b_truth)
    verdict = "OK" if a_proxy == a_truth else "WRONG  <<<"
    print(f"{name:<28} {str(proxy):>9} {b_proxy:>7} {a_proxy:<10} "
          f"{str(truth):>8} {b_truth:>7} {a_truth:<10}  {verdict}")
