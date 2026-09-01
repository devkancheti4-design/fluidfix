# SPDX-License-Identifier: AGPL-3.0-or-later
"""--dry-run: the propose-only channel. A landing repair becomes a patch in
.fluidfix/proposed.patch; the tree stays byte-identical to the broken state."""
import subprocess
import sys

import pytest

from fluidfix import Oracle
from fluidfix.cli import main as cli_main

BUGGY = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
         "        if x >= t:\n            n += 1\n    return n\n")
TEST = ("from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")


def _git(d, *args):
    return subprocess.run(["git", "-C", str(d), *args], capture_output=True,
                          text=True, check=False)


def _repo(tmp_path, git=True):
    (tmp_path / "mod.py").write_text(BUGGY)
    (tmp_path / "test_mod.py").write_text(TEST)
    if git:
        (tmp_path / ".gitignore").write_text(
            ".fluidfix/\n__pycache__/\n.coverage\n.pytest_cache/\n")
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "config", "user.email", "dry@test")
        _git(tmp_path, "config", "user.name", "dry")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-qm", "ship (strictness bug included)")


def test_dry_run_proposes_restores_and_patch_applies(tmp_path, capsys):
    _repo(tmp_path)
    broken = (tmp_path / "mod.py").read_bytes()
    assert cli_main(["guard", str(tmp_path), "--python", sys.executable,
                     "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert (tmp_path / "mod.py").read_bytes() == broken      # byte-identical
    assert _git(tmp_path, "status", "--porcelain", "-uno").stdout.strip() == ""
    assert "PROPOSED (dry-run): apply with git apply .fluidfix/proposed.patch" in out
    assert "-        if x >= t:" in out and "+        if x > t:" in out
    assert (tmp_path / ".fluidfix" / "proposed.patch").exists()
    assert _git(tmp_path, "apply", ".fluidfix/proposed.patch").returncode == 0
    assert "if x > t:" in (tmp_path / "mod.py").read_text()
    assert Oracle(str(tmp_path), python=sys.executable).green()


def test_dry_run_without_git_falls_back_to_difflib(tmp_path, capsys):
    # no repo: the patch comes from difflib, with a/ b/ headers git apply
    # (which works outside a repository too) still consumes
    _repo(tmp_path, git=False)
    broken = (tmp_path / "mod.py").read_bytes()
    assert cli_main(["guard", str(tmp_path), "--python", sys.executable,
                     "--dry-run"]) == 0
    assert (tmp_path / "mod.py").read_bytes() == broken
    patch = (tmp_path / ".fluidfix" / "proposed.patch").read_text()
    assert patch.startswith("--- a/mod.py")
    assert _git(tmp_path, "apply", ".fluidfix/proposed.patch").returncode == 0
    assert "if x > t:" in (tmp_path / "mod.py").read_text()


def test_dry_run_refusal_behaves_exactly_as_today(tmp_path):
    src = "def both(a, b):\n    return bool(a or b)\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import both\n\ndef test_b():\n"
        "    assert both(True, False) is False\n")
    assert cli_main(["guard", str(tmp_path), "--python", sys.executable,
                     "--dry-run"]) == 2
    assert (tmp_path / "mod.py").read_text() == src
    assert (tmp_path / ".fluidfix" / "last_refusal.json").exists()
    assert not (tmp_path / ".fluidfix" / "proposed.patch").exists()


def test_commit_and_dry_run_are_mutually_exclusive(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        cli_main(["guard", str(tmp_path), "--commit", "--dry-run"])
    assert e.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


def test_dry_run_returns_after_proposing_even_with_interval(tmp_path):
    # the proposal is the pass's whole product — looping would grind out the
    # same patch every interval until someone applies it
    _repo(tmp_path)
    assert cli_main(["guard", str(tmp_path), "--python", sys.executable,
                     "--dry-run", "--interval", "9999"]) == 0
