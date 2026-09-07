#!/usr/bin/env python
"""Build the victim repo for the RETRIED-veto / class-order attack.

Shape (all of it mechanical, nothing hand-tuned to fluidfix internals beyond
the two bits the ranking law actually reads):

  pkg/core.py
    alpha_beta_helper(seed)   N decoy lines `acc.append(a + b)`.
        Its NAME shares tokens with the FAILING test's name, so the ranking
        law measures NAMED=1 on every decoy line  ->  priority 2.
        Interleaved with signal-free filler lines (`a = acc.pop()`), which
        localize.build_packet's signal filter drops -> packet.truncated=True
        at pass 0, which is what makes guard_once escalate.
    gamma_delta(x, y)         the REAL defect: `return x - y`, wants `+`.
        Its name shares NO token with the failing test  ->  NAMED=0,
        DENSE=0  ->  priority 3.  It is ranked behind all N decoys.

  tests/test_ledger.py
    test_alpha_beta   FAILS (pins gamma_delta), and CALLS the helper so the
                      helper's lines are covered and enter the packet.
    test_helper_values PASSES, pins every decoy line's arithmetic.

usage: make_victim.py <dest-dir> [n_decoys]
"""
import os
import shutil
import sys

DEST = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 90

shutil.rmtree(DEST, ignore_errors=True)
os.makedirs(os.path.join(DEST, "pkg"))
os.makedirs(os.path.join(DEST, "tests"))

body = []
body.append('"""Ledger core."""')
body.append("")
body.append("")
body.append("def alpha_beta_helper(seed):")
body.append('    """Every line here is executed by the failing test."""')
body.append("    acc = []")
body.append("    a = seed")
body.append("    b = seed")
for i in range(N):
    body.append("    acc.append(a + b)")     # DECOY i  (NAMED, DENSE -> rank 2)
    body.append("    a = acc.pop()")         # signal-free filler
    body.append("    b = a")                 # signal-free filler
body.append("    return a")
body.append("")
body.append("")
body.append("def gamma_delta(x, y):")
body.append('    """The real defect lives on the next line."""')
body.append("    return x - y")             # DEFECT (NAMED=0, DENSE=0 -> rank 3)
body.append("")

open(os.path.join(DEST, "pkg", "core.py"), "w").write("\n".join(body))
open(os.path.join(DEST, "pkg", "__init__.py"), "w").write("")

expected = 3
for _ in range(N):
    expected = expected + expected
open(os.path.join(DEST, "tests", "test_ledger.py"), "w").write(f'''\
from pkg import core


def test_alpha_beta():
    assert core.alpha_beta_helper(3) > 0
    assert core.gamma_delta(7, 5) == 12


def test_helper_values():
    assert core.alpha_beta_helper(3) == {expected}
''')

open(os.path.join(DEST, "pytest.ini"), "w").write("[pytest]\ntestpaths = tests\npythonpath = .\n")
print(f"built {DEST} with {N} decoy lines; defect at "
      f"pkg/core.py:{len(body) - 1}")
