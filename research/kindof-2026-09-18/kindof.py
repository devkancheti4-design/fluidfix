#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The way back: from a fault to its KIND — the smallest edit budget that reaches a certified destination.

`../model-bugs-2026-09-18` sorted thirteen model-written faults into three kinds and admitted underneath
that the sorting was *a reading of the code, not a measurement*. This makes it a measurement.

A fault's kind is not an opinion about how the code looks. It is **the smallest class of edit that the
suite will accept**, and that is a search — the same net, grown over edit budgets instead of territories,
with the same rulings and the same thing stopping it:

    L0  VOCABULARY   fluidfix's shipped + taught classes propose; the suite judges         $0
                     -> MECHANICAL
    L1  ONE-LINE     exactly one existing line replaced by one line, and nothing else      a model writes
                     -> ONE-LINE-TEACHABLE: outside today's vocabulary, but one worked example adds it
    L2  INSERTION    lines may be ADDED; no existing line may change                       a model writes
                     -> INSERTION: every act transforms a line that is already there, so no line-rewriting
                        vocabulary can ever express this, however much it is taught
    L3  ANYTHING     the algorithm, not the line                                           a model writes
                     -> STRUCTURAL

REFUTED at a level means grow WIDER — the next budget up. The first level the suite accepts is the answer,
and it stops the ladder.

The model cannot cheat its level. Every returned patch has its DIFF CHECKED against the budget it was asked
for, mechanically, before the suite ever runs: an L1 answer that adds a line is rejected as an L1 answer.
So the classification is decided by the diff shape and the suite, never by what the model says it did.

  python3 kindof.py --phase l0
  python3 kindof.py --phase ask   --level 1        # writes the prompt for the level's remaining faults
  python3 kindof.py --phase judge --level 1 --answers answers_l1.json
"""
from __future__ import annotations

import argparse, difflib, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent / "life-fluidfix-2026-09-18"))
BUGS = HERE.parent / "model-bugs-2026-09-18"
DICT = str(HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py")
STATE = HERE / "kindof.json"

from life_fluidfix import run_test, shapes_repair                          # noqa: E402

LEVELS = {1: "ONE-LINE-TEACHABLE", 2: "INSERTION", 3: "STRUCTURAL"}


def cases():
    good = {}
    for f in ("written_haiku-hard.json", "written_haiku.json"):
        for r in json.load(open(BUGS / f))["rows"]:
            if r["passed"]:
                good[r["name"]] = r["code"]
    out = []
    for f in sorted(BUGS.glob("written_*.json")):
        d = json.load(open(f))
        if "haiku" in d["author"]:
            continue
        for r in d["rows"]:
            if not r["passed"]:
                out.append({"id": f"{d['author']}/{r['name']}", "fault": r["name"], "writer": d["author"],
                            "code": r["code"], "tests": r["tests"], "why": r["why"]})
    return out


def diff_shape(broken: str, fixed: str) -> dict:
    a, b = broken.split("\n"), fixed.split("\n")
    rem = add = hunks = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        hunks += 1; rem += i2 - i1; add += j2 - j1
    return {"hunks": hunks, "removed": rem, "added": add}


def structure_preserving(broken: str, fixed: str) -> tuple[bool, str]:
    """Is this a one-line fix a vocabulary could ever be TAUGHT, or does it just game the budget?

    "Exactly one line replaced" turns out to be gameable, and the model answering level 1 found the hole at
    once: replace a function's DOCSTRING with `return list(range(start, 0, -1))` and leave the entire
    original body underneath as dead code. That is one line by the diff, and nothing any vocabulary of line
    transforms would ever propose. So the budget is measured here, not merely counted.

    Two disqualifications, both decided from the text and the AST:
      * the replaced line was a docstring or a comment -- not a line the failing test ever executed
      * the edit leaves statements that can never run, an unconditional return/raise now preceding them
    """
    import ast as _ast
    a, b = broken.split("\n"), fixed.split("\n")
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal" or i1 >= len(a):
            continue
        old = a[i1].strip()
        if old[:1] in {"#", chr(34), chr(39)}:
            return False, "replaced a docstring or comment, not a line the test executed"
    try:
        tree = _ast.parse(fixed)
    except SyntaxError:
        return False, "does not parse"
    for node in _ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for st in body[:-1]:
            if isinstance(st, (_ast.Return, _ast.Raise)):
                return False, "leaves dead code after an unconditional return"
    return True, ""


def obeys(level: int, s: dict) -> bool:
    """Does the patch actually stay inside the budget it was asked for? Decided from the diff, not claims."""
    if level == 1:
        return s["hunks"] == 1 and s["removed"] == 1 and s["added"] == 1
    if level == 2:
        return s["removed"] == 0 and s["added"] > 0
    return s["hunks"] >= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["l0", "ask", "judge", "report"], required=True)
    ap.add_argument("--level", type=int, default=1); ap.add_argument("--answers")
    a = ap.parse_args()
    st = json.load(open(STATE)) if STATE.exists() else {"rows": {}}

    if a.phase == "l0":
        cs = cases()
        print(f"{len(cs)} real model-written faults\n{'fault':16} {'writer':16} L0 (the vocabulary, $0)")
        for c in cs:
            got = shapes_repair(c["code"], "\n".join(c["tests"]), DICT)
            st["rows"][c["id"]] = {"fault": c["fault"], "writer": c["writer"],
                                   "kind": "MECHANICAL" if got else None,
                                   "level": 0 if got else None,
                                   "edit": ({"before": got["before"], "after": got["after"],
                                             "shape": got["shape"]} if got else None)}
            print(f"{c['fault']:16} {c['writer']:16} "
                  f"{'MECHANICAL via ' + got['shape'] if got else 'REFUTED -> wider'}")
        open_n = sum(1 for v in st["rows"].values() if v["kind"] is None)
        print(f"\nL0: {len(cs) - open_n} of {len(cs)} MECHANICAL, {open_n} refuted -> level 1")

    elif a.phase == "ask":
        cs = [c for c in cases() if st["rows"].get(c["id"], {}).get("kind") is None]
        rule = {1: "You may replace EXACTLY ONE existing line with exactly one line. You may not add or "
                   "delete any line. No imports may be added.",
                2: "You may only ADD new lines. You may NOT change or delete any existing line.",
                3: "You may change anything."}[a.level]
        payload = [{"id": c["id"], "code": c["code"], "tests": c["tests"]} for c in cs]
        (HERE / f"ask_l{a.level}.json").write_text(json.dumps({"rule": rule, "cases": payload}, indent=1))
        print(f"level {a.level}: {len(cs)} faults still open -> ask_l{a.level}.json\nRULE: {rule}")

    elif a.phase == "judge":
        answers = json.load(open(a.answers))
        cs = {c["id"]: c for c in cases()}
        kept = 0
        print(f"{'fault':16} {'writer':16} {'diff':>22}  verdict")
        for cid, patch in answers.items():
            c = cs.get(cid)
            if c is None or st["rows"].get(cid, {}).get("kind") is not None:
                continue
            s = diff_shape(c["code"], patch)
            shape = f"{s['hunks']}h -{s['removed']} +{s['added']}"
            if not obeys(a.level, s):
                print(f"{c['fault']:16} {c['writer']:16} {shape:>22}  REJECTED — left the budget")
                continue
            if not run_test(patch, "\n".join(c["tests"])):
                print(f"{c['fault']:16} {c['writer']:16} {shape:>22}  refused — the suite rejects it")
                continue
            ok, why = structure_preserving(c["code"], patch) if a.level == 1 else (True, "")
            st["rows"][cid].update({"kind": LEVELS[a.level], "level": a.level, "edit": s,
                                    "patch": patch, "structure_preserving": ok, "caveat": why})
            kept += 1
            note = "" if ok else "   [GAMES THE BUDGET: " + why + "]"
            print(f"{c['fault']:16} {c['writer']:16} {shape:>22}  {LEVELS[a.level]}{note}")
        print(f"\nlevel {a.level}: {kept} settled, "
              f"{sum(1 for v in st['rows'].values() if v['kind'] is None)} still open")

    else:
        from collections import Counter
        t = Counter(v["kind"] or "UNSETTLED" for v in st["rows"].values())
        print(f"{'kind':22} {'n':>3}   what it means for a line-rewriting vocabulary")
        meaning = {"MECHANICAL": "already repaired, $0",
                   "ONE-LINE-TEACHABLE": "one worked example would add it",
                   "INSERTION": "the fix is a line that is NOT THERE — unreachable however much is taught",
                   "STRUCTURAL": "the algorithm — needs a model or a person",
                   "UNSETTLED": "no level settled it"}
        for k, v in t.most_common():
            print(f"{k:22} {v:>3}   {meaning.get(k, '')}")
        gamed = [v for v in st["rows"].values() if v.get("structure_preserving") is False]
        real = [v for v in st["rows"].values() if v.get("structure_preserving") is True]
        if gamed or real:
            print(f"\nof the ONE-LINE verdicts: {len(real)} structure-preserving (a vocabulary could be "
                  f"taught them), {len(gamed)} game the budget:")
            for v in gamed:
                print(f"    {v['fault']:16} {v['writer']:16} {v['caveat']}")
    STATE.write_text(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
