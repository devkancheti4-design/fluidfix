# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regressions for the pre-release adversarial review (all reproduced live)."""
import sys
import textwrap

from fluidfix import MechanicalObserver, Observation, Oracle, apply, build_packet, repair


def obs(**kw):
    return Observation(lineno=1, **kw)


def test_zero_cleanup_never_touches_unrelated_constants():
    # critical: the old global sub ate `-0` inside abs(-0.5) elsewhere on the line
    line = "    return xs[1] * abs(-0.5)"
    assert (apply(line, 6, obs(literal_value="1", literal_occurrence=1))
            == "    return xs[0] * abs(-0.5)")
    # and never manufactures `.5` syntax errors
    line = "    return values[1] + 0.5"
    assert (apply(line, 6, obs(literal_value="1", literal_occurrence=1))
            == "    return values[0] + 0.5")
    # while the intended site-local simplification still works
    assert apply("bound = n + 1", 6, obs()) == "bound = n"


def test_crlf_file_untouched_on_refusal_and_preserved_on_repair(tmp_path):
    # major: universal-newline round trip rewrote CRLF files wholesale
    crlf_src = "def both(a, b):\r\n    return bool(a or b)\r\n"
    (tmp_path / "mod.py").write_bytes(crlf_src.encode())
    (tmp_path / "test_mod.py").write_text(
        "from mod import both\n\ndef test_b():\n    assert both(True, False) is False\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    result = repair(oracle, "mod.py", [])          # out-of-vocab: refuse
    assert result.refused
    assert (tmp_path / "mod.py").read_bytes() == crlf_src.encode()

    crlf_bug = "def cmp(x, t):\r\n    if x >= t:\r\n        return 1\r\n    return 0\r\n"
    (tmp_path / "mod.py").write_bytes(crlf_bug.encode())
    (tmp_path / "test_mod.py").write_text(
        "from mod import cmp\n\ndef test_c():\n    assert cmp(5, 5) == 0\n")
    result = repair(oracle, "mod.py", [Observation(lineno=2, kinds=[0])])
    assert result.repaired
    got = (tmp_path / "mod.py").read_bytes()
    assert got == crlf_bug.replace("x >= t", "x > t").encode()   # \r\n intact


def test_root_level_module_gets_coverage_localised(tmp_path):
    # major: default --cov=mod.py collected nothing for root-level modules
    (tmp_path / "mod.py").write_text(
        "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
        "        if x >= t:\n            n += 1\n    return n\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import count_above\n\ndef test_c():\n"
        "    assert count_above([1, 5, 5, 9], 5) == 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    packet = build_packet(oracle, "mod.py")        # no coverage_target given
    assert packet is not None and 4 in packet.lines


def test_same_suffix_sibling_package_cannot_shadow(tmp_path):
    # major: mypkg/core.py's coverage used to replace pkg/core.py's entirely
    for name in ("pkg", "mypkg"):
        d = tmp_path / name
        d.mkdir()
        (d / "__init__.py").write_text("")
    (tmp_path / "pkg" / "core.py").write_text(
        "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
        "        if x >= t:\n            n += 1\n    return n\n")
    (tmp_path / "mypkg" / "core.py").write_text("VALUE = 1\n")
    (tmp_path / "test_all.py").write_text(
        "from pkg.core import count_above\nimport mypkg.core\n\n"
        "def test_c():\n    assert count_above([1, 5, 5, 9], 5) == 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    packet = build_packet(oracle, "pkg/core.py", coverage_target=".")
    assert packet is not None and 4 in packet.lines


def test_noop_acts_do_not_count_as_tried(tmp_path):
    # minor: unknown kinds routed to absent acts inflated acts_tried and
    # produced the wrong refusal message
    (tmp_path / "mod.py").write_text("def f():\n    return 2\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    result = repair(oracle, "mod.py", [Observation(lineno=2, kinds=[9, 14])])
    assert result.refused and result.acts_tried == []
    assert "no observation named a kind" in result.reason


def test_harvest_why_keeps_long_failing_test_ids(tmp_path):
    # minor: the 200-char why cap amputated long node ids from the harvest
    # log; 400 keeps the killing test recognisable
    long_name = "test_" + "x" * 250
    (tmp_path / "mod.py").write_text("def f(n):\n    return n + 1\n")
    (tmp_path / "test_mod.py").write_text(
        f"from mod import f\n\ndef {long_name}():\n    assert f(1) == 5\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    result = repair(oracle, "mod.py", [Observation(lineno=2, kinds=[3])])
    assert result.refused and result.tried_log
    why = result.tried_log[0]["why"]
    assert long_name in why and 200 < len(why) <= 400


def test_noncompiling_candidate_skipped_before_any_suite_run(tmp_path):
    # a taught transform may emit garbage: reject it for free — never
    # written, no suite run paid — and harvest it with the compile error
    import re
    from fluidfix import ACTS, KINDS, register
    src = "def f():\n    return 2\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    saved_kinds, saved_acts = dict(KINDS), dict(ACTS)
    try:
        register(4, "garbage", "always proposes a syntax error",
                 re.compile(r"return"), lambda line, o: "    return ((")
        result = repair(oracle, "mod.py", [Observation(lineno=2, kinds=[4])])
    finally:
        KINDS.clear(); KINDS.update(saved_kinds)
        ACTS.clear(); ACTS.update(saved_acts)
    assert result.refused
    assert result.suite_runs == 1            # only the red-suite precondition
    assert result.tried_log[0]["why"].startswith("does not compile:")
    assert (tmp_path / "mod.py").read_text() == src


def test_coverage_runs_leave_no_stray_data_file(tmp_path):
    # minor: pytest-cov's .coverage data file was left behind in the guarded
    # repo after every coverage-bearing localisation run
    (tmp_path / "mod.py").write_text("def f(n):\n    return n + 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f(1) == 5\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    assert build_packet(oracle, "mod.py") is not None
    assert not (tmp_path / ".coverage").exists()
    (tmp_path / ".coverage").write_text("")  # pre-existing file is the user's
    build_packet(oracle, "mod.py")
    assert (tmp_path / ".coverage").exists()


class _StubResponse:
    def __init__(self, text, stop="end_turn"):
        class B:
            type = "text"
        b = B()
        b.text = text
        self.content = [b]
        self.stop_reason = stop
        self.usage = None


class _StubClient:
    def __init__(self, text, stop="end_turn"):
        self._r = _StubResponse(text, stop)
        outer = self

        class M:
            def create(self, **kw):
                return outer._r
        self.messages = M()


def _packet():
    from fluidfix import Packet
    return Packet(defect_file="m.py", failure="E boom",
                  lines=[1], src_lines=["x = 1"], mode="frames")


def test_observer_id_mismatch_raises_not_refuses():
    # minor: wrong echoed ids used to become a silent (fake) refusal
    from fluidfix import ClaudeObserver
    import pytest
    bad = ('{"observations": [{"id": 1, "lineno": 1, "kinds": [], '
           '"literal_value": null, "literal_occurrence": null, "op_occurrence": null}]}')
    o = ClaudeObserver(client=_StubClient(bad), fallbacks=False)
    with pytest.raises(RuntimeError, match="wrong bug ids"):
        o.observe([_packet()])


def test_observer_truncation_raises_diagnosable_error():
    from fluidfix import ClaudeObserver
    import pytest
    o = ClaudeObserver(client=_StubClient('{"observations": [{"id"', stop="max_tokens"),
                       fallbacks=False)
    with pytest.raises(RuntimeError, match="truncated"):
        o.observe([_packet()])


def test_injected_client_needs_no_sdk():
    # minor: fallbacks=False with an injected client must not import anthropic
    from fluidfix import ClaudeObserver
    good = ('{"observations": [{"id": 0, "lineno": 1, "kinds": [0], '
            '"literal_value": null, "literal_occurrence": null, "op_occurrence": null}]}')
    o = ClaudeObserver(client=_StubClient(good), fallbacks=False)
    assert o.observe([_packet()])[0][0].kinds == [0]


def test_teach_a_new_class_from_one_registration(tmp_path):
    # the product claim: a class fluidfix refuses today is repairable the
    # moment you hand it the class — one registration, router untouched
    import re
    from fluidfix import KINDS, ACTS, register
    src = "def both(a, b):\n    return bool(a or b)\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import both\n\ndef test_b():\n    assert both(True, False) is False\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)

    packet = build_packet(oracle, "mod.py")
    assert repair(oracle, "mod.py",
                  MechanicalObserver().observe([packet])[0]).refused

    saved_kinds, saved_acts = dict(KINDS), dict(ACTS)
    try:
        def flip_andor(line, o):
            if " or " in line:
                return line.replace(" or ", " and ", 1)
            if " and " in line:
                return line.replace(" and ", " or ", 1)
            return line
        code = register(4, "logic-flip",
                        'an "and" that should be "or", or vice versa',
                        re.compile(r"\b(?:and|or)\b"), flip_andor)
        assert code == 9                    # (4 + 5) mod 16 — inferred, not chosen
        result = repair(oracle, "mod.py",
                        MechanicalObserver().observe([packet])[0])
        assert result.repaired
        assert result.new_line.strip() == "return bool(a and b)"
    finally:
        KINDS.clear(); KINDS.update(saved_kinds)
        ACTS.clear(); ACTS.update(saved_acts)
