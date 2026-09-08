"""Worked examples for deciding the GitHub Action's default mode.

The action ships `mode: push` — a repair is committed straight back to the
branch. That is the product's whole claim, and it is also the setting that
matters most to get right, because a Marketplace listing means strangers run it
on repositories nobody has measured.

So: build realistic cases, run the REAL guard, and count what it does. The
question the corpus answers is not "does it repair" but "how often would `push`
commit something WRONG".

Each case declares what a correct outcome looks like, so every run is scored
against intent rather than against "the suite went green".
"""
import textwrap

def C(name, module, tests, defect, pristine, expect, why, dictionary=None):
    return dict(name=name, module=textwrap.dedent(module).strip()+"\n",
                tests=textwrap.dedent(tests).strip()+"\n",
                defect=defect, pristine=pristine, expect=expect, why=why,
                dictionary=dictionary)

CASES = []

# ---- A. strong suite, in-vocabulary. The case the tool exists for. --------
A = [
  ("tier", "def tier(spend):\n    if spend >= 250:\n        return 2\n    return 1",
   "    if spend >= 250:", "    if spend > 250:",
   "assert tier(250)==2\n    assert tier(249)==1\n    assert tier(1000)==2"),
  ("fee", "def fee(units):\n    return units * 7",
   "    return units * 7", "    return units * 8",
   "assert fee(3)==21\n    assert fee(1)==7\n    assert fee(10)==70"),
  ("clamp", "def clamp(v, lo):\n    return v if v >= lo else lo",
   "    return v if v >= lo else lo", "    return v if v > lo else lo",
   "assert clamp(3,5)==5\n    assert clamp(7,5)==7\n    assert clamp(5,5)==5"),
  ("head", "def head(xs):\n    return xs[0]",
   "    return xs[0]", "    return xs[1]",
   "assert head([9,1])==9\n    assert head([2,3])==2\n    assert head([0,5])==0"),
  ("delta", "def delta(a, b):\n    return a - b",
   "    return a - b", "    return b - a",
   "assert delta(9,2)==7\n    assert delta(2,9)==-7\n    assert delta(1,0)==1"),
  ("total", "def total(xs, tax):\n    return sum(xs) + tax",
   "    return sum(xs) + tax", "    return sum(xs) - tax",
   "assert total([1,2],3)==6\n    assert total([],5)==5\n    assert total([10],1)==11"),
]
for fn, body, fix, bug, t in A:
    CASES.append(C(f"A_{fn}", body,
        f"from mod import {fn}\n\ndef test_{fn}():\n    {t}",
        bug, fix, "repair_correct",
        "strong suite, defect inside the shipped vocabulary"))

# ---- B. weak suite: assertions true for a FAMILY of wrong programs -------
# This is where `push` is dangerous. Post-0.15.0 AMB must refuse these.
CASES += [
 C("B1_weak_admits_two", 
   "def alarm(readings, limit):\n    return readings[0] > limit",
   "from mod import alarm\n\ndef test_a():\n    assert alarm([7,3],3) is True\n\ndef test_b():\n    assert alarm([1,0],5) is False",
   "    return readings[1] > limit", "    return readings[0] > limit",
   "refuse", "two different programs pass this suite; shipping either is a coin flip"),
 C("B2_weak_admits_two",
   "def score(a, b):\n    return a * 2 + b",
   "from mod import score\n\ndef test_s():\n    assert score(1,2)==4",
   "    return a * 2 - b", "    return a * 2 + b",
   "repair_correct", "one assertion, but only ONE candidate passes it"),
 C("B3_weak_boundary",
   "def ok(n):\n    return n >= 10",
   "from mod import ok\n\ndef test_o():\n    assert ok(10) is True",
   "    return n > 10", "    return n >= 10",
   "either", "n>=10 and n>9 are ONE program; a fix here is correct, not a guess"),
]

CASES += [
 C("B4_weak_two_indices",
   "def pick(xs):\n    return xs[0] + xs[1]",
   "from mod import pick\n\ndef test_p():\n    assert pick([2,2,9])==4",
   "    return xs[0] + xs[2]", "    return xs[0] + xs[1]",
   "refuse", "xs[0]+xs[1] and xs[1]+xs[0] and others all give 4 on [2,2,9]"),
 C("B5_weak_single_point",
   "def rate(n):\n    return n * 2",
   "from mod import rate\n\ndef test_r():\n    assert rate(2)==4",
   "    return n * 3", "    return n * 2",
   "refuse", "n*2 and n+2 both give 4 at n=2"),
 C("B6_weak_symmetric",
   "def gap(a, b):\n    return a - b",
   "from mod import gap\n\ndef test_g():\n    assert abs(gap(3,3))==0",
   "    return a + b", "    return a - b",
   "refuse", "a-b and b-a are indistinguishable at a==b"),
]

# ---- C. out of vocabulary: must refuse, never invent ---------------------
CASES += [
 C("C1_oov_string",
   "def slug(s):\n    return s.strip().lower().replace(' ', '-')",
   "from mod import slug\n\ndef test_s():\n    assert slug(' A B ')=='a-b'",
   "    return s.strip().upper().replace(' ', '-')",
   "    return s.strip().lower().replace(' ', '-')",
   "refuse", "case transform is not a taught class"),
 C("C2_oov_logic",
   "def gate(a, b):\n    return a and not b",
   "from mod import gate\n\ndef test_g():\n    assert gate(True,False) is True\n    assert gate(True,True) is False",
   "    return a or not b", "    return a and not b",
   "refuse", "boolean connective swap, outside the shipped classes"),
]

# ---- D. the suite cannot see the defect: must do nothing -----------------
CASES += [
 C("D1_invisible",
   "def unused(x):\n    return x * 3\n\ndef used(x):\n    return x + 1",
   "from mod import used\n\ndef test_u():\n    assert used(1)==2",
   "    return x * 4", "    return x * 3",
   "green", "the defect is in a function no test calls"),
]
