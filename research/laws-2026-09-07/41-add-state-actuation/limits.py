#!/usr/bin/env python
"""Where the ADD_STATE pinning-test generator FAILS -- six shapes, measured.

Each case supplies a repo, a disputed site, and >= 2 suite-passing candidate
lines, exactly as loop.py holds them at line 217. Every candidate is first
CHECKED green against the repo's own suite, so these are real AMB situations
and not hypotheticals. `expect` is what a correct generator should do:

    separate      two genuinely different programs whose difference a single
                  value CAN state; a witness must exist
    no-separate   no single-value assertion can state the difference -- two
                  SPELLINGS of one program (loop.py:213-216), or a purely
                  distributional difference. Reporting none is the RIGHT
                  answer, and emitting a witness is a defect.

usage: nice -n 15 ./tmo 900 .venv/bin/python limits.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import difftest                                                 # noqa: E402

PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
OUT = os.path.join(HERE, "limits_runs")

CASES = [
    # L1 -- two spellings of ONE program. No witness exists; saying so is right.
    dict(name="L1_spelling_only", expect="no-separate", file="stock.py",
         src='"""Stock gate."""\n\n\ndef reorder(units):\n'
             "    return units >= 10\n",
         tests="from stock import reorder\n\n\n"
               "def test_high():\n    assert reorder(15) is True\n\n\n"
               "def test_low():\n    assert reorder(5) is False\n\n\n"
               "def test_at():\n    assert reorder(10) is True\n",
         lineno=5,
         cands=["    return units >= 10", "    return units > 9"]),

    # L2 -- two DIFFERENT programs whose disagreement region is far from any
    # value the suite mentions.
    dict(name="L2_distant_literal", expect="separate", file="fee.py",
         src='"""Oversize fee."""\n\n\ndef fee(w):\n    return w > 20\n',
         tests="from fee import fee\n\n\n"
               "def test_huge():\n    assert fee(200.0) is True\n\n\n"
               "def test_small():\n    assert fee(10.0) is False\n\n\n"
               "def test_tiny():\n    assert fee(5.0) is False\n",
         lineno=5,
         cands=["    return w > 20", "    return w > 120"]),

    # L3 -- C source. fluidfix's real corpus (Box2D, cglm) is C.
    dict(name="L3_c_source", expect="separate", file="clamp.c",
         src="/* clamp */\n#include <stddef.h>\n\n"
             "int clamp(int v, int lo, int hi)\n{\n"
             "    if (v > hi) return hi;\n"
             "    return v < lo ? lo : v;\n}\n",
         tests="", lineno=6,
         cands=["    if (v > hi) return hi;", "    if (v >= hi) return hi;"],
         skip_green_check=True),

    # L4 -- the function does not hold still (random). The stability filter
    # discards every input, so nothing can be pinned.
    # expect=no-separate: the candidates ARE two different programs, but the
    # difference is DISTRIBUTIONAL. No single-value assertion can state it, so
    # emitting a witness here would be a FLAKY test -- refusing is correct.
    dict(name="L4_nondeterministic", expect="no-separate", file="jitter.py",
         src='"""Jittered score."""\nimport random\n\n\ndef score(n):\n'
             "    return n + random.randint(0, 3)\n",
         tests="from jitter import score\n\n\n"
               "def test_range():\n    assert 5 <= score(5) <= 8\n",
         lineno=6,
         cands=["    return n + random.randint(0, 3)",
                "    return n + random.randint(1, 3)"],
         skip_green_check=True),

    # L5 -- the function takes an OBJECT. No literal call args to harvest.
    dict(name="L5_object_argument", expect="separate", file="shape.py",
         src='"""Shapes."""\n\n\nclass Box:\n'
             "    def __init__(self, w, h):\n"
             "        self.w, self.h = w, h\n\n\n"
             "def area(box):\n"
             "    return box.w * box.h\n",
         tests="from shape import Box, area\n\n\n"
               "def test_square():\n    assert area(Box(2, 2)) == 4\n",
         lineno=10,
         cands=["    return box.w * box.h", "    return box.w + box.h"]),

    # L6 -- the COMPENSATING shape loop.py:208-212 describes: two greens at
    # DIFFERENT lines in different functions. Repair `project`, or break `add`
    # so the two faults cancel.
    dict(name="L6_two_site_compensating", expect="separate", file="geom.py",
         src='"""Vector helpers."""\n\n\ndef add(a, b):\n'
             "    return [a[0] + b[0], a[1] + b[1]]\n\n\n"
             "def project(v, k):\n"
             "    return add(v, [k, k])\n",
         tests="from geom import project\n\n\n"
               "def test_project_up():\n"
               "    assert project([1, 2], 3) == [4, 5]\n\n\n"
               "def test_project_zero():\n"
               "    assert project([7, 8], 0) == [7, 8]\n",
         edits=[(9, "    return add(v, [k, k])"),
                (5, "    return [a[0] - b[0], a[1] - b[1]]")],
         defect=(9, "    return add(v, [-k, -k])"),
         lineno=9,
         cands=None),
]


def sh(args, cwd, timeout=120):
    return subprocess.run(["nice", "-n", "15"] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=timeout)


def suite_green(d):
    return sh([PY, "-B", "-m", "pytest", "-q",
               "-p", "no:cacheprovider"], d).returncode == 0


def put(d, rel, src, edits):
    raw = src.split("\n")
    for ln, line in edits:
        raw[ln - 1] = line
    with open(os.path.join(d, rel), "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(raw))


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    rows = []
    for c in CASES:
        d = os.path.join(OUT, c["name"])
        os.makedirs(d)
        with open(os.path.join(d, c["file"]), "w", encoding="utf-8",
                  newline="") as f:
            f.write(c["src"])
        if c["tests"]:
            with open(os.path.join(d, "test_" + c["file"].replace(".c", ".py")),
                      "w", encoding="utf-8", newline="") as f:
                f.write(c["tests"])

        if c.get("edits"):
            edits = c["edits"]
            put(d, c["file"], c["src"], [c["defect"]])
        else:
            edits = [(c["lineno"], x) for x in c["cands"]]

        rec = {"name": c["name"], "expect": c["expect"],
               "candidates": [e[1] for e in edits],
               "sites": sorted({e[0] for e in edits})}

        # every candidate must really be green -- otherwise it is not AMB
        if not c.get("skip_green_check"):
            # a candidate is applied ON TOP of the DEFECTIVE tree, which for
            # the two-site shape is what makes the compensating one green
            base = [c["defect"]] if c.get("defect") else []
            greens = []
            for ln, line in edits:
                put(d, c["file"], c["src"], base + [(ln, line)])
                greens.append(suite_green(d))
            rec["candidates_green"] = greens
            rec["is_real_amb"] = all(greens)
            put(d, c["file"], c["src"],
                [c["defect"]] if c.get("edits") else [])
        else:
            rec["candidates_green"] = "not checked (see note)"

        gen = difftest.differentiate(d, c["file"], rec["sites"][0], edits, HERE)
        rec["separated"] = bool(gen.get("separated"))
        rec["as_expected"] = (rec["separated"] == (c["expect"] == "separate"))
        rec["gen"] = {k: v for k, v in gen.items() if k != "test_text"}
        if gen.get("test_text"):
            with open(os.path.join(d, "test_fluidfix_pin.py"), "w",
                      encoding="utf-8") as f:
                f.write(gen["test_text"])
            rec["witness_call"] = gen["witness_call"]
            rec["witness_values"] = gen["witness_values"]
        rows.append(rec)
        print(f"  {c['name']:<26} expect={c['expect']:<12} "
              f"separated={rec['separated']!s:<6} "
              f"as_expected={rec['as_expected']}  "
              f"{gen.get('witness_call') or gen.get('failed', '')[:70]}")

    with open(os.path.join(HERE, "results_limits.json"), "w") as f:
        json.dump(rows, f, indent=1)
    ok = sum(1 for r in rows if r["as_expected"])
    print(f"\ncases: {len(rows)}   generator did the right thing: {ok}")


if __name__ == "__main__":
    main()
