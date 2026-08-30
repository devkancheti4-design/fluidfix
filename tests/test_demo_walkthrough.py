# SPDX-License-Identifier: AGPL-3.0-or-later
"""docs/DEMO.md, executed. Each test mirrors a numbered step; if the doc's
commands or expected outcomes drift from reality, this file goes red."""
import json
import re
import subprocess
import sys

import pytest

from fluidfix import ACTS, KINDS, MechanicalObserver, Oracle, guard_once
from fluidfix.acts import load_dictionary
from fluidfix.cli import main as cli_main

BILLING = ("def price_after_tax(p, rate):\n"
           "    return p * (1 + rate)\n")
TEST_BILLING = ("from billing import price_after_tax\n\n"
                "def test_tax():\n"
                "    assert price_after_tax(100, 0.1) == 110.00000000000001\n")
INVOICES = ("def total_due(invoices):\n"
            "    due = 0\n"
            "    for inv in invoices:\n"
            '        due += inv["amount"] + inv.get("tax", 0)\n'
            "    return due\n")
TEST_INVOICES = ("from invoices import total_due\n\n"
                 "def test_due():\n"
                 '    assert total_due([{"amount": 50, "tax": 5}, {"amount": 20}]) == 75\n')
from pathlib import Path
_DOC = (Path(__file__).parent.parent / "docs" / "DEMO.md").read_text()
RULES = "# company_rules.py" + _DOC.split("```python\n# company_rules.py")[1].split("```")[0]
# ^ the doc's own dictionary, verbatim — the doc IS the fixture


def _git(d, *args):
    return subprocess.run(["git", "-C", str(d), *args], capture_output=True,
                          text=True, check=False)


@pytest.fixture()
def service(tmp_path):
    (tmp_path / "billing.py").write_text(BILLING)
    (tmp_path / "test_billing.py").write_text(TEST_BILLING)
    (tmp_path / "invoices.py").write_text(INVOICES)
    (tmp_path / "test_invoices.py").write_text(TEST_INVOICES)
    (tmp_path / ".gitignore").write_text(".fluidfix/\n__pycache__/\n.coverage\n.pytest_cache/\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "demo@test")
    _git(tmp_path, "config", "user.name", "demo")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "deploy billing service")
    saved = dict(KINDS), dict(ACTS)
    yield tmp_path
    KINDS.clear(); KINDS.update(saved[0])
    ACTS.clear(); ACTS.update(saved[1])


def test_step1_selfcheck_passes(capsys):
    assert cli_main(["selfcheck"]) == 0
    assert "SELFCHECK PASS" in capsys.readouterr().out


def test_step2_green_suite_untouched(service):
    before = (service / "billing.py").read_bytes()
    assert cli_main(["guard", str(service), "--python", sys.executable]) == 0
    assert (service / "billing.py").read_bytes() == before


def test_step3_guard_repairs_and_commits_without_being_told_the_file(service):
    (service / "billing.py").write_text(BILLING.replace("1 + rate", "1 - rate"))
    _git(service, "commit", "-aqm", "ship pricing v2")
    assert cli_main(["guard", str(service), "--python", sys.executable,
                     "--commit"]) == 0
    assert "1 + rate" in (service / "billing.py").read_text()
    assert "fluidfix: restore billing.py:2" in _git(service, "log", "--oneline").stdout


def test_step4_novel_class_refused_with_signal(service):
    (service / "invoices.py").write_text(INVOICES.replace('.get("tax", 0)', '.get("tax")'))
    _git(service, "commit", "-aqm", "ship invoicing v3")
    broken = (service / "invoices.py").read_bytes()
    assert cli_main(["guard", str(service), "--python", sys.executable,
                     "--commit"]) == 2                       # documented CI exit code
    assert (service / "invoices.py").read_bytes() == broken   # tree untouched
    signal = json.loads((service / ".fluidfix" / "last_refusal.json").read_text())
    assert signal["status"] == "refused"


def test_step5_and_6_dictionary_frees_the_class(service):
    (service / "company_rules.py").write_text(RULES)
    (service / "invoices.py").write_text(INVOICES.replace('.get("tax", 0)', '.get("tax")'))
    _git(service, "commit", "-aqm", "ship invoicing v3")
    assert cli_main(["guard", str(service), "--python", sys.executable,
                     "--commit", "--dictionary", str(service / "company_rules.py")]) == 0
    assert '.get("tax", 0)' in (service / "invoices.py").read_text()
    # a DIFFERENT member of the class, in a different file, is also free
    (service / "metrics.py").write_text(
        "def p_total(samples):\n    acc = 0\n    for s in samples:\n"
        '        acc += s.get("ms")\n    return acc\n')
    (service / "test_metrics.py").write_text(
        "from metrics import p_total\n\ndef test_m():\n"
        '    assert p_total([{"ms": 12}, {}]) == 12\n')
    _git(service, "add", "-A")
    _git(service, "commit", "-qm", "ship metrics v2")
    assert cli_main(["guard", str(service), "--python", sys.executable,
                     "--commit", "--dictionary", str(service / "company_rules.py")]) == 0
    assert '.get("ms", 0)' in (service / "metrics.py").read_text()
    log = _git(service, "log", "--oneline").stdout
    assert "fluidfix: restore invoices.py" in log
    assert "fluidfix: restore metrics.py" in log


def test_step7_library_api(service):
    (service / "company_rules.py").write_text(RULES)
    (service / "invoices.py").write_text(INVOICES.replace('.get("tax", 0)', '.get("tax")'))
    assert load_dictionary(str(service / "company_rules.py")) == 1
    report = guard_once(Oracle(str(service), python=sys.executable),
                        MechanicalObserver())
    assert report.status == "repaired"
    assert "repaired" in report.summary()
