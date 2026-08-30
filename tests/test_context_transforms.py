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
