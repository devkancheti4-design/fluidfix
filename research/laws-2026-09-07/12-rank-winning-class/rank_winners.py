#!/usr/bin/env python
"""12-rank-winning-class: on the Python fixtures in tests/, log the rank the
ranking law (src/fluidfix/rank.py) gives each candidate line/class and which
class actually repairs; distribution of "rank of the winner".

Nothing in src/ is edited. The body is instrumented by monkeypatching three
module attributes for the duration of one guard_once() call:

  fluidfix.rank.rank            -> record (byte, priority) per observation
  fluidfix.loop.candidates      -> record (line, kinds, act, candidate set)
  fluidfix.oracle.Oracle.check  -> record what was on disk at each suite run

Fixtures are copied VERBATIM from tests/ and docs/ (source noted per fixture).
No git repositories are created (brief: no state-changing git), so the
RECENT lane is unreachable in these runs — see REPORT.md.

Usage:
  nice -n 15 timeout 300 .venv/bin/python rank_winners.py [--only NAME,...] [--group G]
Writes runs/<name>/ (the throwaway project) and log/<name>.json.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import sys
import textwrap
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLUIDFIX = HERE.parent.parent.parent
sys.path.insert(0, str(FLUIDFIX / "src"))

import fluidfix.guard as G            # noqa: E402
import fluidfix.loop as L             # noqa: E402
import fluidfix.rank as R             # noqa: E402
from fluidfix import MechanicalObserver, Oracle, guard_once   # noqa: E402
from fluidfix.acts import ACTS, KINDS, act_for, load_dictionary   # noqa: E402
from fluidfix.rank import BITS       # noqa: E402

RUNS = HERE / "runs"
LOG = HERE / "log"

# --------------------------------------------------------------- fixtures --
# Each: name, src (where in tests/ it comes from), group, files {rel: text},
# dictionary (text of a rules file for load_dictionary, or None),
# expect ("repaired"/"refused"), guard_kwargs.

COUNT_ABOVE = ("def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
               "        if x >= t:\n            n += 1\n    return n\n")
COUNT_ABOVE_TEST = ("from mod import count_above\n\ndef test_c():\n"
                    "    assert count_above([1, 5, 5, 9], 5) == 1\n")

GET_DEFAULT_DICT = '''\
register(4, "missing-get-default",
         'a .get(key) with no default, letting None poison arithmetic',
         re.compile(r"\\.get\\((\\"[^\\"]+\\"|'[^']+')\\)"),
         lambda line, o: re.sub(r"\\.get\\((\\"[^\\"]+\\"|'[^']+')\\)",
                                r".get(\\1, 0)", line))
'''

WRONG_ATTR_DICT = '''\
import ast
def attrs_in_repo(obs):
    try:
        tree = ast.parse("\\n".join(obs.all_lines or []))
    except SyntaxError:
        return []
    return sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)})
register(4, "wrong-attribute",
         "a returned attribute that is the wrong one; the right name "
         "exists elsewhere in this file",
         re.compile(r"return \\w+\\.\\w+"),
         lambda line, o: [re.sub(r"(return \\w+)\\.\\w+", rf"\\1.{a}", line)
                          for a in attrs_in_repo(o)])
'''

SCALE_SPAN_DICT = '''\
def fix(line, o):
    m = re.match(r"^(\\s*)a = (\\w+) \\* \\d+$", line)
    if not m:
        return [line]
    ind, v = m.groups()
    return [SpanEdit(o.lineno, o.lineno + 1,
                     f"{ind}a = {v} * 2\\n{ind}b = a + 7")]
register(4, "scale-pair", "the scale pair drifted together",
         re.compile(r"a = \\w+ \\* \\d+"), fix)
'''

RATE_SPAN_DICT = '''\
def fix(line, o):
    m = re.match(r"^(\\s*)r = (\\w+) \\* [\\d.]+$", line)
    if not m:
        return [line]
    ind, v = m.groups()
    return [SpanEdit(o.lineno, o.lineno + 1,
                     f"{ind}r = {v} * 0.18\\n{ind}return r")]
register(4, "rate-block", "wrong rate; fix is the whole block",
         re.compile(r"r = \\w+ \\* [\\d.]+"), fix)
'''

GUARDED_SPAN_DICT = '''\
def fix(line, o):
    m = re.match(r"^(\\s*)a = (\\w+) \\* \\d+$", line)
    if not m:
        return [line]
    ind, v = m.groups()
    return [SpanEdit(0, 99, "nonsense"),
            SpanEdit(o.lineno + 5, o.lineno + 9, "far away"),
            SpanEdit(o.lineno, o.lineno + 1,
                     f"{ind}a = {v} * 2\\n{ind}b = a + 7")]
register(4, "guarded-span", "span with bad candidates first",
         re.compile(r"a = \\w+ \\* \\d+"), fix)
'''

ZERO_GUARD_DICT = '''\
def zero_guard(line, o):
    m = re.match(r"^(\\s*)return (\\w+) / (\\w+)$", line)
    if not m:
        return [line]
    ind, a, b = m.groups()
    return [f"{ind}if {b} == 0:\\n{ind}    return 0\\n{ind}return {a} / {b}"]
register(4, "missing-zero-guard",
         "a bare x / y return with no guard for y == 0",
         re.compile(r"return \\w+ / \\w+"), zero_guard)
'''

MEDIAN_DICT = '''\
def mean_to_median(line, o):
    m = re.match(r"^(\\s*)return sum\\((\\w+)\\) / len\\(\\2\\)$", line)
    if not m:
        return [line]
    ind, v = m.groups()
    return [(f"{ind}ys = sorted({v})\\n{ind}n = len(ys)\\n"
             f"{ind}if n % 2:\\n{ind}    return ys[n // 2]\\n"
             f"{ind}return (ys[n // 2 - 1] + ys[n // 2]) / 2")]
register(4, "mean-where-median",
         "a mean computed where the tests demand a median",
         re.compile(r"return sum\\(\\w+\\) / len\\(\\w+\\)"), mean_to_median)
'''

LIT_NEIGHBORHOOD_DICT = '''\
def lit_swap(line, o):
    out = []
    for m in re.finditer(r"(?<![\\w.])(\\d+)(?![\\w.])", line):
        for d in (1, 2, -1, -2):
            v = int(m.group(1)) + d
            if v >= 0:
                out.append(line[:m.start()] + str(v) + line[m.end():])
    return out or [line]
register(4, "lit-neighborhood", "an integer literal off by 1-2",
         re.compile(r"(?<![\\w.])\\d+(?![\\w.])"), lit_swap)
'''

ANDOR_DICT = '''\
def flip_andor(line, o):
    if " or " in line:
        return line.replace(" or ", " and ", 1)
    if " and " in line:
        return line.replace(" and ", " or ", 1)
    return line
register(4, "logic-flip", 'an "and" that should be "or", or vice versa',
         re.compile(r"\\b(?:and|or)\\b"), flip_andor)
'''

AMB_DICT = '''\
register(4, "amb-demo", "demo class with two suite-passing candidates",
         re.compile(r"K = "), lambda line, o: ["K = 1", "K = 2"])
'''


def _doc_dict(doc: str) -> str:
    d = (FLUIDFIX / "docs" / doc).read_text()
    return "# company_rules.py" + d.split("```python\n# company_rules.py")[1].split("```")[0]


def _proof_dict() -> str:
    # import docs/proof_one_example.py (main() is behind __name__ guard) and
    # take its DICTIONARY constant verbatim
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "proof_one_example", FLUIDFIX / "docs" / "proof_one_example.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.DICTIONARY


EXAMPLE_DICT = (FLUIDFIX / "examples" / "company_rules.py").read_text()

FIXTURES: list[dict] = []


def fx(name, src, group, files, dictionary=None, expect="repaired", **guard_kwargs):
    FIXTURES.append(dict(name=name, src=src, group=group, files=files,
                         dictionary=dictionary, expect=expect,
                         guard_kwargs=guard_kwargs))


# ---- shipped vocabulary -----------------------------------------------------
fx("e2e_count_above", "tests/test_e2e.py BUGGY/TEST; tests/test_guard.py",
   "shipped", {"mod.py": COUNT_ABOVE, "test_mod.py": COUNT_ABOVE_TEST})
fx("guard_join2", "tests/test_guard.py test_guard_follows_traceback_frames",
   "shipped", {"mod.py": "def join2(a, b):\n    return a - b\n",
               "test_mod.py": ("from mod import join2\n\ndef test_j():\n"
                               "    assert join2('x', 'y') == 'xy'\n")})
fx("acts_minmax", "tests/test_acts.py test_guard_repairs_minmax_swap_end_to_end",
   "shipped", {"mod.py": "def largest(xs):\n    return min(xs)\n",
               "test_mod.py": ("from mod import largest\n\ndef test_l():\n"
                               "    assert largest([3, 9, 4]) == 9\n")})
fx("fusion_cmp_ge", "tests/test_engine_fusion.py test_unambiguous_single_green_still_ships",
   "shipped", {"mod.py": "def cmp(x, t):\n    if x > t:\n        return 1\n    return 0\n",
               "test_mod.py": ("from mod import cmp\n\ndef test_c():\n"
                               "    assert cmp(5, 5) == 1 and cmp(4, 5) == 0\n")})
fx("regress_crlf_cmp", "tests/test_regressions.py test_crlf_file_untouched_... (via observer, not a hand-written Observation)",
   "shipped", {"mod.py": "def cmp(x, t):\r\n    if x >= t:\r\n        return 1\r\n    return 0\r\n",
               "test_mod.py": "from mod import cmp\n\ndef test_c():\n    assert cmp(5, 5) == 0\n"})
fx("demo_billing", "tests/test_demo_walkthrough.py step3 (no git here)",
   "shipped", {"billing.py": "def price_after_tax(p, rate):\n    return p * (1 - rate)\n",
               "test_billing.py": ("from billing import price_after_tax\n\n"
                                   "def test_tax():\n"
                                   "    assert price_after_tax(100, 0.1) == 110.00000000000001\n"),
               "invoices.py": ("def total_due(invoices):\n    due = 0\n    for inv in invoices:\n"
                               '        due += inv["amount"] + inv.get("tax", 0)\n    return due\n'),
               "test_invoices.py": ("from invoices import total_due\n\ndef test_due():\n"
                                    '    assert total_due([{"amount": 50, "tax": 5}, {"amount": 20}]) == 75\n')})

# ---- taught classes --------------------------------------------------------
fx("span_scale_pair", "tests/test_span_edits.py test_span_fixes_two_coordinated_wrong_lines",
   "taught", {"mod.py": "def scale(x):\n    a = x * 3\n    b = a + 5\n    return b\n",
              "test_mod.py": ("from mod import scale\n\ndef test_s():\n"
                              "    assert scale(1) == 9\n    assert scale(2) == 11\n")},
   SCALE_SPAN_DICT)
fx("span_rate_block", "tests/test_span_edits.py test_span_leaves_no_dead_code",
   "taught", {"mod.py": "def tax(p):\n    r = p * 0.5\n    return r + 1\n",
              "test_mod.py": "from mod import tax\n\ndef test_t():\n    assert tax(100) == 18.0\n"},
   RATE_SPAN_DICT)
fx("span_guarded", "tests/test_span_edits.py test_span_bounds_and_anchor_safety",
   "taught", {"mod.py": "def scale(x):\n    a = x * 3\n    b = a + 5\n    return b\n",
              "test_mod.py": "from mod import scale\n\ndef test_s():\n    assert scale(1) == 9\n"},
   GUARDED_SPAN_DICT)
fx("teach_split", "tests/test_teaching.py test_walkthrough_dictionary_repairs_the_incident (docs/TEACHING.md dict)",
   "taught", {"mod.py": "def parse_row(row):\n    fields = row.split()\n    return fields\n",
              "test_mod.py": ('from mod import parse_row\n\ndef test_r():\n'
                              '    assert parse_row("widget,4") == ["widget", "4"]\n')},
   _doc_dict("TEACHING.md"))
fx("teach_get_default", "tests/test_teaching.py test_example_rule_class_missing_get_default (examples/company_rules.py)",
   "taught", {"mod.py": ('def total_due(invoices):\n    due = 0\n    for inv in invoices:\n'
                         '        due += inv["amount"] + inv.get("tax")\n    return due\n'),
              "test_mod.py": ('from mod import total_due\n\ndef test_d():\n'
                              '    assert total_due([{"amount": 50, "tax": 5}, {"amount": 20}]) == 75\n')},
   EXAMPLE_DICT)
fx("teach_wrong_attr", "tests/test_teaching.py test_example_repo_mined_class_wrong_attribute",
   "taught", {"mod.py": ("class User:\n    def __init__(s):\n        s.id = 7\n        s.name = 'a'\n"
                         "def lookup_key(u):\n    return u.name\n"),
              "test_mod.py": ("from mod import User, lookup_key\n\ndef test_k():\n"
                              "    assert lookup_key(User()) == 7\n")},
   EXAMPLE_DICT)
fx("teach_round_span", "tests/test_teaching.py test_example_span_class_round_before_accumulate",
   "taught", {"mod.py": ("def checkout(subtotal, surcharge):\n"
                         "    total = round(subtotal)\n"
                         "    total = total + surcharge\n"
                         "    return total\n"),
              "test_mod.py": ("from mod import checkout\n\ndef test_c():\n"
                              "    assert checkout(99.6, 0.7) == 100\n")},
   EXAMPLE_DICT)
fx("ctx_zero_guard_r1", "tests/test_context_transforms.py test_multiline_logic_fix_from_one_example (r1)",
   "taught", {"mod.py": ("def safe_div(a, b):\n    return a / b\n\n"
                         "def rate(events, seconds):\n    return events / seconds\n"),
              "test_mod.py": ("from mod import safe_div, rate\n\ndef test_div():\n"
                              "    assert safe_div(6, 2) == 3\n    assert safe_div(5, 0) == 0\n")},
   ZERO_GUARD_DICT)
fx("ctx_zero_guard_r2", "tests/test_context_transforms.py test_multiline_logic_fix_from_one_example (r2)",
   "taught", {"mod.py": ("def safe_div(a, b):\n    if b == 0:\n        return 0\n    return a / b\n\n"
                         "def rate(events, seconds):\n    return events / seconds\n"),
              "test_mod.py": ("from mod import safe_div, rate\n\ndef test_div():\n"
                              "    assert safe_div(5, 0) == 0\n\ndef test_rate():\n"
                              "    assert rate(10, 0) == 0\n")},
   ZERO_GUARD_DICT)
fx("ctx_median_r1", "tests/test_context_transforms.py test_whole_algorithm_fix_from_one_example (r1)",
   "taught", {"mod.py": ("def middle_price(xs):\n    return sum(xs) / len(xs)\n\n"
                         "def middle_latency(vals):\n    return sum(vals) / len(vals)\n"),
              "test_mod.py": ("from mod import middle_price\n\ndef test_m():\n"
                              "    assert middle_price([1, 100, 3]) == 3\n"
                              "    assert middle_price([1, 2, 100, 4]) == 3\n")},
   MEDIAN_DICT)
fx("ctx_median_r2", "tests/test_context_transforms.py test_whole_algorithm_fix_from_one_example (r2)",
   "taught", {"mod.py": ("def middle_price(xs):\n    ys = sorted(xs)\n    n = len(ys)\n"
                         "    if n % 2:\n        return ys[n // 2]\n"
                         "    return (ys[n // 2 - 1] + ys[n // 2]) / 2\n\n"
                         "def middle_latency(vals):\n    return sum(vals) / len(vals)\n"),
              "test_mod.py": ("from mod import middle_price, middle_latency\n\ndef test_m():\n"
                              "    assert middle_price([1, 100, 3]) == 3\n\n"
                              "def test_l():\n    assert middle_latency([5, 900, 7, 9]) == 8\n")},
   MEDIAN_DICT)
fx("ctx_attr_case1", "tests/test_context_transforms.py test_value_found_in_repo_case1",
   "taught", {"mod.py": ("class U:\n    def __init__(s):\n        s.id = 7\n        s.name = 'a'\n"
                         "def f(u):\n    return u.name\n"),
              "test_mod.py": "from mod import U, f\n\ndef test():\n    assert f(U()) == 7\n"},
   WRONG_ATTR_DICT)
fx("ctx_attr_case2", "tests/test_context_transforms.py test_value_found_in_repo_case2",
   "taught", {"mod.py": ("class R:\n    def __init__(s):\n        s.total = 99\n        s.count = 1\n"
                         "def g(r):\n    return r.count\n"),
              "test_mod.py": "from mod import R, g\n\ndef test():\n    assert g(R()) == 99\n"},
   WRONG_ATTR_DICT)
fx("dict_payroll", "tests/test_dictionary.py test_dictionary_teaches_a_class_the_cli_can_use",
   "taught", {"payroll.py": ('def total_comp(rows):\n    total = 0\n    for r in rows:\n'
                             '        total += r["salary"] + r.get("bonus")\n    return total\n'),
              "test_payroll.py": ('from payroll import total_comp\n\ndef test_t():\n'
                                  '    assert total_comp([{"salary": 100, "bonus": 10}, {"salary": 200}]) == 310\n')},
   GET_DEFAULT_DICT)
fx("demo_invoices_dict", "tests/test_demo_walkthrough.py step5 (docs/DEMO.md dict; no git here)",
   "taught", {"billing.py": "def price_after_tax(p, rate):\n    return p * (1 + rate)\n",
              "test_billing.py": ("from billing import price_after_tax\n\n"
                                  "def test_tax():\n"
                                  "    assert price_after_tax(100, 0.1) == 110.00000000000001\n"),
              "invoices.py": ("def total_due(invoices):\n    due = 0\n    for inv in invoices:\n"
                              '        due += inv["amount"] + inv.get("tax")\n    return due\n'),
              "test_invoices.py": ("from invoices import total_due\n\ndef test_due():\n"
                                   '    assert total_due([{"amount": 50, "tax": 5}, {"amount": 20}]) == 75\n')},
   _doc_dict("DEMO.md"))
fx("demo_metrics_dict", "tests/test_demo_walkthrough.py step5 second member (metrics.py; no git here)",
   "taught", {"billing.py": "def price_after_tax(p, rate):\n    return p * (1 + rate)\n",
              "test_billing.py": ("from billing import price_after_tax\n\n"
                                  "def test_tax():\n"
                                  "    assert price_after_tax(100, 0.1) == 110.00000000000001\n"),
              "invoices.py": ("def total_due(invoices):\n    due = 0\n    for inv in invoices:\n"
                              '        due += inv["amount"] + inv.get("tax", 0)\n    return due\n'),
              "test_invoices.py": ("from invoices import total_due\n\ndef test_due():\n"
                                   '    assert total_due([{"amount": 50, "tax": 5}, {"amount": 20}]) == 75\n'),
              "metrics.py": ("def p_total(samples):\n    acc = 0\n    for s in samples:\n"
                             '        acc += s.get("ms")\n    return acc\n'),
              "test_metrics.py": ("from metrics import p_total\n\ndef test_m():\n"
                                  '    assert p_total([{"ms": 12}, {}]) == 12\n')},
   _doc_dict("DEMO.md"))
fx("regress_teach_andor", "tests/test_regressions.py test_teach_a_new_class_from_one_registration",
   "taught", {"mod.py": "def both(a, b):\n    return bool(a or b)\n",
              "test_mod.py": ("from mod import both\n\ndef test_b():\n"
                              "    assert both(True, False) is False\n")},
   ANDOR_DICT)

# ---- docs/proof_one_example.py members --------------------------------------
_PROOF = [
    ("billing.py", 'def due(inv):\n    return inv["amount"] + inv.get("tax")\n',
     'from billing import due\n\ndef test_due():\n    assert due({"amount": 100}) == 100\n'),
    ("metrics.py", "def latency(m):\n    return m['base'] * 2 + m.get('jitter')\n",
     "from metrics import latency\n\ndef test_latency():\n    assert latency({'base': 10}) == 20\n"),
    ("scoring.py", 'def score(cfg, base):\n    return round(base - cfg.get("penalty"))\n',
     'from scoring import score\n\ndef test_score():\n    assert score({}, 7.4) == 7\n'),
    ("cart.py", ('def total(items):\n    t = 0\n    for it in items:\n'
                 '        t += it["price"] + it.get("shipping")\n    return t\n'),
     'from cart import total\n\ndef test_total():\n    assert total([{"price": 5}, {"price": 7}]) == 12\n'),
    ("report.py", 'def net(row):\n    return row["gross"] - row.get("fee") - row.get("tax")\n',
     'from report import net\n\ndef test_net():\n    assert net({"gross": 50}) == 50\n'),
]
for i, (nm, broken, test) in enumerate(_PROOF, 1):
    fx(f"proof_member{i}_{nm[:-3]}", f"docs/proof_one_example.py MEMBERS[{i-1}]",
       "taught", {nm: broken, "test_" + nm: test}, _proof_dict())

# ---- refusals (no winner; the ranking is still logged) ---------------------
fx("ref_andor_untaught", "tests/test_e2e.py test_failed_repair_restores_source",
   "refusal", {"mod.py": "def both(a, b):\n    return bool(a or b)\n",
               "test_mod.py": ("from mod import both\n\ndef test_both():\n"
                               "    assert both(True, False) is False\n")}, expect="refused")
fx("ref_mul_out_of_vocab", "tests/test_engine_fusion.py test_refuted_refusal_does_not_escalate",
   "refusal", {"mod.py": "def f(a, b):\n    return a * b\n",
               "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f(6, 2) == 3\n"},
   expect="refused")
fx("ref_cmp_unsatisfiable", "tests/test_span_edits.py test_refusal_logs_why_each_candidate_failed",
   "refusal", {"mod.py": "def cmp(x, t):\n    if x > t:\n        return 1\n    return 0\n",
               "test_mod.py": "from mod import cmp\n\ndef test_c():\n    assert cmp(5, 5) == 7\n"},
   expect="refused")
fx("ref_two_lines_single_edit", "tests/test_context_transforms.py test_two_coordinated_wrong_lines_refuse",
   "refusal", {"mod.py": "def scale(x):\n    a = x * 3\n    b = a + 5\n    return b\n",
               "test_mod.py": ("from mod import scale\n\ndef test_s():\n"
                               "    assert scale(1) == 9\n    assert scale(2) == 11\n")},
   LIT_NEIGHBORHOOD_DICT, expect="refused")
fx("ref_amb_two_greens", "tests/test_engine_fusion.py test_ambiguous_greens_refuse_with_add_state",
   "refusal", {"mod.py": "K = 0\n\ndef f():\n    return K\n",
               "test_mod.py": "from mod import f\n\ndef test_f():\n    assert f() >= 1\n"},
   AMB_DICT, expect="refused")
fx("ref_proof_control", "docs/proof_one_example.py CONTROL",
   "refusal", {"shipping.py": 'def cost(w):\n    return w * 3\n',
               "test_shipping.py": 'from shipping import cost\n\ndef test_cost():\n    assert cost(2) == 11\n'},
   _proof_dict(), expect="refused")


# ---- the heavy one: CAPPED escalation (tests/test_engine_fusion.py) --------
def _capped_files():
    import itertools
    names = ["".join(t) for t in itertools.product("abcdefghij", repeat=3)][:800]
    filler = [f"f_{n} = True" for n in names]
    fn = ["", "def tier(v, limit):", "    if v > limit:", "        return 1", "    return 0", ""]
    body = filler[:400] + fn + filler[400:]
    return {"mod.py": "\n".join(body) + "\n",
            "test_mod.py": ("from mod import tier\n\ndef test_t():\n"
                            "    assert tier(5, 5) == 1 and tier(4, 5) == 0\n")}


fx("heavy_capped_escalation", "tests/test_engine_fusion.py test_capped_escalation_raises_budget_and_repairs (pad=0)",
   "heavy", _capped_files(), budget=280)


# ------------------------------------------------------------ harness -----
def bits_of(byte: int) -> str:
    return "+".join(b for i, b in enumerate(BITS) if byte >> i & 1) or "-"


def run_fixture(f: dict) -> dict:
    d = RUNS / f["name"]
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for rel, text in f["files"].items():
        (d / rel).write_bytes(text.encode())
    originals = {rel: text for rel, text in f["files"].items() if not rel.startswith("test_")}

    saved = dict(KINDS), dict(ACTS)
    taught = {}
    if f["dictionary"]:
        (d / "rules.py").write_text(f["dictionary"])
        n = load_dictionary(str(d / "rules.py"))
        taught = {k: KINDS[k][0] for k in KINDS if k not in saved[0]}
        assert n == len(taught), (n, taught)

    ro_log: list[dict] = []
    cand_log: list[dict] = []
    check_log: list[dict] = []

    orig_rank, orig_ro, orig_cands, orig_check = R.rank, G.rank_observations, L.candidates, Oracle.check

    def ro(src, observations, failing_output, **kw):
        calls = []

        def rank_rec(x):
            p = orig_rank(x)
            calls.append((x, p))
            return p
        R.rank = rank_rec
        try:
            out = orig_ro(src, observations, failing_output, **kw)
        finally:
            R.rank = orig_rank
        assert len(calls) == len(observations)
        rows = []
        for o, (byte, p) in zip(observations, calls):
            rows.append({"lineno": o.lineno, "kinds": list(o.kinds),
                         "classes": [KINDS[k][0] if k in KINDS else f"?{k}" for k in o.kinds],
                         "byte": byte, "bits": bits_of(byte), "priority": p,
                         "text": src.split("\n")[o.lineno - 1].strip()[:70]})
        by_line = {r["lineno"]: r for r in rows}
        ro_log.append({"rel": kw.get("rel"), "n_obs": len(observations),
                       "input_order": [o.lineno for o in observations],
                       "ranked_order": [o.lineno for o in out],
                       "rows": [by_line[o.lineno] for o in out]})
        return out

    def cands(line, act, obs):
        out = orig_cands(line, act, obs)
        cand_log.append({"lineno": obs.lineno, "kinds": list(obs.kinds), "act": act,
                         "kind": next((k for k in obs.kinds if act_for(k) == act), None),
                         "n": len(out),
                         "cands": [c if isinstance(c, str) else f"SPAN[{c.start}-{c.end}]{c.text}" for c in out]})
        return out

    def check(self, timeout=None):
        changed = []
        for rel, orig in originals.items():
            try:
                now = (Path(self.root) / rel).read_bytes().decode()
            except OSError:
                continue
            if now != orig:
                a, b = orig.split("\n"), now.split("\n")
                sm = difflib.SequenceMatcher(None, a, b)
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != "equal":
                        changed.append({"file": rel, "old_lines": f"{i1+1}-{i2}",
                                        "new": "\\n".join(x.strip() for x in b[j1:j2])[:90]})
        ok, why = orig_check(self, timeout)
        check_log.append({"n": len(check_log) + 1, "ok": ok, "changed": changed})
        return ok, why

    G.rank_observations, L.candidates, Oracle.check = ro, cands, check
    t0 = time.time()
    try:
        oracle = Oracle(str(d), python=sys.executable)
        report = guard_once(oracle, MechanicalObserver(), **f["guard_kwargs"])
    finally:
        G.rank_observations, L.candidates, Oracle.check = orig_ro, orig_cands, orig_check
        R.rank = orig_rank
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])
    secs = time.time() - t0

    out = {"name": f["name"], "src": f["src"], "group": f["group"], "expect": f["expect"],
           "taught": taught, "status": report.status, "file": report.file,
           "candidate_files": report.candidates, "evidence": report.evidence,
           "seconds": round(secs, 1), "hint": (report.hint or "")[:200],
           "rank_calls": ro_log, "candidate_calls": cand_log, "checks": check_log,
           "suite_runs": report.result.suite_runs if report.result else None,
           "winner": None}
    if report.status == "repaired":
        r = report.result
        # the ranking that governed the winning file (last call for that rel)
        table = next((c for c in reversed(ro_log) if c["rel"] == report.file), None)
        # which class produced the shipped candidate
        new = r.new_line
        win = None
        for c in cand_log:
            if c["lineno"] == r.lineno or (isinstance(new, str) and "\n" in new):
                for cand in c["cands"]:
                    if cand == new or cand == f"SPAN[{r.lineno}-{r.lineno + new.count(chr(10))}]{new}" \
                            or (cand.startswith("SPAN[") and cand.split("]", 1)[1] == new):
                        win = c
                        break
            if win:
                break
        first_green = next((c["n"] for c in check_log if c["ok"]), None)
        w = {"lineno": r.lineno, "new_line": new, "old_line": r.old_line,
             "kind": win["kind"] if win else None,
             "class": (KINDS.get(win["kind"], taught.get(win["kind"], ("?",)))[0]
                       if win and win["kind"] in KINDS else taught.get(win["kind"]) if win else None),
             "act": win["act"] if win else None,
             "first_green_check": first_green, "suite_runs": r.suite_runs,
             "reason": r.reason}
        if table is not None:
            rows = table["rows"]
            pos = next((i + 1 for i, row in enumerate(rows) if row["lineno"] == r.lineno), None)
            row = next((row for row in rows if row["lineno"] == r.lineno), None)
            w.update({
                "law_priority": row["priority"] if row else None,
                "bits": row["bits"] if row else None,
                "position_ranked": pos, "n_obs": len(rows),
                "position_input": (table["input_order"].index(r.lineno) + 1
                                   if r.lineno in table["input_order"] else None),
                "same_priority_ahead": (sum(1 for x in rows[:pos - 1] if x["priority"] == row["priority"])
                                        if pos and row else None),
                "better_priority_ahead": (sum(1 for x in rows[:pos - 1] if x["priority"] < row["priority"])
                                          if pos and row else None),
                "kind_position_in_line": ((row["kinds"].index(win["kind"]) + 1) if row and win and win["kind"] in row["kinds"] else None),
                "kinds_on_line": len(row["kinds"]) if row else None,
            })
            # flat (line, kind) slot order the body tries: ranked lines, kinds ascending
            slots = [(x["lineno"], k) for x in rows for k in sorted(kk for kk in x["kinds"] if 0 <= kk <= 15)]
            w["class_slot_position"] = (slots.index((r.lineno, win["kind"])) + 1
                                        if win and (r.lineno, win["kind"]) in slots else None)
            w["class_slots_total"] = len(slots)
        out["winner"] = w
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--group", default="")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    sel = FIXTURES
    if a.only:
        names = set(a.only.split(","))
        sel = [f for f in sel if f["name"] in names]
    if a.group:
        sel = [f for f in sel if f["group"] == a.group]
    if a.list:
        for f in sel:
            print(f["group"], f["name"])
        return 0
    LOG.mkdir(exist_ok=True)
    for f in sel:
        res = run_fixture(f)
        (LOG / f"{f['name']}.json").write_text(json.dumps(res, indent=1))
        w = res["winner"]
        line = (f"{res['name']:28s} {res['status']:8s} {res['seconds']:5.1f}s runs={res['suite_runs']}")
        if w:
            line += (f"  win L{w['lineno']} kind={w['kind']}({w['class']}) prio={w['law_priority']}"
                     f" bits={w['bits']} pos={w['position_ranked']}/{w['n_obs']}"
                     f" input_pos={w['position_input']} slot={w['class_slot_position']}/{w['class_slots_total']}"
                     f" kind_in_line={w['kind_position_in_line']}/{w['kinds_on_line']}"
                     f" first_green_check={w['first_green_check']}")
        else:
            line += f"  hint={res['hint'][:80]!r}"
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
