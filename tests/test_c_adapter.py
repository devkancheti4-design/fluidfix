# SPDX-License-Identifier: AGPL-3.0-or-later
"""The C/C++ adapter: same contract surface, same kernels, a compiler as a
second oracle.

The end-to-end test builds a tiny C project in a tmp dir and repairs a real
defect through the whole pipeline — no cloned repo, no network. The parser
tests pin the two runner formats measured in the wild, because C has no
pytest monoculture and a parser tuned to one sees nothing in the other.
"""
import os
import shutil
import subprocess

import pytest

from fluidfix.coracle import (COracle, _c_sources, _fail_names,
                              build_packet_c, cguard_once,
                              find_candidate_files_c)

HAS_CC = shutil.which("cc") is not None


# ------------------------------------------------------- runner formats --
def test_parses_the_cglm_runner_format():
    """cglm: a cross mark, then the test name."""
    assert _fail_names("𐄂 glm_vec3_add\n𐄂 glm_quat_look") == \
        ["glm_vec3_add", "glm_quat_look"]


def test_parses_the_box2d_runner_format():
    """Box2D: `test failed: MathTest`, and NO file or line anywhere.
    Measured 2026-09-03 — a cglm-tuned parser extracted zero from this."""
    out = "condition false: abs(w.x - u.x) < 4.7e-07\ntest failed: MathTest\n"
    assert _fail_names(out) == ["MathTest"]


def test_parses_generic_FAILED_shapes():
    assert "MyThing" in _fail_names("FAILED: MyThing")
    assert "OtherThing" in _fail_names("OtherThing ... FAILED")


# ------------------------------------------------------ source discovery --
def test_sample_and_harness_trees_are_never_candidates(tmp_path):
    """Measured on Box2D: `DeterminismTest` matched shared/determinism.c and
    samples/sample_determinism.cpp — demo code that cannot hold a defect."""
    for rel in ("src/solver.c", "samples/sample_determinism.cpp",
                "shared/determinism.c", "test/test_world.c", "extern/dep.c"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("int x;\n")
    found = set(_c_sources(str(tmp_path)).values())
    assert found == {"src/solver.c"}


def test_a_stem_maps_to_every_file_that_shares_it(tmp_path):
    """vec3.c and vec3.h share the stem `vec3`; in a header-implemented
    library the .c is a wrapper and the header holds the defect. Keeping
    only one silently searched the wrapper."""
    for rel in ("src/vec3.c", "include/vec3.h"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("float f(void){ return 1 + 2; }\n" * 40)
    o = COracle(str(tmp_path), build_dir="build")
    o._fail_tests = ["glm_vec3_add"]
    got = find_candidate_files_c(o, "")
    assert "include/vec3.h" in got and "src/vec3.c" in got


def test_camelcase_test_names_are_split(tmp_path):
    """`MathTest` is one token to a naive splitter, and `math` is the only
    part that names anything."""
    p = tmp_path / "src" / "math_functions.c"
    p.parent.mkdir(parents=True)
    p.write_text("float f(void){ return 1 + 2; }\n" * 40)
    o = COracle(str(tmp_path), build_dir="build")
    o._fail_tests = ["MathTest"]
    assert "src/math_functions.c" in find_candidate_files_c(o, "")


def test_the_test_harness_is_never_a_candidate(tmp_path):
    """THE ORACLE IS NOT A CANDIDATE. Caught by this file's own end-to-end
    test on 2026-09-04: a runner at the repo root was not recognised as test
    code and the guard repaired the RUNNER instead of the defect. If the
    guard can edit the tests it can "repair" anything by weakening the
    assertion — the one failure mode that voids every other guarantee."""
    for rel in ("src/solver.c", "runner.c", "test_main.c", "solver_test.c",
                "unit_tests.c"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("int x;\n")
    assert set(_c_sources(str(tmp_path)).values()) == {"src/solver.c"}


# ------------------------------------------------------------- packets ---
def test_coverage_lines_anchor_the_packet(tmp_path):
    """Given executed lines, the packet uses them and says mode=coverage."""
    p = tmp_path / "a.c"
    p.write_text("\n".join(f"int v{i} = {i} + 1;" for i in range(400)))
    o = COracle(str(tmp_path), build_dir="build")
    pk = build_packet_c(o, "a.c", "", covered={7, 9, 11})
    assert pk.mode == "coverage"
    assert pk.lines == [7, 9, 11]


def test_taught_signals_survive_truncation_when_sampling_would_not(tmp_path):
    """Measured on cglm: spread-sampling a 1,277-line header kept lines 283
    and 286 and dropped 284 — the defect. The vocabulary filter must keep a
    line a taught class could repair."""
    lines = ["void pad(void) { int q; }"] * 600
    lines[283] = "  dest[0] = a[0] - b[0];"          # flipped-additive
    p = tmp_path / "vec3.h"
    p.write_text("\n".join(lines))
    o = COracle(str(tmp_path), build_dir="build")
    pk = build_packet_c(o, "vec3.h", "")
    assert 284 in pk.lines
    assert pk.truncated                              # engine law: CAPPED


# ------------------------------------------------------------ end to end --
def _tiny_project(tmp_path, body):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mathx.c").write_text(
        f"int add(int a, int b) {{ return {body}; }}\n")
    (tmp_path / "src" / "mathx.h").write_text("int add(int, int);\n")
    (tmp_path / "runner.c").write_text(
        '#include <stdio.h>\n#include "src/mathx.h"\n'
        "int main(void){ if (add(2,3) != 5) "
        '{ printf("test failed: AddTest\\n"); return 1; } '
        'printf("all passed\\n"); return 0; }\n')
    return COracle(str(tmp_path),
                   build_cmd="cc -o runner runner.c src/mathx.c",
                   test_cmd="./runner", build_dir=".")


@pytest.mark.skipif(not HAS_CC, reason="no C compiler")
def test_green_project_is_left_alone(tmp_path):
    from fluidfix.observers import MechanicalObserver
    o = _tiny_project(tmp_path, "a + b")
    rep = cguard_once(o, MechanicalObserver(), budget=120)
    assert rep.status == "green"


@pytest.mark.skipif(not HAS_CC, reason="no C compiler")
def test_repairs_a_real_c_defect_end_to_end(tmp_path):
    """The whole pipeline on real C: build, run, parse, rank, mutate, judge,
    accept. Mirrors the measured Box2D result (b2Cross sign flip, byte-exact
    in 46 suite runs) at a size CI can afford."""
    from fluidfix.observers import MechanicalObserver
    o = _tiny_project(tmp_path, "a - b")             # the defect
    rep = cguard_once(o, MechanicalObserver(), budget=300)
    assert rep.status == "repaired", rep.summary()
    assert rep.file == "src/mathx.c"
    src = (tmp_path / "src" / "mathx.c").read_text()
    assert "a + b" in src                            # byte-exact restoration


def test_a_green_exit_code_with_failures_in_the_output_is_not_green(tmp_path):
    """A GREEN EXIT CODE IS NOT ENOUGH — the oracle-gaming defence.

    Measured 2026-09-04: given a runner it could edit, the guard changed the
    harness's failing `return 1` to `return 0`. The defect was untouched and
    the output still read `test failed: AddTest`; only the exit code moved.
    Any repair tool that can reach its own oracle will find that edit,
    because it is the cheapest path to green."""
    class _Fake(COracle):
        def run(self, extra=None, timeout=None):
            return 0, "test failed: AddTest\n"      # exit 0, still failing
    o = _Fake(str(tmp_path), build_cmd="true", test_cmd="true", build_dir=".")
    ok, why = o.check(timeout=5)
    assert ok is False
    assert "silences the oracle" in why
    # and the guard must treat such a suite as RED, not green
    fails, _out = o.failing_output()
    assert fails is True


@pytest.mark.skipif(not HAS_CC, reason="no C compiler")
def test_will_not_repair_by_editing_the_harness_even_if_reachable(tmp_path):
    """Defence in depth: with the name-based harness exclusion disabled, the
    output cross-examination must still force a real repair."""
    import fluidfix.coracle as C
    from fluidfix.observers import MechanicalObserver
    o = _tiny_project(tmp_path, "a - b")
    runner_before = (tmp_path / "runner.c").read_text()
    orig, C._is_harness_file = C._is_harness_file, lambda b: False
    try:
        rep = cguard_once(o, MechanicalObserver(), budget=300)
    finally:
        C._is_harness_file = orig
    assert rep.status == "repaired"
    assert rep.file == "src/mathx.c"
    assert (tmp_path / "runner.c").read_text() == runner_before
    assert "a + b" in (tmp_path / "src" / "mathx.c").read_text()


@pytest.mark.skipif(not HAS_CC, reason="no C compiler")
def test_a_candidate_that_does_not_compile_is_rejected_not_fatal(tmp_path):
    """The compiler is a second oracle: a non-compiling candidate is the
    candidate's fault, judged in milliseconds without running a test."""
    o = _tiny_project(tmp_path, "a + b")
    (tmp_path / "src" / "mathx.c").write_text("int add(int a,int b){ return a +; }\n")
    ok, why = o.check(timeout=120)
    assert ok is False
    assert why                                       # names the compile error


def test_python_oracle_also_refuses_a_silenced_suite():
    """The exposure is structural, not language-specific. Python leans on
    `_is_test_path` to keep test files out of the candidate set, but a
    project may keep its tests somewhere fluidfix does not recognise — so
    the pytest exit code is cross-examined too."""
    from fluidfix.oracle import _still_reports_failures as f
    assert f("1 failed, 3 passed in 0.1s") == "1 failed"
    assert f("2 errors in 0.1s") == "2 errors"
    assert f("0 failed, 5 passed in 0.1s") == ""      # no false positive
    assert f("1990 passed, 25 skipped in 4.5s") == ""
