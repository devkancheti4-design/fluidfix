#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A seventh gate: MINIMAL DELTA — a repair may change behaviour only where the failing test demands it.

The six gates ask whether the suite went green. None of them asks **what else changed**. Both false accepts
found on real history slipped through precisely there:

    segment.py    `- 1` outside the multiplication instead of inside it
    traceback.py  a padding tuple altered somewhere else in the file entirely

Neither breaks a test, because the tests do not pin those behaviours. But both change what the program
*computes* under tests that were already passing — and a repair has no business doing that.

This measures it without writing a single new test. The enclosing function of the changed line is wrapped
so that every call it makes during the suite records its result. The suite is then run three times, over
exactly the tests that were ALREADY PASSING:

    original      the buggy program
    candidate     what fluidfix shipped
    reference     what the maintainer committed        (a control, not available at repair time)

and the delta is the fraction of recorded calls whose result changed. A correct repair should be near zero
on tests that were already passing: it fixes the broken case and leaves the rest alone. A compensating edit
should be large.

  PYTHONPATH=<fluidfix>/src python3 delta.py
"""
from __future__ import annotations

import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/rp_rich")
PY = str(REPO / ".venv" / "bin" / "python")
BASE = ["-q", "--no-header", "-p", "no:cacheprovider", "-W", "default"]

PLUGIN = '''
import json, os
def pytest_configure(config):
    import importlib
    mod = importlib.import_module(os.environ["DELTA_MOD"])
    parts = os.environ["DELTA_QUAL"].split(".")
    parent = mod
    for p in parts[:-1]:
        parent = getattr(parent, p)
    orig = getattr(parent, parts[-1])
    log = []
    config._delta_log = log
    def wrapper(*a, **k):
        r = orig(*a, **k)
        try:
            log.append(repr(r)[:300])
        except Exception:
            log.append("<unreprable>")
        return r
    wrapper.__name__ = getattr(orig, "__name__", parts[-1])
    setattr(parent, parts[-1], wrapper)

def pytest_sessionfinish(session, exitstatus):
    log = getattr(session.config, "_delta_log", [])
    with open(os.environ["DELTA_OUT"], "w") as f:
        json.dump(log, f)
'''

CASES = [
 {"name": "rich/segment.py — Segment._split_cells", "sha": "aa0929298b", "rel": "rich/segment.py",
  "line": 122, "mod": "rich.segment", "qual": "Segment.split_cells",
  # observe the PUBLIC method the tests call: _split_cells is a @classmethod under @lru_cache, and
  # replacing that attribute breaks the descriptor instead of wrapping it.
  "orig":  "        pos = int((cut / cell_length) * len(text))",
  "cand":  "        pos = int((cut / cell_length) * len(text) - 1)",
  "ref":   "        pos = int((cut / cell_length) * (len(text) - 1))"},
 {"name": "rich/traceback.py — Traceback.__rich_console__", "sha": "83af951663", "rel": "rich/traceback.py",
  "line": 452, "mod": "rich.traceback", "qual": "Traceback.__rich_console__",
  "orig":  "                    padding=(0, 1),",
  "cand":  "                    padding=(0, 0),",
  # the maintainer's fix is at a DIFFERENT LINE, 587 — further confirmation that what fluidfix
  # changed was nowhere near the fault
  "ref":   "            first = frame_index == 0",
  "ref_line": 587,
  "ref_orig": "            first = frame_index == 1"},
]


def sh(a, cwd=None, env=None, t=1800):
    return subprocess.run(a, cwd=cwd, env=env, capture_output=True, text=True, timeout=t)


def run_logged(case, variant_lines, passing_only, tag):
    """Run the already-passing tests with the function wrapped, and return its recorded results."""
    src = REPO / case["rel"]
    keep = src.read_text()
    src.write_text("\n".join(variant_lines))
    out = REPO / f"_delta_{tag}.json"
    env = dict(os.environ, DELTA_MOD=case["mod"], DELTA_QUAL=case["qual"], DELTA_OUT=str(out))
    sh([PY, "-m", "pytest"] + BASE + ["--tb=no", "-p", "_delta_plugin"] + passing_only,
       cwd=REPO, env=env, t=1800)
    src.write_text(keep)
    if out.exists():
        data = json.loads(out.read_text()); out.unlink()
        return data
    return None


def main():
    rows = {r["sha"][:10]: r for r in
            json.load(open(HERE.parent / "real-history-2026-09-19" / "tested_fixes.json"))}
    (REPO / "_delta_plugin.py").write_text(PLUGIN)
    report = []

    for case in CASES:
        r = rows[case["sha"]]
        print(f"\n{'='*76}\n{case['name']}")
        sh(["git", "checkout", "-q", "-f", r["sha"] + "^"], cwd=REPO); sh(["git", "clean", "-qfd", "-e", "_delta_plugin.py", "-e", ".venv"], cwd=REPO)
        (REPO / "_delta_plugin.py").write_text(PLUGIN)

        g0 = sh([PY, "-m", "pytest"] + BASE + ["--tb=no"], cwd=REPO)
        pre = {l.split(" ")[1] for l in g0.stdout.split("\n")
               if l.startswith("FAILED") and len(l.split(" ")) > 1}
        desel = [x for t in pre for x in ("--deselect", t)]
        sh(["git", "checkout", r["sha"], "--"] + r["tests"], cwd=REPO)
        g1 = sh([PY, "-m", "pytest"] + BASE + ["--tb=no"] + desel, cwd=REPO)
        failing = {l.split(" ")[1] for l in g1.stdout.split("\n")
                   if l.startswith("FAILED") and len(l.split(" ")) > 1}
        # the gate measures ONLY tests that were already passing: the failing one is allowed to change
        passing_only = desel + [x for t in failing for x in ("--deselect", t)]
        print(f"  {len(pre)} pre-existing failures deselected · "
              f"{len(failing)} failing test(s) also excluded — the delta is measured on the rest")

        src_lines = (REPO / case["rel"]).read_text().split("\n")
        assert src_lines[case["line"]-1].rstrip() == case["orig"].rstrip(), "line moved"

        def variant(newline, at=None):
            v = list(src_lines); v[(at or case["line"])-1] = newline; return v

        base = run_logged(case, src_lines, passing_only, "base")
        cand = run_logged(case, variant(case["cand"]), passing_only, "cand")
        if base is None or cand is None:
            print("  the wrapper recorded nothing — cannot measure"); continue

        n = min(len(base), len(cand))
        changed = sum(1 for i in range(n) if base[i] != cand[i])
        print(f"  calls recorded: {len(base)} original, {len(cand)} candidate")
        print(f"  CANDIDATE  (what fluidfix shipped)  delta = {changed}/{n} "
              f"({changed/max(1,n):.0%}) of calls under ALREADY-PASSING tests")

        entry = {"case": case["name"], "calls": n, "candidate_delta": changed}
        if case.get("ref"):
            at = case.get("ref_line") or case["line"]
            if case.get("ref_orig"):
                assert src_lines[at-1].rstrip() == case["ref_orig"].rstrip(), \
                    f"reference line moved: {src_lines[at-1]!r}"
            ref = run_logged(case, variant(case["ref"], at), passing_only, "ref")
            if ref is not None:
                m = min(len(base), len(ref))
                rc = sum(1 for i in range(m) if base[i] != ref[i])
                print(f"  REFERENCE  (what the maintainer wrote) delta = {rc}/{m} ({rc/max(1,m):.0%})")
                entry["reference_delta"] = rc; entry["reference_calls"] = m
        report.append(entry)

    sh(["git", "checkout", "-q", "-f", "HEAD"], cwd=REPO)
    (HERE / "delta.json").write_text(json.dumps(report, indent=1))
    print("\nDELTA_DONE")


if __name__ == "__main__":
    main()
