#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hand fluidfix fixes it could never have written, and adversarial ones, and see what its judge does.

Every broken program here is one a model actually wrote from prose alone (research/model-bugs-2026-09-18).
Every `true` patch is a correct implementation of the same specification written by a DIFFERENT model —
a whole-function rewrite, structurally outside anything fluidfix's line-transform vocabulary could author.
fluidfix contributes nothing but the judgment.

  PYTHONPATH=<fluidfix>/src python3 run.py [--work DIR] [--confirm 2]
"""
from __future__ import annotations

import argparse, json, sys, time
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import certify as C                                                    # noqa: E402
import patches as P                                                    # noqa: E402

BUGS = HERE.parent / "model-bugs-2026-09-18"
CLASSES = ["true", "wrong", "overfit", "flaky", "collateral", "outside-near", "outside-far"]
EXPECT = {"true": "CERTIFIED", "wrong": "refused", "overfit": "(the hole)", "flaky": "refused",
          "collateral": "refused", "outside-near": "CERTIFIED", "outside-far": "CERTIFIED"}


def load():
    """Every model-authored failure, with a correct implementation of the same spec from another model."""
    written, correct = {}, {}
    for f in sorted(BUGS.glob("written_*.json")):
        d = json.load(open(f))
        for r in d["rows"]:
            key = (d["author"].endswith("-hard"), r["name"])
            written.setdefault(key, []).append((d["author"], r))
            if r["passed"] and "haiku" in d["author"]:
                correct[key] = r["code"]
    cases = []
    for key, rows in sorted(written.items()):
        for author, r in rows:
            if r["passed"] or key not in correct:
                continue
            other = next((o["code"] for a, o in rows
                          if not o["passed"] and a != author), None)
            cases.append({"spec": r["name"], "hard": key[0], "author": author, "broken": r["code"],
                          "correct": correct[key], "asserts": r["tests"], "other_broken": other,
                          "why_it_failed": r["why"]})
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
                                      "08d7e720-11a1-4c61-9902-ed128ff506ec/scratchpad/certify")
    ap.add_argument("--confirm", type=int, default=2)
    a = ap.parse_args()
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)

    cases, report, t0 = load(), [], time.time()
    print(f"{len(cases)} bugs models actually wrote; each gets a correct implementation of the same spec "
          f"written by another model, plus adversarial patches\n", flush=True)

    for n, case in enumerate(cases, 1):
        root = work / f"case{n:02d}"
        C.build_repo(root, case["broken"], case["asserts"])
        o = C.Oracle(str(root), python=C.PY)
        green0, red_ids = C.failing_ids(o)
        red_idx = {int(t.split("_")[1]) for t in red_ids if t.startswith("test_")}
        print(f"[{n:>2}/{len(cases)}] {case['spec']:16} by {case['author']:16} "
              f"red before: {sorted(red_ids) or 'NONE'}", flush=True)
        if green0:
            print("      skipped: the suite already accepts it", flush=True)
            continue

        pset = P.make(root, case["broken"], case["correct"], case["asserts"], red_idx, case["other_broken"])
        row = {"spec": case["spec"], "author": case["author"], "hard": case["hard"],
               "red_before": sorted(red_ids), "verdicts": {}}
        for cls in CLASSES:
            if cls not in pset:
                continue
            cert = C.certify(root, pset[cls], confirm=a.confirm)
            row["verdicts"][cls] = asdict(cert)
            flag = "" if cert.rolled_back_exact else "  ROLLBACK NOT EXACT"
            print(f"      {cls:13} -> {cert.verdict:11} {cert.suite_runs} suite runs, "
                  f"{cert.seconds}s  {cert.why[:64]}{flag}", flush=True)

        # ---- UNIQUE: two patches that both pass. Does fluidfix's differ tell them apart?
        row["separation"] = {}
        for rival in ("overfit", "outside-near", "outside-far"):
            if rival not in pset or row["verdicts"].get(rival, {}).get("verdict") != "CERTIFIED":
                continue
            if row["verdicts"].get("true", {}).get("verdict") != "CERTIFIED":
                continue
            name, _ = P.fn_name_arity(case["correct"])
            sep = C.separate(root, name, pset["true"], pset[rival], work / f"case{n:02d}_probe")
            row["separation"][rival] = sep
            got = "AMBIGUOUS — refuse both" if sep.get("witness") is not None else "no witness: certified alone"
            print(f"      unique vs {rival:13} pool={sep.get('pool')} -> {got}"
                  f"{'  at ' + repr(sep['witness']) if sep.get('witness') is not None else ''}", flush=True)
        report.append(row)

    (HERE / "certify_results.json").write_text(json.dumps(report, indent=1))

    # ---------------------------------------------------------------- the tally
    print("\n" + "=" * 96)
    tally = {}
    for r in report:
        for cls, v in r["verdicts"].items():
            t = tally.setdefault(cls, {})
            t[v["verdict"]] = t.get(v["verdict"], 0) + 1
    print(f"{'patch class':14} {'expected':12} verdicts")
    for cls in CLASSES:
        if cls in tally:
            print(f"{cls:14} {EXPECT[cls]:12} " +
                  ", ".join(f"{k} {v}" for k, v in sorted(tally[cls].items(), key=lambda kv: -kv[1])))
    bad = [(r["spec"], c) for r in report for c, v in r["verdicts"].items() if not v["rolled_back_exact"]]
    print(f"\nrollback byte-exact on every refusal: {'YES' if not bad else 'NO -> ' + str(bad)}")
    runs = sum(v["suite_runs"] for r in report for v in r["verdicts"].values())
    print(f"{runs} suite runs, {round(time.time() - t0, 1)}s total")
    print("CERTIFY_DONE")


if __name__ == "__main__":
    main()
