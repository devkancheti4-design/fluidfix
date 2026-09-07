# SPDX-License-Identifier: AGPL-3.0-or-later
"""EVERY exit from a search carries a ruling.

Before 0.15.0 a refusal could not carry one. `loop._rule` returned None when
nothing went green and the caller printed a hardcoded string, so the situations
the law has lanes for — REFUTED, CAPPED, UNREAD — were decided by code.

Measured 2026-09-07, before this change:
  * five cguard runs on cglm: five refusals, ZERO engine-law rulings;
  * five cguard runs on Box2D: 403 candidates, 2,233 kernel invocations, ONE
    ruling;
  * on the Python path, three refusals in ten reached the law as an EMPTY byte,
    which the law can only answer SHIP, because nothing measured "the taught
    vocabulary named nothing".

And the defect four separate agents confirmed independently: a pass holding a
suite-passing candidate reported "every generated candidate was rejected by the
suite", because guard.py measured REFUTED as "candidates were generated" while
engine.py:24-25 defines it as "candidates were generated AND the suite rejected
EVERY ONE" — and guard.py never read `result.greens` at all.
"""
import sys, time
import pytest

from fluidfix.engine import decide, situation
from fluidfix.loop import RepairResult


def test_refuted_needs_both_halves_of_its_definition():
    """The byte that shipped the false claim, and the byte that was owed."""
    # what guard.py used to build: "candidates were generated"
    assert decide(situation(CAPPED=False, REFUTED=True)) == "HARVEST_COUNTEREXAMPLE"
    # what the run actually was: a green in hand, the search cut short
    assert decide(situation(BUILT=True, CAPPED=True)) == "RAISE_BUDGET"
    # the two disagree, which is why the mismeasurement changed the outcome
    assert decide(situation(CAPPED=True, REFUTED=False)) == "RAISE_BUDGET"


def test_result_carries_the_ruling_and_the_cap():
    """guard.py cannot measure honestly unless repair() tells it these."""
    r = RepairResult(repaired=False, refused=True)
    assert hasattr(r, "ruling") and hasattr(r, "capped") and hasattr(r, "greens")
    assert r.ruling == "" and r.capped is False


@pytest.mark.parametrize("built,amb,capped,refuted,unread,expect", [
    # a green, nothing blocking                       -> ship it
    (True,  False, False, False, False, "SHIP"),
    # a green, but the search was cut short           -> the budget, not a guess
    (True,  False, True,  False, False, "RAISE_BUDGET"),
    # two programs, one input                         -> ask for a pinning test
    (True,  True,  False, False, False, "ADD_STATE"),
    # candidates generated, ALL rejected              -> keep the counterexamples
    (False, False, False, True,  False, "HARVEST_COUNTEREXAMPLE"),
    # cut short before the vocabulary was exhausted   -> the budget
    (False, False, True,  False, False, "RAISE_BUDGET"),
    # the vocabulary named nothing at all             -> bring more material
    (False, False, False, False, True,  "ADD_MATERIAL"),
])
def test_every_byte_the_loop_can_now_build_has_a_ruling(
        built, amb, capped, refuted, unread, expect):
    """These six are the whole constructible vocabulary of `_rule`. Each one is
    a situation that used to end in a hardcoded sentence."""
    assert decide(situation(BUILT=built, AMB=amb, CAPPED=capped,
                            REFUTED=refuted, UNREAD=unread)) == expect


def test_the_empty_byte_is_no_longer_constructible():
    """An observation with no bits set rules SHIP, which is the one answer a
    refusal must never carry. It was reached 3 times in 10 refusals. It is now
    unreachable: no greens and no acts means the vocabulary named nothing
    (UNREAD), or the clock cut the search short (CAPPED)."""
    assert decide(situation()) == "SHIP"          # why it had to be closed
    assert decide(situation(UNREAD=True)) == "ADD_MATERIAL"
    assert decide(situation(CAPPED=True)) == "RAISE_BUDGET"


def _fixture(tmp_path, body, test_body):
    (tmp_path / "mod.py").write_text(body)
    (tmp_path / "test_mod.py").write_text(test_body)
    return tmp_path


def _observe(o, rel="mod.py"):
    from fluidfix.observers import MechanicalObserver
    from fluidfix.guard import build_packet, rank_observations
    _, out = o.failing_output()
    pkt = build_packet(o, rel)
    return rank_observations("\n".join(pkt.src_lines),
                             MechanicalObserver().observe([pkt])[0], out,
                             root=o.root, rel=rel), out


def test_a_cut_short_search_rules_raise_budget_not_a_hardcoded_sentence(tmp_path):
    """The deadline path. It used to print 'wall-clock deadline reached
    mid-search' — true, but not a ruling, and the situation it describes is one
    the law has a lane for."""
    from fluidfix.oracle import Oracle
    from fluidfix.loop import repair
    root = _fixture(tmp_path, "def add(a, b):\n    return a - b\n",
                    "from mod import add\ndef test_add():\n    assert add(2, 3) == 5\n")
    o = Oracle(str(root), python=sys.executable)
    obs, _ = _observe(o)
    res = repair(o, "mod.py", obs, deadline=time.time() - 1)   # already expired
    assert res.repaired is False
    assert res.capped is True
    assert res.ruling == "RAISE_BUDGET", res.ruling
    assert "engine law: CAPPED -> RAISE_BUDGET" in res.reason
    # and it must NOT claim the candidates were rejected: none was ever tried
    assert "rejected" not in res.reason


def test_a_vocabulary_that_names_nothing_rules_add_material(tmp_path):
    """UNREAD is measured from the OBSERVATIONS, not from the clock. A search
    the deadline cut off before its first candidate has read nothing yet — that
    is CAPPED. Only a genuinely silent vocabulary is UNREAD."""
    from fluidfix.oracle import Oracle
    from fluidfix.loop import repair
    from fluidfix.acts import Observation
    root = _fixture(tmp_path, "def f(x):\n    return x\n",
                    "from mod import f\ndef test_f():\n    assert f('a') == 'A'\n")
    o = Oracle(str(root), python=sys.executable)
    res = repair(o, "mod.py", [Observation(lineno=2, kinds=[])])
    assert res.repaired is False
    assert res.ruling == "ADD_MATERIAL", res.ruling
    assert "engine law: UNREAD -> ADD_MATERIAL" in res.reason


# --------------------------------------------------------------------------
# The C and Java guards. Measured 2026-09-07, before this change:
#   * five cguard runs on cglm  -> five refusals, ZERO engine-law rulings;
#   * five cguard runs on Box2D -> 403 candidates, 2,233 kernel invocations,
#     exactly ONE ruling, and `coracle.py` imported no law module at all.
# Both bits the law needs were already in those functions' locals:
# `packet.truncated` IS the CAPPED bit, and a non-empty rejection list with
# nothing green IS REFUTED.
# --------------------------------------------------------------------------
import shutil

HAS_CC = shutil.which("cc") is not None


def test_the_c_and_java_guards_import_the_engine_law():
    """The static fact an agent measured: coracle.py imported no law module,
    so no refusal it produced could carry a ruling, by construction."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "fluidfix"
    for mod in ("coracle.py", "javaoracle.py"):
        text = (src / mod).read_text(encoding="utf-8")
        assert "decide(situation(" in text, f"{mod} never asks the law"


@pytest.mark.skipif(not HAS_CC, reason="no C compiler")
def test_a_c_refusal_carries_a_ruling(tmp_path):
    """A budget too small to finish is CAPPED, and the law rules RAISE_BUDGET.
    It used to print `--budget exhausted (Ns)` and no ruling at all."""
    from fluidfix.observers import MechanicalObserver
    from fluidfix.coracle import cguard_once
    from test_c_adapter import _tiny_project
    o = _tiny_project(tmp_path, "a - b")
    rep = cguard_once(o, MechanicalObserver(), budget=0.001)  # expires at once
    assert rep.status == "refused"
    assert "engine law:" in (rep.hint or ""), rep.hint
    assert "RAISE_BUDGET" in (rep.hint or ""), rep.hint


def test_an_observation_that_names_an_unbuildable_kind_rules_add_material(tmp_path):
    """The case that broke a draft of this change, kept as a pin.

    Kinds 9 and 14 route to no applier, so the observation NAMES something and
    nothing is ever generated. A draft measured UNREAD from the observation
    list, read this as "the vocabulary spoke", and handed the law byte 512 —
    which rules SHIP, with no candidate in hand. UNREAD is therefore measured
    as "nothing was generated to judge, and the clock is not the reason"."""
    from fluidfix.oracle import Oracle
    from fluidfix.loop import repair
    from fluidfix.acts import Observation
    (tmp_path / "mod.py").write_text("def f():\n    return 2\n")
    (tmp_path / "test_mod.py").write_text(
        "from mod import f\n\ndef test_f():\n    assert f() == 1\n")
    o = Oracle(str(tmp_path), python=sys.executable)
    res = repair(o, "mod.py", [Observation(lineno=2, kinds=[9, 14])])
    assert res.refused and res.acts_tried == []
    assert res.ruling == "ADD_MATERIAL", res.ruling
    assert res.capped is False


def test_ship_without_a_green_refuses_instead_of_crashing():
    """Defence for the shape above: SHIP is reachable only through BUILT, and
    BUILT is bool(greens). If a future mismeasurement breaks that, the loop
    must refuse and say why, not raise IndexError."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "src" / "fluidfix" / "loop.py").read_text(encoding="utf-8")
    assert 'if ruling == "SHIP" and not greens:' in src
