# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE central claim, CI-enforced: one example teaches a CLASS.

docs/proof_one_example.py is the human-runnable version of this test (it
prints the taught dictionary and every repair). This pins the same result to
the build: if one example ever stops generalising to the whole class, or the
out-of-class control ever stops being refused, the build goes red.
"""
import subprocess
import sys
from pathlib import Path


def test_one_example_heals_five_different_members_and_refuses_the_control():
    proof = Path(__file__).resolve().parent.parent / "docs" / "proof_one_example.py"
    r = subprocess.run([sys.executable, str(proof)], capture_output=True,
                       text=True, timeout=900)
    out = r.stdout + r.stderr
    assert "5/5 members repaired BYTE-EXACT from ONE example" in out, out[-2500:]
    assert "control correctly refused" in out, out[-2500:]
    assert r.returncode == 0, out[-2500:]
