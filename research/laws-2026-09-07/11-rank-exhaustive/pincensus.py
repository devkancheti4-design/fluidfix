#!/usr/bin/env python
"""11-rank-exhaustive: a MEASURED pin census of tests/test_rank_law.py.

The earlier exhaustive.py section E read the test file by eye and wrote the
census as a literal dict.  That is not a measurement.  This script measures
it: for each of the 256 inputs x, replace rank(x) with a WRONG value (every
one of the seven other rulings in turn, so the census does not depend on a
lucky choice of mutant) and run every test in tests/test_rank_law.py
in-process.  An input is PINNED iff some test goes red for some wrong value.

Nothing is written to tests/; the module is imported read-only and its test
functions are called directly.

Run:  nice -n 15 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python pincensus.py
"""
import sys
import tempfile

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/tests")

import fluidfix.rank as R                      # noqa: E402
import test_rank_law as T                      # noqa: E402

TRUE = R.rank                                  # the real law
GOLD = [TRUE(x) for x in range(256)]

TESTS = [(n, getattr(T, n)) for n in dir(T) if n.startswith("test_")]
print("tests found in tests/test_rank_law.py:")
for n, _ in TESTS:
    print("   ", n)


def run_all(mutant):
    """Install `mutant` as the law everywhere the tests can see it, run all
    tests, return the set of test names that went red."""
    R.rank = mutant
    T.rank = mutant                # the test module bound the name at import
    red = set()
    for name, fn in TESTS:
        try:
            with tempfile.TemporaryDirectory() as td:
                fn(td) if fn.__code__.co_argcount else fn()
        except BaseException:
            red.add(name)
    R.rank = TRUE
    T.rank = TRUE
    return red


# sanity: unmutated, every test must be green
assert not run_all(TRUE), "baseline is not green -- census is meaningless"
print("\nbaseline (no mutation): all tests green\n")

pinned_by = {}          # x -> set of test names that caught some wrong value
for x in range(256):
    caught = set()
    for wrong in range(8):
        if wrong == GOLD[x]:
            continue

        def mutant(v, _x=x, _w=wrong):
            return _w if v == _x else TRUE(v)

        caught |= run_all(mutant)
    pinned_by[x] = caught

unpinned = [x for x in range(256) if not pinned_by[x]]
print(f"PINNED   : {256 - len(unpinned)}/256 inputs")
print(f"UNPINNED : {len(unpinned)}/256 inputs -> {unpinned}")

# which test does the pinning, and how much of the pinning is exclusive
print("\ninputs caught by each test:")
for name, _ in TESTS:
    got = [x for x in range(256) if name in pinned_by[x]]
    only = [x for x in got if pinned_by[x] == {name}]
    print(f"   {name:<50} catches {len(got):3d}   sole pin for {len(only):3d}")

# If the one whole-domain test were deleted, what survives?
WHOLE = "test_all_256_situations_match_the_specification"
without = [x for x in range(256) if pinned_by[x] - {WHOLE}]
print(f"\nif {WHOLE}() were deleted, "
      f"{len(without)}/256 inputs would still be pinned by another test")
by_rank = {}
for x in without:
    by_rank.setdefault(GOLD[x], []).append(x)
for p in range(8):
    print(f"   rank {p}: {len(by_rank.get(p, []))} inputs still pinned")
print("   rulings that would lose EVERY pin: "
      f"{[p for p in range(8) if not by_rank.get(p)]}")
