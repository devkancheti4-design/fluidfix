# SPDX-License-Identifier: AGPL-3.0-or-later
"""docs/TEACHING.md and examples/company_rules.py, executed. The walkthrough's
dictionary is extracted from the doc verbatim (the doc IS the fixture) and the
example dictionary's three classes each repair a live project end-to-end; if
either file drifts from reality, this goes red."""
import sys
from pathlib import Path

import pytest

from fluidfix import (ACTS, KINDS, MechanicalObserver, Observation, Oracle,
                      guard_once)
from fluidfix.acts import act_for, candidates, load_dictionary

ROOT = Path(__file__).parent.parent
EXAMPLE = ROOT / "examples" / "company_rules.py"
_DOC = (ROOT / "docs" / "TEACHING.md").read_text()
WALKTHROUGH = "# company_rules.py" + \
    _DOC.split("```python\n# company_rules.py")[1].split("```")[0]
# ^ the doc's own walkthrough dictionary, verbatim — the doc IS the fixture


@pytest.fixture()
def clean_registry():
    saved = dict(KINDS), dict(ACTS)
    yield
    KINDS.clear(); KINDS.update(saved[0])
    ACTS.clear(); ACTS.update(saved[1])


def _oracle(tmp_path, mod, test):
    (tmp_path / "mod.py").write_text(mod)
    (tmp_path / "test_mod.py").write_text(test)
    return Oracle(str(tmp_path), python=sys.executable)


def test_example_dictionary_registers_three_classes(clean_registry):
    assert load_dictionary(str(EXAMPLE)) == 3
    assert {4, 5, 6} <= set(KINDS)
    for kind in (4, 5, 6):
        assert act_for(kind) in ACTS            # each class got an applier
        assert KINDS[kind][0] in _DOC           # doc and example stay in sync


def test_walkthrough_dictionary_repairs_the_incident(tmp_path, clean_registry):
    (tmp_path / "company_rules.py").write_text(WALKTHROUGH)
    assert load_dictionary(str(tmp_path / "company_rules.py")) == 1
    # the doc's 0:15 transform unit check, verbatim
    assert candidates("    fields = row.split()", act_for(4),
                      Observation(lineno=1)) == ['    fields = row.split(",")']
    oracle = _oracle(
        tmp_path,
        "def parse_row(row):\n    fields = row.split()\n    return fields\n",
        'from mod import parse_row\n\ndef test_r():\n'
        '    assert parse_row("widget,4") == ["widget", "4"]\n')
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert 'row.split(",")' in (tmp_path / "mod.py").read_text()


def test_example_rule_class_missing_get_default(tmp_path, clean_registry):
    load_dictionary(str(EXAMPLE))
    oracle = _oracle(
        tmp_path,
        'def total_due(invoices):\n    due = 0\n    for inv in invoices:\n'
        '        due += inv["amount"] + inv.get("tax")\n    return due\n',
        'from mod import total_due\n\ndef test_d():\n'
        '    assert total_due([{"amount": 50, "tax": 5}, {"amount": 20}]) == 75\n')
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert '.get("tax", 0)' in (tmp_path / "mod.py").read_text()


def test_example_repo_mined_class_wrong_attribute(tmp_path, clean_registry):
    load_dictionary(str(EXAMPLE))
    oracle = _oracle(
        tmp_path,
        "class User:\n    def __init__(s):\n        s.id = 7\n        s.name = 'a'\n"
        "def lookup_key(u):\n    return u.name\n",
        "from mod import User, lookup_key\n\ndef test_k():\n"
        "    assert lookup_key(User()) == 7\n")
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert "return u.id" in (tmp_path / "mod.py").read_text()


def test_example_span_class_round_before_accumulate(tmp_path, clean_registry):
    load_dictionary(str(EXAMPLE))
    oracle = _oracle(
        tmp_path,
        "def checkout(subtotal, surcharge):\n"
        "    total = round(subtotal)\n"
        "    total = total + surcharge\n"
        "    return total\n",
        "from mod import checkout\n\ndef test_c():\n"
        "    assert checkout(99.6, 0.7) == 100\n")
    report = guard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert ("    total = subtotal + surcharge\n    total = round(total)\n"
            in (tmp_path / "mod.py").read_text())
