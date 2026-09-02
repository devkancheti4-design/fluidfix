#!/usr/bin/env python3
"""PROOF: one example teaches a CLASS, not a case.

Run it yourself — nothing is stubbed, every repair below is fluidfix's real
guard run against a real pytest suite:

    python3 docs/proof_one_example.py

ONE worked example is registered (a real incident shape: a `.get(key)` with
no default letting None poison arithmetic). Then FIVE different members of
that class are injected — different files, different variable names,
different keys, different arithmetic, different shapes — and NOTHING further
is taught. Finally a bug OUTSIDE the class is injected as a control: it must
be refused with the tree untouched.

The dictionary is printed verbatim so you can check for yourself that it
hardcodes no answer: it derives the fix from the line it is given.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

# ---------------------------------------------------------------- THE ONE ---
# Taught from ONE worked example (incident INC-2041):
#     due += inv["amount"] + inv.get("tax")      <- summed None, crashed
#     due += inv["amount"] + inv.get("tax", 0)   <- the fix
DICTIONARY = textwrap.dedent('''
    def _missing_get_default(line, o):
        """Add the default the class is missing. The KEY is read off the
        line itself — nothing here knows any of the members below."""
        return [re.sub(r"\\.get\\((\\"[^\\"]+\\"|\\'[^\\']+\\')\\)",
                       r".get(\\1, 0)", line)]

    register(4, "missing-get-default",
             "a .get(key) with no default, letting None poison arithmetic",
             re.compile(r"\\.get\\((\\"[^\\"]+\\"|\\'[^\\']+\\')\\)"),
             _missing_get_default)
''').strip()

# ------------------------------------------------------- THE CLASS MEMBERS ---
# Each is a DIFFERENT member: different file, names, key, and arithmetic.
MEMBERS = [
    ("billing.py", "different key + different accumulator",
     'def due(inv):\n    return inv["amount"] + inv.get("tax")\n',
     'def due(inv):\n    return inv["amount"] + inv.get("tax", 0)\n',
     'from billing import due\n\ndef test_due():\n'
     '    assert due({"amount": 100}) == 100\n'),

    ("metrics.py", "different file, single-quoted key, multiplication",
     "def latency(m):\n    return m['base'] * 2 + m.get('jitter')\n",
     "def latency(m):\n    return m['base'] * 2 + m.get('jitter', 0)\n",
     "from metrics import latency\n\ndef test_latency():\n"
     "    assert latency({'base': 10}) == 20\n"),

    ("scoring.py", "different names, subtraction, nested call",
     'def score(cfg, base):\n    return round(base - cfg.get("penalty"))\n',
     'def score(cfg, base):\n    return round(base - cfg.get("penalty", 0))\n',
     'from scoring import score\n\ndef test_score():\n'
     '    assert score({}, 7.4) == 7\n'),

    ("cart.py", "member inside a loop, accumulator pattern",
     'def total(items):\n    t = 0\n    for it in items:\n'
     '        t += it["price"] + it.get("shipping")\n    return t\n',
     'def total(items):\n    t = 0\n    for it in items:\n'
     '        t += it["price"] + it.get("shipping", 0)\n    return t\n',
     'from cart import total\n\ndef test_total():\n'
     '    assert total([{"price": 5}, {"price": 7}]) == 12\n'),

    ("report.py", "two members on the SAME line",
     'def net(row):\n    return row["gross"] - row.get("fee") - row.get("tax")\n',
     'def net(row):\n    return row["gross"] - row.get("fee", 0) - row.get("tax", 0)\n',
     'from report import net\n\ndef test_net():\n'
     '    assert net({"gross": 50}) == 50\n'),
]

# control: outside the taught vocabulary entirely — must REFUSE
CONTROL = ("shipping.py",
           'def cost(w):\n    return w * 3\n',
           'from shipping import cost\n\ndef test_cost():\n'
           '    assert cost(2) == 11\n')          # unreachable by any class


def run_case(tmp, name, module_src, test_src, dict_path):
    from fluidfix import MechanicalObserver, Oracle, guard_once
    for f in os.listdir(tmp):
        if f.endswith(".py"):
            os.remove(os.path.join(tmp, f))
    open(os.path.join(tmp, name), "w").write(module_src)
    open(os.path.join(tmp, "test_" + name), "w").write(test_src)
    oracle = Oracle(tmp, python=sys.executable)
    t0 = time.time()
    report = guard_once(oracle, MechanicalObserver())
    return report, open(os.path.join(tmp, name)).read(), time.time() - t0


def main():
    from fluidfix.acts import load_dictionary

    print(__doc__)
    print("=" * 74)
    print("THE ONE EXAMPLE TAUGHT (verbatim — check it hardcodes no answer):")
    print("=" * 74)
    print(DICTIONARY)

    tmp = tempfile.mkdtemp(prefix="fluidfix-proof-")
    try:
        dict_path = os.path.join(tmp, "rules.py")
        open(dict_path, "w").write(DICTIONARY)
        n = load_dictionary(dict_path)
        print(f"\nregistered {n} class. Nothing else is taught from here on.\n")

        print("=" * 74)
        print("FIVE DIFFERENT MEMBERS OF THE CLASS — zero additional teaching")
        print("=" * 74)
        exact = 0
        for name, why, broken, fixed, test in MEMBERS:
            report, got, secs = run_case(tmp, name, broken, test, dict_path)
            ok = report.status == "repaired" and got == fixed
            exact += ok
            print(f"\n  {name:12s} {why}")
            print(f"    injected : {broken.strip().splitlines()[-1].strip()[:66]}")
            print(f"    repaired : {got.strip().splitlines()[-1].strip()[:66] if report.status=='repaired' else '(not repaired)'}")
            print(f"    verdict  : {'BYTE-EXACT' if ok else report.status.upper()}"
                  f"  in {secs:.1f}s / {report.result.suite_runs if report.result else 0} suite runs")
        print(f"\n  ---> {exact}/{len(MEMBERS)} members repaired BYTE-EXACT "
              f"from ONE example\n")

        print("=" * 74)
        print("CONTROL — a bug OUTSIDE the taught class must be REFUSED")
        print("=" * 74)
        name, broken, test = CONTROL
        report, got, secs = run_case(tmp, name, broken, test, dict_path)
        print(f"\n  {name:12s} injected : {broken.strip().splitlines()[-1].strip()}")
        print(f"    verdict  : {report.status.upper()} in {secs:.1f}s")
        print(f"    tree untouched: {got == broken}")
        if report.attempts:
            e = report.attempts[0]
            print(f"    harvest  : tried {e['tried'][:34]!r} -> {e['why'][:52]}")
        ok_control = report.status == "refused" and got == broken
        print(f"\n{'=' * 74}")
        print(f"RESULT: {exact}/{len(MEMBERS)} class members healed from ONE example; "
              f"control {'correctly refused' if ok_control else 'FAILED'}.")
        print("=" * 74)
        return 0 if exact == len(MEMBERS) and ok_control else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
