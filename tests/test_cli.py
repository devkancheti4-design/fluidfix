# SPDX-License-Identifier: AGPL-3.0-or-later
"""CLI surface: help layout, exit-code docs, --python validation, `kinds`."""
import os
import subprocess
import sys

import pytest

from fluidfix.acts import ACTS, KINDS
from fluidfix.cli import main as cli_main

DICT = '''\
register(4, "off-by-two",
         "a numeric literal exactly two greater than correct",
         re.compile(r"\\\\d"),
         lambda line, o: line)
'''


def test_kinds_lists_stock_classes_and_free_slots(capsys):
    assert cli_main(["kinds"]) == 0
    out = capsys.readouterr().out
    for name in ("strictness", "literal-off-by-one", "swapped-return-operands",
                 "flipped-additive", "minmax-swap", "flipped-augmented-assign",
                 "flipped-comparison-direction", "reversed-minus-operands",
                 "flipped-boolean"):
        assert name in out
    assert "(shipped)" in out and "free for users" in out
    assert "  4  (free" in out                       # the reserved user slots


def test_kinds_shows_a_taught_dictionary_class(tmp_path, capsys):
    (tmp_path / "rules.py").write_text(DICT)
    saved_kinds, saved_acts = dict(KINDS), dict(ACTS)
    try:
        assert cli_main(["kinds", "--dictionary",
                         str(tmp_path / "rules.py")]) == 0
        out = capsys.readouterr().out
        assert "off-by-two" in out and "(taught)" in out
    finally:
        KINDS.clear(); KINDS.update(saved_kinds)
        ACTS.clear(); ACTS.update(saved_acts)


def test_bad_python_fails_fast_with_one_line_no_traceback(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "fluidfix.cli", "repair", str(tmp_path),
         "--file", "x.py", "--python", "no/such/interpreter"],
        capture_output=True, text=True)
    assert r.returncode == 2
    assert "Traceback" not in r.stdout + r.stderr
    assert "not a working interpreter" in r.stderr
    assert "\n" not in r.stderr.strip()              # exactly one line


def test_relative_python_resolves_against_invoking_cwd(tmp_path, monkeypatch,
                                                       capsys):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "m.py").write_text("X = 1\n")
    (tmp_path / "venvpy").symlink_to(sys.executable)
    monkeypatch.chdir(tmp_path)
    # "./venvpy" only exists relative to the INVOKING cwd, not to proj
    assert cli_main(["init", str(proj), "--python",
                     os.path.join(os.curdir, "venvpy")]) == 0
    assert "guarding 1 module(s)" in capsys.readouterr().out


def test_help_examples_epilog_and_exit_code_docs(capsys):
    with pytest.raises(SystemExit) as e:
        cli_main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert "examples:" in out and "fluidfix repair ROOT --file pkg/mod.py" in out
    for cmd, codes in (("guard", "0 green or repaired, 2 refused"),
                       ("jguard", "0 green or repaired, 2 refused"),
                       ("repair", "0 repaired, 2 refused, 3 suite green")):
        with pytest.raises(SystemExit):
            cli_main([cmd, "--help"])
        assert codes in capsys.readouterr().out
