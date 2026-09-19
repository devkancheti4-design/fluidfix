#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""An eighth gate: EXHAUSTIVE over a bounded domain — the closest thing to "right for all inputs".

The six gates ask whether the suite accepts a patch. Today gave the sharpest possible demonstration of why
that is not enough: `if items[i] > value:` -> `< value:` passes all three of its bug's tests and returns
[1, 5, 4, 6] for insert_sorted([1, 4, 6], 5). It was the study's one "verified, zero wrong" repair.

Enumerating inputs alone cannot help, because enumeration needs an ORACLE and the whole premise is that no
correct version exists to compare against. What does not need a reference is a PROPERTY: a statement that
must hold for every input, whatever the implementation.

    insert_sorted   the result is sorted, and is a permutation of the input plus the value

A property is a teachable artefact exactly like a fault class, and it is worth more per unit of effort:
a class repairs one shape, a property gates every future repair to that function forever. Checked
exhaustively over a bounded domain it is a proof on that domain — not "the tests pass", but "no input up
to this size can distinguish this from correct".

  python3 gate.py
"""
from __future__ import annotations

import itertools, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent / "life-fluidfix-2026-09-18"))
from life_fluidfix import shapes_repair                                   # noqa: E402

BUGS = HERE.parent / "model-bugs-2026-09-18"


def prop_insert_sorted(fn, domain=range(0, 4), maxlen=4):
    """For every sorted list up to `maxlen` over `domain`, and every value in it: the result must be
    sorted and must be a permutation of the input plus the value."""
    checked = 0
    for n in range(0, maxlen + 1):
        for base in itertools.combinations_with_replacement(domain, n):
            for v in domain:
                items = list(base)
                try:
                    got = fn(list(items), v)
                except Exception as e:
                    return False, f"{items}, {v} raised {type(e).__name__}", checked
                checked += 1
                if got is None:
                    return False, f"{items}, {v} returned None", checked
                if list(got) != sorted(got):
                    return False, f"{items}, {v} -> {got} is not sorted", checked
                if sorted(got) != sorted(items + [v]):
                    return False, f"{items}, {v} -> {got} is not the input plus the value", checked
    return True, "", checked


def main():
    rows = []
    for f in sorted(BUGS.glob("written_*.json")):
        d = json.load(open(f))
        if "haiku" in d["author"]:
            continue
        for r in d["rows"]:
            if not r["passed"] and r["name"] == "insert_sorted":
                rows.append((d["author"], r))

    print(f"{'writer':18} {'the suite':>10} {'the property, exhaustively':>34}")
    for author, r in rows:
        for dic, tag in (("examples/taught-2026-09-16/rules_session.py", ""),
                         ("examples/taught-2026-09-19/spans.py", "")):
            got = shapes_repair(r["code"], "\n".join(r["tests"]),
                                str(HERE.parents[1] / dic))
            if got:
                break
        if not got:
            print(f"{author:18} {'refused':>10}")
            continue
        ns = {}
        exec(got["code"], ns)
        fn = ns["insert_sorted"]
        ok, why, checked = prop_insert_sorted(fn)
        verdict = f"PASS over {checked} inputs" if ok else f"FAIL — {why}"
        print(f"{author:18} {'accepted':>10} {verdict:>34}")
        rows and None
    print()
    print("The suite is three assertions. The property is every sorted list up to length four over 0..3,")
    print("with every value — and it is the difference between 'the tests pass' and 'no input this size")
    print("can tell it from correct'.")


if __name__ == "__main__":
    main()
