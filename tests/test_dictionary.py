# SPDX-License-Identifier: AGPL-3.0-or-later
"""Repo fault-class dictionaries: taught once, loaded by the CLI, versioned."""
import re
import sys

from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, guard_once
from fluidfix.acts import load_dictionary

RULES = '''\
register(4, "missing-get-default",
         'a .get(key) with no default, letting None poison arithmetic',
         re.compile(r"\\.get\\((\\"[^\\"]+\\"|'[^']+')\\)"),
         lambda line, o: re.sub(r"\\.get\\((\\"[^\\"]+\\"|'[^']+')\\)",
                                r".get(\\1, 0)", line))
'''


def test_dictionary_teaches_a_class_the_cli_can_use(tmp_path):
    (tmp_path / "company_rules.py").write_text(RULES)
    (tmp_path / "payroll.py").write_text(
        'def total_comp(rows):\n    total = 0\n    for r in rows:\n'
        '        total += r["salary"] + r.get("bonus")\n    return total\n')
    (tmp_path / "test_payroll.py").write_text(
        'from payroll import total_comp\n\ndef test_t():\n'
        '    assert total_comp([{"salary": 100, "bonus": 10}, {"salary": 200}]) == 310\n')
    saved_kinds, saved_acts = dict(KINDS), dict(ACTS)
    try:
        n = load_dictionary(str(tmp_path / "company_rules.py"))
        assert n == 1 and 4 in KINDS
        report = guard_once(Oracle(str(tmp_path), python=sys.executable),
                            MechanicalObserver())
        assert report.status == "repaired"
        assert '.get("bonus", 0)' in (tmp_path / "payroll.py").read_text()
    finally:
        KINDS.clear(); KINDS.update(saved_kinds)
        ACTS.clear(); ACTS.update(saved_acts)
