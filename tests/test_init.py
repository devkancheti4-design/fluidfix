# SPDX-License-Identifier: AGPL-3.0-or-later
"""`fluidfix init`: the zero-tests on-ramp, end to end.

A beginner repo with NO tests becomes guardable in three commands:
init generates an import-smoke suite; the guard then repairs an
import-breaking mechanical regression using it as the oracle."""
import subprocess
import sys

from fluidfix.cli import main as cli_main


def test_init_generates_suite_and_guard_repairs(tmp_path, capsys):
    # a beginner project: two modules, zero tests
    (tmp_path / "pricing.py").write_text(
        'BASE = 100\nLABEL = "v" + "1"\n\ndef price():\n    return BASE\n')
    (tmp_path / "helpers.py").write_text("def double(x):\n    return x * 2\n")
    (tmp_path / "broken_dep.py").write_text("import not_a_real_package_xyz\n")
    (tmp_path / ".gitignore").write_text(".fluidfix/\n__pycache__/\n.coverage\n.pytest_cache/\n")

    assert cli_main(["init", str(tmp_path), "--python", sys.executable]) == 0
    out = capsys.readouterr().out
    assert "guarding 2 module(s)" in out
    assert "broken_dep" in out                       # reported as skipped
    smoke = (tmp_path / "test_fluidfix_smoke.py").read_text()
    assert '"pricing",' in smoke and '"helpers",' in smoke
    assert "broken_dep" not in smoke.split("MODULES")[1]

    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "i@t"],
                ["git", "config", "user.name", "i"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "seed"]):
        subprocess.run(cmd, cwd=tmp_path, check=True, capture_output=True)

    # green suite -> guard touches nothing
    assert cli_main(["guard", str(tmp_path), "--python", sys.executable]) == 0

    # an import-breaking mechanical regression ships: "+" -> "-" on str concat
    (tmp_path / "pricing.py").write_text(
        'BASE = 100\nLABEL = "v" - "1"\n\ndef price():\n    return BASE\n')
    subprocess.run(["git", "commit", "-aqm", "ship label change"], cwd=tmp_path,
                   check=True, capture_output=True)
    assert cli_main(["guard", str(tmp_path), "--python", sys.executable,
                     "--commit"]) == 0
    assert '"v" + "1"' in (tmp_path / "pricing.py").read_text()
    log = subprocess.run(["git", "log", "--oneline", "-1"], cwd=tmp_path,
                         capture_output=True, text=True).stdout
    assert "fluidfix: restore pricing.py" in log


def test_init_refuses_to_clobber_without_force(tmp_path, capsys):
    (tmp_path / "m.py").write_text("X = 1\n")
    (tmp_path / "test_fluidfix_smoke.py").write_text("# existing\n")
    assert cli_main(["init", str(tmp_path)]) == 1
    assert "--force" in capsys.readouterr().out
