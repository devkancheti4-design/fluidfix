#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The handoff: fluidnet refuses, a model writes, fluidnet certifies — and every artifact is recorded.

This is the loop the whole body of work points at, run end to end on a fault fluidfix has already been
measured unable to author:

  1  REFUSE    the net grows over (territory, class) until the vocabulary is exhausted. The refusal is not
               a shrug: it names the territory the failure points at, every class it tried, and what the
               suite said. That localisation is the artefact handed onward.
  2  WRITE     a model sees the failing test, the file, and the refusal. Nothing else. It writes a fix.
  3  CERTIFY   the fix is judged by DESTINATION, not by who wrote it or how it is spelled: red before,
               green on the full suite, stable on re-check, nothing else broken, byte-exact rollback
               otherwise.
  4  SEPARATE  if two fixes both pass, the suite cannot tell them apart -- AMB. The net then grows over
               INPUT space until it finds the input where the two actually diverge, and refuses to certify
               either, naming the place the specification never decided.

  PYTHONPATH=<fluidfix>/src python3 handoff.py --phase refuse
  PYTHONPATH=<fluidfix>/src python3 handoff.py --phase certify --patch a.py [--patch b.py]
"""
from __future__ import annotations

import argparse, ast, json, os, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
BUGS = HERE.parent / "model-bugs-2026-09-18"
CERT = HERE.parent / "certify-2026-09-18"
DIVERGE = HERE.parent / "model-divergence-2026-09-18"
PY = str(HERE.parents[1] / ".venv" / "bin" / "python")
sys.path.insert(0, str(SRC)); sys.path.insert(0, str(CERT)); sys.path.insert(0, str(DIVERGE))
sys.path.insert(0, str(HERE.parent / "closed-loop-2026-09-18")); sys.path.insert(0, str(HERE))

from fluidfix.oracle import Oracle                                         # noqa: E402
from fluidfix import differ                                                # noqa: E402
from closed_loop import DRIVER, sh                                         # noqa: E402
import fluidnet as FN                                                      # noqa: E402

WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/handoff")
STATE = HERE / "handoff_state.json"
# a REAL model-authored fault, already measured as refused by the vocabulary (../model-bugs-2026-09-18)
FAULT = ("percentile", "written_gemma3-4b-hard.json")


def build(root: Path):
    rows = (json.load(open(BUGS / "written_haiku-hard.json"))["rows"]
            + json.load(open(BUGS / "written_haiku.json"))["rows"])
    good = [(r["name"], r["code"], r["tests"]) for r in rows if r["passed"]]
    broken_rows = json.load(open(BUGS / FAULT[1]))["rows"]
    bad = next(r for r in broken_rows if r["name"] == FAULT[0] and not r["passed"])
    mods = [m for m in good if m[0] != FAULT[0]][:7]
    mods.append((FAULT[0], bad["code"], bad["tests"]))
    FN.build_world(root, mods)
    return bad


def refuse(a):
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    WORK.mkdir(parents=True, exist_ok=True)
    root = WORK / "world"
    bad = build(root)
    o = Oracle(str(root), python=PY)
    assert not o.green(), "the fault did not turn the suite red"
    red, out = o.failing_output()
    sv = FN.survey(root)
    pairs = sum(len(k) for _r, k in sv)
    print(f"world: {len(sv)} territories, {pairs} (territory, class) pairs")
    print(f"fault: a REAL implementation written by {json.load(open(BUGS / FAULT[1]))['author']} "
          f"for `{FAULT[0]}`, which its own hidden tests reject")
    print(f"suite says: {bad['why'][:110]}\n")

    t0, tried, runs = time.time(), [], 0
    for rel, kinds in sv:
        for k in kinds:
            rc, text = FN.node(root, rel, k, env)
            ruling = "SHIP" if rc == 0 else ("EMPTY" if "cannot exhibit" in text else "REFUTED")
            sr = 0
            for line in text.split("\n"):
                if line.startswith("suite_runs="):
                    sr = int(line.split("=")[1]); runs += sr
            tried.append({"rel": rel, "kind": k, "ruling": ruling, "suite_runs": sr})
            if rc == 0:
                print(f"  {rel} class {k} -> SHIP (unexpected: this fault was measured as refused)")
                return
    wall = round(time.time() - t0, 1)
    real = [t for t in tried if t["ruling"] == "REFUTED"]
    localised = sorted({t["rel"] for t in real})
    print(f"RULING    REFUTED — {len(tried)} nodes, {len(real)} of them real searches, {runs} suite runs, "
          f"{wall}s")
    print(f"          every class in the vocabulary was tried and the suite rejected every candidate")
    print(f"          the failure points at: {', '.join(localised) or '(nothing executed)'}")
    print(f"          classes ruled out in {FAULT[0]}: "
          f"{sorted(t['kind'] for t in tried if t['rel'].endswith(FAULT[0] + '.py'))}")
    STATE.write_text(json.dumps({
        "fault": FAULT[0], "author": json.load(open(BUGS / FAULT[1]))["author"],
        "territories": len(sv), "pairs": pairs, "nodes": len(tried), "real_searches": len(real),
        "suite_runs": runs, "wall_s": wall, "localised_to": localised,
        "tried": tried, "failing_output": out[-1500:], "broken_code": bad["code"],
        "tests": bad["tests"], "rel": f"pkg/{FAULT[0]}.py"}, indent=1))
    print(f"\nrecorded -> {STATE.name}. The refusal is the artefact: a localisation and a list of "
          f"everything ruled out.")


def certify(a):
    st = json.load(open(STATE))
    root = WORK / "world"
    rel = st["rel"]
    original = (root / rel).read_text()
    o = Oracle(str(root), python=PY)
    assert not o.green(), "the world is not red — re-run --phase refuse"

    results = []
    for path in a.patch:
        code = Path(path).read_text()
        (root / rel).write_text(code if code.endswith("\n") else code + "\n")
        c = FN.certify(root, rel, original, confirm=2)
        c["patch"] = Path(path).name
        c["code"] = code
        results.append(c)
        print(f"CERTIFY   {Path(path).name}: {'CERTIFIED' if c['certified'] else 'REFUSED'} — {c['why']} "
              f"({c['suite_runs']} suite runs)")
        (root / rel).write_text(original)

    st["certificates"] = [{k: v for k, v in r.items() if k != "code"} for r in results]
    passing = [r for r in results if r["certified"]]

    if len(passing) >= 2:
        print(f"\nRULING    AMB — {len(passing)} different programs both pass this suite. The suite cannot "
              f"tell them apart, so it is not entitled to pick one.")
        name = st["fault"]
        # body[0] is the model's new `from math import ceil`, not the function -- the very insertion the
        # vocabulary could not make. Find the function by name instead of by position.
        fn = differ.find_function(passing[0]["code"], name)
        arity = len(fn.args.args)
        seeds = differ.harvest_seeds(str(root), name, arity)
        probe_root = WORK / "probe"
        shutil.rmtree(probe_root, ignore_errors=True); shutil.copytree(root, probe_root)
        pool = differ.build_pool(seeds, arity)
        ra = differ.evaluate(str(probe_root), rel, passing[0]["code"], f"pkg.{name}", name, pool)
        rb = differ.evaluate(str(probe_root), rel, passing[1]["code"], f"pkg.{name}", name, pool)
        wit = None
        if "values" in ra and "values" in rb:
            for i, args in enumerate(pool):
                if i < len(ra["values"]) and i < len(rb["values"]) and ra["values"][i] != rb["values"][i]:
                    wit = {"input": args, "a": ra["values"][i], "b": rb["values"][i]}
                    break
        st["amb"] = {"passing": len(passing), "pool": len(pool), "witness": wit}
        if wit:
            print(f"SEPARATE  they diverge at {wit['input']!r}: "
                  f"{passing[0]['patch']} says {wit['a']}, {passing[1]['patch']} says {wit['b']}")
            print(f"          neither is certified. That input is where the specification never decided.")
        else:
            print(f"SEPARATE  no input in the {len(pool)}-input pool tells them apart — they may be one "
                  f"program spelled twice, which is NOT ambiguity. Certified.")
    STATE.write_text(json.dumps(st, indent=1))
    print("HANDOFF_DONE")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["refuse", "certify"], required=True)
    ap.add_argument("--patch", action="append", default=[])
    a = ap.parse_args()
    (refuse if a.phase == "refuse" else certify)(a)
