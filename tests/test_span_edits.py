# SPDX-License-Identifier: AGPL-3.0-or-later
"""v0.7: span edits (engine law CHANGE_GRANULARITY, actuated) and the
per-candidate failure log (engine law HARVEST_COUNTEREXAMPLE, actuated).

A taught transform may return SpanEdit(start, end, text): one candidate
replacing several existing lines atomically. Every contract carries over —
suite-adjudicated, byte-exact rollback, AMB refusal, anchor safety — and
every rejected candidate is logged WITH the failing test that rejected it.
"""
import json
import re
import sys

import pytest

from fluidfix import (ACTS, KINDS, MechanicalObserver, Oracle, SpanEdit,
                      guard_once, repair)
from fluidfix.acts import register
from fluidfix.guard import write_refusal
from fluidfix.localize import build_packet


@pytest.fixture()
def clean_registry():
    saved = dict(KINDS), dict(ACTS)
    yield
    KINDS.clear(); KINDS.update(saved[0])
    ACTS.clear(); ACTS.update(saved[1])


def _scale_span_class():
    # taught from ONE perfect example: two lines wrong TOGETHER
    #   a = x * 3   ->   a = x * 2
    #   b = a + 5   ->   b = a + 7
    def fix(line, o):
        m = re.match(r"^(\s*)a = (\w+) \* \d+$", line)
        if not m:
            return [line]
        ind, v = m.groups()
        return [SpanEdit(o.lineno, o.lineno + 1,
                         f"{ind}a = {v} * 2\n{ind}b = a + 7")]
    register(4, "scale-pair", "the scale pair drifted together",
             re.compile(r"a = \w+ \* \d+"), fix)


def test_span_fixes_two_coordinated_wrong_lines(tmp_path, clean_registry):
    # THE motivating case — pinned as a refusal for single-line classes in
    # test_two_coordinated_wrong_lines_refuse; a span class repairs it.
    _scale_span_class()
    (tmp_path / "mod.py").write_text(
        "def scale(x):\n    a = x * 3\n    b = a + 5\n    return b\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import scale\n\ndef test_s():\n"
        "    assert scale(1) == 9\n    assert scale(2) == 11\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert (tmp_path / "mod.py").read_text() == \
        "def scale(x):\n    a = x * 2\n    b = a + 7\n    return b\n"


def test_span_leaves_no_dead_code(tmp_path, clean_registry):
    # the shadowing hazard, closed: a span rewrites BOTH lines — no
    # unreachable old line survives behind a new return
    def fix(line, o):
        m = re.match(r"^(\s*)r = (\w+) \* [\d.]+$", line)
        if not m:
            return [line]
        ind, v = m.groups()
        return [SpanEdit(o.lineno, o.lineno + 1,
                         f"{ind}r = {v} * 0.18\n{ind}return r")]
    register(4, "rate-block", "wrong rate; fix is the whole block",
             re.compile(r"r = \w+ \* [\d.]+"), fix)
    (tmp_path / "mod.py").write_text(
        "def tax(p):\n    r = p * 0.5\n    return r + 1\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import tax\n\ndef test_t():\n    assert tax(100) == 18.0\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    body = (tmp_path / "mod.py").read_text()
    assert body == "def tax(p):\n    r = p * 0.18\n    return r\n"
    assert "r + 1" not in body                       # dead line GONE


def test_span_rejection_rolls_back_byte_exact_crlf(tmp_path, clean_registry):
    # a failing span candidate must leave the tree byte-identical — pinned
    # on a CRLF file where byte-exactness is easiest to lose
    def fix(line, o):
        return [SpanEdit(o.lineno, o.lineno + 1,
                         "    a = x * 9\n    b = a + 9")]
    register(4, "bad-span", "a span candidate the suite rejects",
             re.compile(r"a = \w+ \* \d+"), fix)
    src = "def scale(x):\r\n    a = x * 3\r\n    b = a + 5\r\n    return b\r\n"
    (tmp_path / "mod.py").write_bytes(src.encode())
    (tmp_path / "test_mod.py").write_text(
        "from mod import scale\n\ndef test_s():\n    assert scale(1) == 9\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert (tmp_path / "mod.py").read_bytes() == src.encode()   # byte-exact


def test_span_bounds_and_anchor_safety(tmp_path, clean_registry):
    # out-of-file spans and spans not containing the observed line are
    # skipped without a write; a later good candidate still repairs
    def fix(line, o):
        m = re.match(r"^(\s*)a = (\w+) \* \d+$", line)
        if not m:
            return [line]
        ind, v = m.groups()
        return [SpanEdit(0, 99, "nonsense"),           # out of bounds
                SpanEdit(o.lineno + 5, o.lineno + 9, "far away"),  # no anchor
                SpanEdit(o.lineno, o.lineno + 1,
                         f"{ind}a = {v} * 2\n{ind}b = a + 7")]
    register(4, "guarded-span", "span with bad candidates first",
             re.compile(r"a = \w+ \* \d+"), fix)
    (tmp_path / "mod.py").write_text(
        "def scale(x):\n    a = x * 3\n    b = a + 5\n    return b\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import scale\n\ndef test_s():\n    assert scale(1) == 9\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert "a = x * 2" in (tmp_path / "mod.py").read_text()


def test_two_green_spans_refuse_ambiguous(tmp_path, clean_registry):
    # AMB carries over to spans: two DIFFERENT span candidates that both
    # green a weak suite refuse with the pinning-test ask, tree untouched
    def fix(line, o):
        m = re.match(r"^(\s*)K = \d+$", line)
        if not m:
            return [line]
        ind = m.group(1)
        return [SpanEdit(o.lineno, o.lineno + 1, f"{ind}K = 1\n{ind}J = 1"),
                SpanEdit(o.lineno, o.lineno + 1, f"{ind}K = 2\n{ind}J = 1")]
    register(4, "amb-span", "two suite-indistinguishable span candidates",
             re.compile(r"K = \d+"), fix)
    src = "K = 0\nJ = 0\n\ndef f():\n    return K + J\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() >= 2\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert "AMBIGUOUS" in report.hint and "pinning test" in report.hint
    assert (tmp_path / "mod.py").read_text() == src


def test_refusal_logs_why_each_candidate_failed(tmp_path):
    # HARVEST_COUNTEREXAMPLE actuated: the refusal report names every
    # rejected candidate WITH the failing test that rejected it
    (tmp_path / "mod.py").write_text(
        "def cmp(x, t):\n    if x > t:\n        return 1\n    return 0\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import cmp\n\ndef test_c():\n"
        "    assert cmp(5, 5) == 7\n")            # unsatisfiable: refusal
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert report.attempts                          # something was tried
    entry = report.attempts[0]
    assert entry["at"].startswith("mod.py:")
    assert "test_c" in entry["why"]                 # the killing test, named
    assert "rejected" in report.summary()
    path = write_refusal(str(tmp_path), report)
    data = json.load(open(path))
    assert data["rejected_candidates"] == report.attempts[:200]


def test_global_budget_is_an_honest_stop(tmp_path, clean_registry):
    # --budget expiry anywhere is an honest refusal: tree untouched, the
    # hint names the budget. (AMB-proof atomicity is separately pinned in
    # test_deadline_never_ships_unproven_ambiguity.)
    def slow_class(line, o):
        return [f"K = {n}" for n in range(2, 30)]     # a grind, all red
    register(4, "grind", "many wrong candidates",
             re.compile(r"K = "), slow_class)
    src = "K = 0\n\ndef f():\n    return K\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 99\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver(), budget=3)
    assert report.status == "refused"
    assert (tmp_path / "mod.py").read_text() == src
    # bounded well under the unbounded grind (28 candidates x ~1s suite)
    assert report.seconds < 30


def test_budget_hands_first_pass_over_to_escalation(tmp_path, clean_registry):
    # the measured locales anatomy, miniature: the bug is OUTSIDE the
    # first-pass packet sample, and a slow taught class makes the first
    # pass grind. With --budget the first pass is cut at half and the
    # escalation stage (full sight) repairs; correctness must not depend
    # on the first pass finishing its grind.
    import itertools
    names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
    filler = [f"f_{n} = True" for n in names]
    fn = ["", "def tier(v, limit):", "    if v > limit:",
          "        return 1", "    return 0", ""]
    (tmp_path / "test_mod.py").write_text(
        "from mod import tier\n\ndef test_t():\n"
        "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    for pad in range(6):
        body = filler[:400 + pad] + fn + filler[400 + pad:]
        bug_lineno = (400 + pad) + 3
        (tmp_path / "mod.py").write_text("\n".join(body) + "\n")
        pk = build_packet(oracle, "mod.py")
        if pk is not None and pk.truncated and bug_lineno not in pk.lines:
            break
    else:
        pytest.skip("could not place the bug outside the first-pass sample")
    report = guard_once(oracle, MechanicalObserver(), budget=300)
    assert report.status == "repaired"
    assert report.result.new_line.strip() == "if v >= limit:"
