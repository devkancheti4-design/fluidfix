# SPDX-License-Identifier: AGPL-3.0-or-later
"""v0.3: values that live in the repo are searchable.

A taught transform may return a candidate SET built from repo context
(obs.file / obs.root / obs.all_lines); the suite adjudicates each candidate
and refusal still happens when none passes — the no-wrong-repairs contract
is unchanged, precision now bounded by suite strength."""
import ast
import re
import sys

import pytest

from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, build_packet, repair
from fluidfix.acts import register


def attrs_in_repo(obs):
    """Every attribute name used anywhere in the defect file — the value
    space for a wrong-attribute bug, enumerated from the repo itself."""
    try:
        tree = ast.parse("\n".join(obs.all_lines or []))
    except SyntaxError:
        return []
    return sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)})


def teach_wrong_attribute():
    register(4, "wrong-attribute",
             "a returned attribute that is the wrong one; the right name "
             "exists elsewhere in this file",
             re.compile(r"return \w+\.\w+"),
             lambda line, o: [re.sub(r"(return \w+)\.\w+", rf"\1.{a}", line)
                              for a in attrs_in_repo(o)])


@pytest.fixture()
def clean_registry():
    saved = dict(KINDS), dict(ACTS)
    yield
    KINDS.clear(); KINDS.update(saved[0])
    ACTS.clear(); ACTS.update(saved[1])


def _run(tmp_path, module_src, test_src):
    (tmp_path / "mod.py").write_text(module_src)
    (tmp_path / "test_mod.py").write_text(test_src)
    oracle = Oracle(str(tmp_path), python=sys.executable)
    packet = build_packet(oracle, "mod.py", coverage_target="mod")
    assert packet is not None
    obs = MechanicalObserver().observe([packet])[0]
    return repair(oracle, "mod.py", obs)


def test_value_found_in_repo_case1(tmp_path, clean_registry):
    # the failed held-out from the generalization experiment: should be .id
    teach_wrong_attribute()
    r = _run(tmp_path,
             "class U:\n    def __init__(s):\n        s.id = 7\n        s.name = 'a'\n"
             "def f(u):\n    return u.name\n",
             "from mod import U, f\n\ndef test():\n    assert f(U()) == 7\n")
    assert r.repaired and r.new_line.strip() == "return u.id"


def test_value_found_in_repo_case2(tmp_path, clean_registry):
    # second held-out: should be .total — a DIFFERENT value, same one class
    teach_wrong_attribute()
    r = _run(tmp_path,
             "class R:\n    def __init__(s):\n        s.total = 99\n        s.count = 1\n"
             "def g(r):\n    return r.count\n",
             "from mod import R, g\n\ndef test():\n    assert g(R()) == 99\n")
    assert r.repaired and r.new_line.strip() == "return r.total"


def test_value_not_in_repo_still_refuses(tmp_path, clean_registry):
    # the correct answer is a computation, not any attribute in the file:
    # every enumerated candidate fails the suite -> honest refusal, tree intact
    teach_wrong_attribute()
    src = ("class C:\n    def __init__(s):\n        s.a = 2\n        s.b = 3\n"
           "def h(c):\n    return c.a\n")
    r = _run(tmp_path, src,
             "from mod import C, h\n\ndef test():\n    assert h(C()) == 6\n")
    assert r.refused and not r.repaired
    assert (tmp_path / "mod.py").read_text() == src


def test_candidate_sets_are_bounded():
    from fluidfix.acts import candidates as _cands, Observation
    register(5, "flood", "candidate flood guard", re.compile("x"),
             lambda line, o: [f"y = {i}" for i in range(500)])
    try:
        out = _cands("x = 1", (5 + 5) % 16, Observation(lineno=1))
        assert len(out) <= 32
    finally:
        KINDS.pop(5, None); ACTS.pop(10, None)


def test_multiline_logic_fix_from_one_example(tmp_path, clean_registry):
    # A taught class may rewrite its ONE defective line into a corrected
    # BLOCK — new control flow, not a token flip. Taught from one worked
    # example (a zero-guard incident) and generalising to a second member
    # with different names, zero new examples. Live-proven 2026-08-31;
    # pinned here so the multi-line claim is CI-enforced.
    def zero_guard(line, o):
        m = re.match(r"^(\s*)return (\w+) / (\w+)$", line)
        if not m:
            return [line]
        ind, a, b = m.groups()
        return [f"{ind}if {b} == 0:\n{ind}    return 0\n{ind}return {a} / {b}"]

    register(4, "missing-zero-guard",
             "a bare x / y return with no guard for y == 0",
             re.compile(r"return \w+ / \w+"), zero_guard)
    (tmp_path / "mod.py").write_text(
        "def safe_div(a, b):\n    return a / b\n\n"
        "def rate(events, seconds):\n    return events / seconds\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import safe_div, rate\n\ndef test_div():\n"
        "    assert safe_div(6, 2) == 3\n    assert safe_div(5, 0) == 0\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    from fluidfix import guard_once
    r1 = guard_once(oracle, MechanicalObserver())
    assert r1.status == "repaired"
    body = (tmp_path / "mod.py").read_text()
    assert "    if b == 0:\n        return 0\n    return a / b" in body

    # second member of the class, same dictionary, no new example
    (tmp_path / "test_mod.py").write_text(
        "from mod import safe_div, rate\n\ndef test_div():\n"
        "    assert safe_div(5, 0) == 0\n\ndef test_rate():\n"
        "    assert rate(10, 0) == 0\n")
    r2 = guard_once(oracle, MechanicalObserver())
    assert r2.status == "repaired"
    assert "    if seconds == 0:\n        return 0\n    return events / seconds" \
        in (tmp_path / "mod.py").read_text()


def test_whole_algorithm_fix_from_one_example(tmp_path, clean_registry):
    # "It fixes what it was shown": ONE perfect example teaches a class
    # whose fix is a complete 5-line algorithm, not a token — and the class
    # covers every member (second function, different variable name, zero
    # new examples). Live-proven 2026-09-01; pinned so the claim is
    # CI-enforced.
    def mean_to_median(line, o):
        m = re.match(r"^(\s*)return sum\((\w+)\) / len\(\2\)$", line)
        if not m:
            return [line]
        ind, v = m.groups()
        return [(f"{ind}ys = sorted({v})\n{ind}n = len(ys)\n"
                 f"{ind}if n % 2:\n{ind}    return ys[n // 2]\n"
                 f"{ind}return (ys[n // 2 - 1] + ys[n // 2]) / 2")]

    register(4, "mean-where-median",
             "a mean computed where the tests demand a median",
             re.compile(r"return sum\(\w+\) / len\(\w+\)"), mean_to_median)
    (tmp_path / "mod.py").write_text(
        "def middle_price(xs):\n    return sum(xs) / len(xs)\n\n"
        "def middle_latency(vals):\n    return sum(vals) / len(vals)\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import middle_price\n\ndef test_m():\n"
        "    assert middle_price([1, 100, 3]) == 3\n"
        "    assert middle_price([1, 2, 100, 4]) == 3\n")
    from fluidfix import guard_once
    oracle = Oracle(str(tmp_path), python=sys.executable)
    r1 = guard_once(oracle, MechanicalObserver())
    assert r1.status == "repaired"
    assert "ys = sorted(xs)" in (tmp_path / "mod.py").read_text()

    (tmp_path / "test_mod.py").write_text(
        "from mod import middle_price, middle_latency\n\ndef test_m():\n"
        "    assert middle_price([1, 100, 3]) == 3\n\n"
        "def test_l():\n    assert middle_latency([5, 900, 7, 9]) == 8\n")
    r2 = guard_once(oracle, MechanicalObserver())
    assert r2.status == "repaired"
    assert "ys = sorted(vals)" in (tmp_path / "mod.py").read_text()


def test_two_coordinated_wrong_lines_refuse(tmp_path, clean_registry):
    # The honest boundary, pinned: when TWO existing lines are wrong
    # together (neither alone greens the suite), single-line candidates
    # cannot land and the guard refuses with the tree byte-identical —
    # it never half-fixes and never guesses.
    def lit_swap(line, o):
        out = []
        for m in re.finditer(r"(?<![\w.])(\d+)(?![\w.])", line):
            for d in (1, 2, -1, -2):
                v = int(m.group(1)) + d
                if v >= 0:
                    out.append(line[:m.start()] + str(v) + line[m.end():])
        return out or [line]

    register(4, "lit-neighborhood", "an integer literal off by 1-2",
             re.compile(r"(?<![\w.])\d+(?![\w.])"), lit_swap)
    src = "def scale(x):\n    a = x * 3\n    b = a + 5\n    return b\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import scale\n\ndef test_s():\n"
        "    assert scale(1) == 9\n    assert scale(2) == 11\n")
    from fluidfix import guard_once
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert (tmp_path / "mod.py").read_text() == src
