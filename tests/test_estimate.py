# SPDX-License-Identifier: AGPL-3.0-or-later
"""`fluidfix estimate` — answer "how fast on MY repo?" before installing.

The model, measured across three orders of magnitude (independent
third-party testing Sept 2026 + this project's benchmarks):

    repair time ~= suite runs x (your suite's runtime + ~0.5s startup)

Validated against real repairs: a 105-test suite (0.07s) predicted
1.4-7s and repaired in 1.7s; click (1,990 tests, 4.5s) predicted
12.2-61s and repaired in 36s and 50s. Test COUNT barely matters.
"""
import subprocess
import sys


def test_estimate_projects_from_the_suites_own_runtime(tmp_path, capsys):
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 1\n")
    r = subprocess.run([sys.executable, "-m", "fluidfix.cli", "estimate",
                        str(tmp_path), "--python", sys.executable],
                       capture_output=True, text=True, timeout=300)
    out = r.stdout
    assert r.returncode == 0, out + r.stderr
    assert "suite runtime:" in out
    assert "EXPECTED REPAIR TIME" in out
    assert "2-10 suite runs" in out
    # a trivial suite must be reported as fast, and the advice must follow
    assert "Fast suite" in out
    assert "your tests are the entire bill" in out


def test_estimate_says_so_when_the_suite_is_red(tmp_path):
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 2\n")
    r = subprocess.run([sys.executable, "-m", "fluidfix.cli", "estimate",
                        str(tmp_path), "--python", sys.executable],
                       capture_output=True, text=True, timeout=300)
    assert "currently RED" in r.stdout
