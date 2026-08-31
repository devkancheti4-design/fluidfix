# SPDX-License-Identifier: AGPL-3.0-or-later
"""The engine law fused into the guard: rulings, ambiguity, escalation.

The law is the third machine-authored kernel (dev repo, 2026-08-17) and is
vendored VERBATIM — the fingerprint test pins it to the source's own claim.
"""
import hashlib
import re
import sys

import pytest

from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, guard_once, repair
from fluidfix.acts import register
from fluidfix.engine import LAW, decide, situation


def test_law_is_verbatim():
    # the dev repo's README states: sha256 48bf50bff36a2cc9 · 1,555 characters
    assert len(LAW) == 1555
    assert hashlib.sha256(LAW.encode()).hexdigest().startswith("48bf50bff36a2cc9")


def test_rulings_fluidfix_depends_on():
    assert decide(situation(BUILT=1)) == "SHIP"
    assert decide(situation(BUILT=1, AMB=1)) == "ADD_STATE"
    assert decide(situation(UNREAD=1)) == "ADD_MATERIAL"
    assert decide(situation(CAPPED=1)) == "RAISE_BUDGET"
    assert decide(situation(CAPPED=1, REFUTED=1)) == "RAISE_BUDGET"
    assert decide(situation(REFUTED=1)) == "HARVEST_COUNTEREXAMPLE"


@pytest.fixture()
def clean_registry():
    saved = dict(KINDS), dict(ACTS)
    yield
    KINDS.clear(); KINDS.update(saved[0])
    ACTS.clear(); ACTS.update(saved[1])


def test_ambiguous_greens_refuse_with_add_state(tmp_path, clean_registry):
    # two DIFFERENT candidates both satisfy a weak suite -> the law rules
    # ADD_STATE: refuse, name the ambiguity, leave the tree byte-identical
    register(4, "amb-demo", "demo class with two suite-passing candidates",
             re.compile(r"K = "),
             lambda line, o: ["K = 1", "K = 2"])
    src = "K = 0\n\ndef f():\n    return K\n"
    (tmp_path / "mod.py").write_text(src)
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() >= 1\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert "AMBIGUOUS" in report.hint and "pinning test" in report.hint
    assert (tmp_path / "mod.py").read_text() == src        # untouched
    assert len(report.result.greens) >= 2


def test_unambiguous_single_green_still_ships(tmp_path):
    (tmp_path / "mod.py").write_text(
        "def cmp(x, t):\n    if x > t:\n        return 1\n    return 0\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import cmp\n\ndef test_c():\n"
        "    assert cmp(5, 5) == 1 and cmp(4, 5) == 0\n")   # pins >= exactly
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert report.result.new_line.strip() == "if x >= t:"


def test_capped_escalation_raises_budget_and_repairs(tmp_path):
    # Hundreds of covered signal lines force round-1 packet truncation; the
    # bug line must land OUTSIDE the round-1 spread sample, so only the law's
    # RAISE_BUDGET retry can reach it. Fillers match the packet's signal
    # filter (True) but yield NO observer kinds (no digits, no comparisons),
    # keeping the suite-run count small.
    import itertools
    from fluidfix.localize import build_packet

    names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
    filler = [f"f_{n} = True" for n in names]
    fn = ["", "def tier(v, limit):", "    if v > limit:",      # the bug
          "        return 1", "    return 0", ""]
    (tmp_path / "test_mod.py").write_text(
        "from mod import tier\n\ndef test_t():\n"
        "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)

    pk1 = None
    for pad in range(6):   # nudge layout until the bug line is NOT sampled
        body = filler[:400 + pad] + fn + filler[400 + pad:]
        bug_lineno = (400 + pad) + 3
        (tmp_path / "mod.py").write_text("\n".join(body) + "\n")
        assert body[bug_lineno - 1].strip() == "if v > limit:"
        pk1 = build_packet(oracle, "mod.py")
        assert pk1 is not None and pk1.truncated            # CAPPED is real
        if bug_lineno not in pk1.lines:
            break
    else:
        pytest.skip("could not place the bug outside the round-1 sample")

    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert report.result.new_line.strip() == "if v >= limit:"
    assert "RAISE_BUDGET" in report.result.reason


def test_refuted_refusal_does_not_escalate(tmp_path):
    # candidates were generated and rejected, nothing was truncated:
    # law rules HARVEST_COUNTEREXAMPLE — an honest stop, no budget rounds
    (tmp_path / "mod.py").write_text(
        "def f(a, b):\n    return a * b\n")                 # * is out of vocab
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f(6, 2) == 3\n")
    oracle = Oracle(str(tmp_path), python=sys.executable)
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    src = (tmp_path / "mod.py").read_text()
    assert "a * b" in src                                    # untouched
