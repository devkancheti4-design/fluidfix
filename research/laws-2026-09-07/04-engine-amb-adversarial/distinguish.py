#!/usr/bin/env python
"""Report-only OBSERVATION prototype: are two green candidates the SAME
program or DIFFERENT programs?

The body today measures AMB as `set_amb or len(sites) > 1` (loop.py:218),
i.e. "same candidate set" or "different line". Neither is "different
program". This script measures the thing the spec actually names: for each
fixture in amb_fixtures.py it rebuilds the two green modules and probes
every top-level function of both with the same random integer inputs,
counting inputs on which the two greens DISAGREE (different value, or one
raises and the other does not).

    0 disagreements in N samples  -> no evidence they are different programs
                                     (NOT a proof of equivalence; bounded
                                     observation, ints only)
    >0 disagreements              -> proven different programs, with a
                                     concrete witness input

Nothing decides here; the number is the observation a law could read.
Run:  nice -n 15 ./with_timeout.sh 300 <venv>/bin/python distinguish.py
"""
from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)

from amb_fixtures import FIXTURES, kinds_for  # noqa: E402
from fluidfix.acts import Observation, act_for, candidates  # noqa: E402

N = 2000
random.seed(20260907)


def green_variants(fx: dict, greens: list[str]) -> list[tuple[int, str]]:
    """Locate each green (stripped text) as (lineno, full candidate line) by
    regenerating the candidate sets exactly as loop.py does."""
    src_lines = fx["mod"].split("\n")
    out = []
    for g in greens:
        found = None
        for l in fx["lines"]:
            body = src_lines[l - 1]
            obs = Observation(lineno=l, kinds=kinds_for(body))
            obs.all_lines = src_lines
            for k in obs.kinds:
                for c in candidates(body, act_for(k), obs):
                    if isinstance(c, str) and c.strip() == g:
                        found = (l, c)
                        break
                if found:
                    break
            if found:
                break
        assert found, (fx["name"], g)
        out.append(found)
    return out


def module_with(fx: dict, lineno: int, line: str) -> dict:
    src_lines = fx["mod"].split("\n")
    src_lines[lineno - 1] = line
    ns: dict = {}
    exec(compile("\n".join(src_lines), f"<{fx['name']}>", "exec"), ns)
    return ns


def call(fn, args):
    try:
        return ("ok", fn(*args))
    except Exception as e:                       # noqa: BLE001
        return ("raise", type(e).__name__)


def probe(fx: dict, a: dict, b: dict) -> dict:
    fns = [k for k, v in a.items()
           if callable(v) and getattr(v, "__module__", None) is None
           and not k.startswith("_")]
    disagreements = 0
    witness = None
    for _ in range(N):
        name = random.choice(fns)
        fa, fb = a[name], b[name]
        arity = fa.__code__.co_argcount
        args = tuple(random.randint(-20, 20) for _ in range(arity))
        ra, rb = call(fa, args), call(fb, args)
        if ra != rb:
            disagreements += 1
            if witness is None:
                witness = f"{name}{args}: {ra} vs {rb}"
    return dict(samples=N, functions=fns, disagreements=disagreements,
                witness=witness)


def main() -> None:
    with open(os.path.join(HERE, "results.json")) as fh:
        results = {r["name"]: r for r in json.load(fh)}
    rows = []
    print(f"{'fixture':48} {'spec':10} {'body AMB':9} {'disagree/N':12} witness")
    for fx in FIXTURES:
        r = results[fx["name"]]
        greens = r["direct"]["greens"]
        if len(greens) < 2:
            continue
        (l1, c1), (l2, c2) = green_variants(fx, greens[:2])
        m1, m2 = module_with(fx, l1, c1), module_with(fx, l2, c2)
        p = probe(fx, m1, m2)
        body_amb = r["direct"]["ambiguous"]
        measured_amb = p["disagreements"] > 0
        rows.append(dict(name=fx["name"], spec=fx["spec"], body_amb=body_amb,
                         greens=[(l1, c1.strip()), (l2, c2.strip())],
                         probe=p, probe_amb=measured_amb))
        print(f"{fx['name']:48} {fx['spec']:10} {str(body_amb):9} "
              f"{p['disagreements']:>5}/{p['samples']:<6} {p['witness']}")
    with open(os.path.join(HERE, "distinguish.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    agree = sum(1 for r in rows
                if (r["probe_amb"] and r["spec"] == "ADD_STATE")
                or (not r["probe_amb"] and r["spec"] == "SHIP"))
    body = sum(1 for r in rows
               if (r["body_amb"] and r["spec"] == "ADD_STATE")
               or (not r["body_amb"] and r["spec"] == "SHIP"))
    print(f"\nfixtures where the observation matches the spec's 'different "
          f"program' reading: probe {agree}/{len(rows)}, body today {body}/{len(rows)}")
    print("(F6 is the exception by design: CHANGELOG defines two SITES as AMB "
          "regardless of program identity — the probe says 'one program', the "
          "sites rule says 'two claims about where'.)")


if __name__ == "__main__":
    main()
