# SPDX-License-Identifier: AGPL-3.0-or-later
"""THE LAW DOES NOT MAKE REPAIRS. IT RULES ON SITUATIONS.

Every defect this project has found — and it publishes them — has lived in
the code that MEASURES a situation or APPLIES an act. Not once in the ruling
itself. This file audits that claim against every incident on record, so the
claim stays checkable rather than becoming folklore.

The distinction matters commercially and technically. "fluidfix never makes a
wrong repair" is false: a flaky oracle produced `return b - a` for
`return a + b` in 14% of searches. "The law never ruled wrongly" is true, and
so is what follows from it — correctness is bounded by the quality of the
observation, which is a property a team can inspect and improve.
"""
from fluidfix.engine import decide, situation

# Each incident: what fluidfix observed, what the law ruled, and WHERE the
# defect lived — one of OBSERVATION (the situation was measured wrong),
# ACTUATION (the act was applied wrong), MESSAGE (the report described it
# wrong), or RULING (the law itself). The claim under test is that RULING
# has never once been the answer.
OBSERVATION, ACTUATION, MESSAGE, RULING, NONE = (
    "observation", "actuation", "message", "ruling", "none")

INCIDENTS = [
    ("harness edited to `return 0` (oracle gaming)",
     dict(BUILT=True), "SHIP", OBSERVATION,
     "check() trusted an exit code while the output still said 'test failed'"),
    ("flaky suite accepted `return b - a`",
     dict(BUILT=True), "SHIP", OBSERVATION,
     "BUILT set from ONE run of a suite that does not hold still"),
    ("two candidates both pass",
     dict(BUILT=True, AMB=True), "ADD_STATE", NONE,
     "this ruling is what PREVENTS a coin-flip repair"),
    ("budget ran out mid-search",
     dict(CAPPED=True), "RAISE_BUDGET", MESSAGE,
     "the refusal blamed a search limit when nothing pointed anywhere"),
    ("every candidate rejected",
     dict(REFUTED=True), "HARVEST_COUNTEREXAMPLE", NONE, ""),
    ("pytest-cov missing, coverage blind",
     dict(UNREAD=True), "ADD_MATERIAL", NONE, ""),
    ("green once, red on re-check",
     dict(HIDDEN=True), "CHANGE_GRANULARITY", OBSERVATION,
     "the lane was never measured, so the situation never reached the law"),
    ("rollback lost when the process was killed",
     dict(), None, ACTUATION,
     "no law involved — the act was applied without a durable journal"),
    ("stale binary made every candidate look red",
     dict(REFUTED=True), "HARVEST_COUNTEREXAMPLE", OBSERVATION,
     "the suite that ran was not the code on disk"),
]


def test_the_law_ruled_correctly_on_every_incident_on_record():
    wrong = [(name, decide(situation(**obs)), expect)
             for name, obs, expect, _where, _note in INCIDENTS
             if expect is not None and decide(situation(**obs)) != expect]
    assert wrong == [], f"the law ruled wrongly: {wrong}"


def test_no_defect_has_ever_lived_in_the_ruling():
    """THE claim. If a future incident traces to the RULING, this fails —
    and that would be the first time in the project's history."""
    in_ruling = [n for n, _o, _e, where, _note in INCIDENTS if where == RULING]
    assert in_ruling == [], f"a defect lived in the ruling: {in_ruling}"


def test_the_audit_carries_real_incidents_not_only_clean_cases():
    real = [n for n, _o, _e, where, _note in INCIDENTS if where != NONE]
    assert len(real) >= 5, "the audit must record the failures, not just the wins"


def test_ship_is_not_a_veto_and_amb_is_the_brake():
    """BUILT alone ships. Adding AMB — two candidates the suite cannot tell
    apart — changes the ruling to refuse. The brake is in the law."""
    assert decide(situation(BUILT=True)) == "SHIP"
    assert decide(situation(BUILT=True, AMB=True)) == "ADD_STATE"
