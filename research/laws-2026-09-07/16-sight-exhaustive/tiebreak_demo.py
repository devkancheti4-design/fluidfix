#!/usr/bin/env python
"""Inside one SIGHT priority class the LAW rules a tie and the CALLER breaks
it. sight.py:61-62 says callers use "specificity, then executed-line count";
guard.py:208 says "Specificity still breaks ties INSIDE a priority class".
The actual key, transcribed VERBATIM from guard.py:195 and :300-301, is

    ranked2.append((affinity, specificity, n_fail, rel))          # :195
    ranked2.sort(key=lambda t: (file_priority2(t[3], t[1], t[2]), # :300
                                -t[0], -t[1], -t[2], t[3]))        # :301

i.e. priority, then AFFINITY (the same filename-token overlap that sets the
NAMED bit), then specificity, then executed lines, then path. This script
applies that key to two synthetic files that the law puts in the same class.
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.sight import observe_bits, sight  # noqa: E402

# (affinity, specificity, n_fail, rel, bits) -- two files both POINTED at.
# A: pointed by SCARCE, very specific to the failure, no name overlap.
# B: pointed by LITERAL, weakly specific, but its name shares a token with
#    the failing test module (affinity 1.0 == NAMED bit set).
files = [
    (0.0, 1.00, 40, "pkg/types.py",
     observe_bits(scarce=True, failonly=True, small=True)),
    (1.0, 0.30, 500, "pkg/shell_completion.py",
     observe_bits(literal=True, named=True)),
]
for aff, spec, n, rel, bits in files:
    print(f"  {rel:<26} bits={bits:<3} sight={sight(bits)}  affinity={aff} "
          f"specificity={spec} n_fail={n}")

key_as_written = lambda t: (sight(t[4]), -t[0], -t[1], -t[2], t[3])   # noqa: E731
key_as_documented = lambda t: (sight(t[4]), -t[1], -t[2], t[3])        # noqa: E731

print()
print("order under the key AS WRITTEN (guard.py:300-301, affinity first):")
for t in sorted(files, key=key_as_written):
    print("   ", t[3])
print("order under the key AS DOCUMENTED (sight.py:61-62, specificity first):")
for t in sorted(files, key=key_as_documented):
    print("   ", t[3])
