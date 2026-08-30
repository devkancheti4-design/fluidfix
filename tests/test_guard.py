# SPDX-License-Identifier: AGPL-3.0-or-later
"""The guard: commit-and-forget maintenance, end to end."""
import subprocess
import sys

from fluidfix import MechanicalObserver, Oracle, commit_repair, guard_once, write_refusal

BUGGY = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
         "        if x >= t:\n            n += 1\n    return n\n")
TEST = ("from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")


def _project(tmp_path, module_src=BUGGY, test_src=TEST):
    (tmp_path / "mod.py").write_text(module_src)
    (tmp_path / "test_mod.py").write_text(test_src)
    return Oracle(str(tmp_path), python=sys.executable)


def test_guard_finds_file_and_repairs_without_being_told(tmp_path):
    # pure assertion failure: no source frames — the coverage ranker must
    # discover mod.py on its own
    oracle = _project(tmp_path)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired" and report.file == "mod.py"
    assert "if x > t:" in (tmp_path / "mod.py").read_text()
    assert oracle.green()


def test_guard_follows_traceback_frames(tmp_path):
    # a raising fault: the traceback names mod.py directly
    oracle = _project(
        tmp_path,
        module_src="def join2(a, b):\n    return a - b\n",
        test_src=("from mod import join2\n\ndef test_j():\n"
                  "    assert join2('x', 'y') == 'xy'\n"))
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired" and report.file == "mod.py"
    assert "a + b" in (tmp_path / "mod.py").read_text()


def test_guard_green_touches_nothing(tmp_path):
    oracle = _project(tmp_path, module_src=BUGGY.replace("x >= t", "x > t"))
    before = (tmp_path / "mod.py").read_bytes()
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "green"
    assert (tmp_path / "mod.py").read_bytes() == before


def test_guard_refuses_novel_class_loudly_and_untouched(tmp_path):
    src = "def both(a, b):\n    return bool(a or b)\n"
    oracle = _project(
        tmp_path, module_src=src,
        test_src=("from mod import both\n\ndef test_b():\n"
                  "    assert both(True, False) is False\n"))
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert (tmp_path / "mod.py").read_text() == src
    path = write_refusal(str(tmp_path), report)
    assert "register()" in open(path).read() or "vocabulary" in open(path).read()


def test_guard_commit_records_the_restoration(tmp_path):
    oracle = _project(tmp_path)
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "guard@test"],
                ["git", "config", "user.name", "guard"],
                ["git", "add", "-A"],
                ["git", "commit", "-qm", "seed (bug included)"]):
        subprocess.run(cmd, cwd=tmp_path, check=True, capture_output=True)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert commit_repair(str(tmp_path), report) == "committed"
    log = subprocess.run(["git", "log", "--oneline", "-1"], cwd=tmp_path,
                         capture_output=True, text=True).stdout
    assert "fluidfix: restore mod.py:4" in log
    status = subprocess.run(["git", "status", "--porcelain", "-uno"],
                            cwd=tmp_path, capture_output=True, text=True).stdout
    assert status.strip() == ""          # no tracked file left modified
