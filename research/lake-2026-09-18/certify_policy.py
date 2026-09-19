#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Certify an ORDERING POLICY against the recorded incidents, instead of guessing at one.

How the net orders its territories is a policy. I had begun guessing — deprioritise what was refused
before — and then paying an hour of suite runs per guess. The incidents can rule on it directly: each one
records the territories the failing test executed, their executed-line counts, what the failure output
names, and which territory actually held the fault.

A policy is scored by the RANK it gives the answering territory, replayed over the incidents in order, so
that a policy which learns from earlier incidents is measured on the later ones. Rank 1 means the net opens
the right territory first.

Nothing is asserted here and nothing is run: the incidents decide.
"""
import json, re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
INC = json.load(open(HERE / "surveys_click.json"))


def names_it(rec, rel):
    out, stem = rec["failing_output"], Path(rel).stem
    if rel in out or f"{stem}.py" in out:
        return 2
    for line in out.split("\n"):
        if line.startswith("FAILED") and len(line.split(" ")) > 1:
            for part in Path(line.split(" ")[1].split("::")[0]).parts:
                s = Path(part).stem
                if (s[5:] if s.startswith("test_") else s) == stem:
                    return 1
    return 0


POLICIES = {
    "most-executed first (net.py today)":
        lambda rec, rel, refused, answered: (-rec["files"][rel]["executed"],),
    "what the failure names, then executed":
        lambda rec, rel, refused, answered: (-names_it(rec, rel), -rec["files"][rel]["executed"]),
    "... + FEWEST past refusals  (my guess)":
        lambda rec, rel, refused, answered: (-names_it(rec, rel), refused.get(rel, 0),
                                             -rec["files"][rel]["executed"]),
    "... + MOST past refusals  (the inverted sign)":
        lambda rec, rel, refused, answered: (-names_it(rec, rel), -refused.get(rel, 0),
                                             -rec["files"][rel]["executed"]),
    "... + territories that have ANSWERED before":
        lambda rec, rel, refused, answered: (-names_it(rec, rel), -answered.get(rel, 0),
                                             -rec["files"][rel]["executed"]),
}

print(f"{'policy':46} {'ranks of the answering territory':>34} {'mean':>6}")
results = {}
for label, key in POLICIES.items():
    refused, answered, ranks = Counter(), Counter(), []
    for rec in INC:
        order = sorted(rec["files"], key=lambda r: key(rec, r, refused, answered))
        rank = order.index(rec["answer_file"]) + 1
        ranks.append(rank)
        # everything the net would have opened before the answer counts as a refusal it paid for
        for r in order[:rank - 1]:
            refused[r] += 1
        answered[rec["answer_file"]] += 1
    results[label] = ranks
    print(f"{label:46} {str(ranks):>34} {sum(ranks)/len(ranks):>6.1f}")

best = min(results, key=lambda k: sum(results[k]))
print(f"\nthe incidents rule for: {best}")
print(f"  total territory-openings before the answer: "
      + ", ".join(f"{sum(v)} ({k.split('(')[0].strip()[:28]})" for k, v in
                  sorted(results.items(), key=lambda kv: sum(kv[1]))))
