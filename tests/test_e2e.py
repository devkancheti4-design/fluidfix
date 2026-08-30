# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-to-end: localise -> observe (mechanically) -> route -> repair -> verify.

Uses this interpreter's own pytest as the target-project runner.
"""
import os
import sys
import textwrap

import pytest

from fluidfix import MechanicalObserver, Oracle, build_packet, repair

BUGGY = textwrap.dedent("""\
    def count_above(xs, t):
        n = 0
        for x in xs:
            if x >= t:
                n += 1
        return n
""")

TEST = textwrap.dedent("""\
    from mod import count_above

    def test_count_above():
        assert count_above([1, 5, 5, 9], 5) == 1
""")

def _project(tmp_path, module_src, test_src):
    (tmp_path / "mod.py").write_text(module_src)
    (tmp_path / "test_mod.py").write_text(test_src)
    return Oracle(str(tmp_path), python=sys.executable)


def test_repairs_strictness_bug_byte_exact(tmp_path):
    oracle = _project(tmp_path, BUGGY, TEST)
    packet = build_packet(oracle, "mod.py", coverage_target="mod")
    assert packet is not None
    assert 4 in packet.lines                      # the buggy line is localised
    observations = MechanicalObserver().observe([packet])[0]
    result = repair(oracle, "mod.py", observations)
    assert result.repaired
    assert result.new_line.strip() == "if x > t:"
    assert oracle.green()


def test_green_suite_refuses_before_searching(tmp_path):
    fixed = BUGGY.replace("x >= t", "x > t")
    oracle = _project(tmp_path, fixed, TEST)
    assert build_packet(oracle, "mod.py", coverage_target="mod") is None
    result = repair(oracle, "mod.py", [])
    assert result.refused and not result.repaired
    assert "no failing test" in result.reason
    assert (tmp_path / "mod.py").read_text() == fixed   # untouched


def test_failed_repair_restores_source(tmp_path):
    # and/or fault: outside the vocabulary — must refuse and restore
    src = textwrap.dedent("""\
        def both(a, b):
            return bool(a or b)
    """)
    tst = textwrap.dedent("""\
        from mod import both

        def test_both():
            assert both(True, False) is False
    """)
    oracle = _project(tmp_path, src, tst)
    packet = build_packet(oracle, "mod.py", coverage_target="mod")
    assert packet is not None
    observations = MechanicalObserver().observe([packet])[0]
    result = repair(oracle, "mod.py", observations)
    assert result.refused and not result.repaired
    assert (tmp_path / "mod.py").read_text() == src     # byte-identical restore
