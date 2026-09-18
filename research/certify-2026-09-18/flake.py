#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What does the re-check actually buy? A green that does not repeat, measured at four confirm levels.

STABLE is the cheapest of the certificate's properties to claim and the easiest to fake, so it is the one
worth measuring rather than asserting. A patch is correct except that it raises on a small fraction of its
calls — the shape of a real intermittent fault: a clock, an ordering, a hash seed, a network stub. A single
suite run accepts it whenever the flake happens not to fire.

`FLUIDFIX_CONFIRM` sets how many FINE observations are taken before a coarse green is trusted. This measures
the false-accept rate at 0, 1, 2 and 4 on the same patch, so the flag's cost and its value are both visible.

  PYTHONPATH=<fluidfix>/src python3 flake.py [--trials 20]
"""
from __future__ import annotations

import argparse, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import certify as C                                                    # noqa: E402

BUGS = HERE.parent / "model-bugs-2026-09-18"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--work", default="/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
                                      "08d7e720-11a1-4c61-9902-ed128ff506ec/scratchpad/certify_flake")
    a = ap.parse_args()

    hard = json.load(open(BUGS / "written_phi4-mini-hard.json"))
    good = json.load(open(BUGS / "written_haiku-hard.json"))
    bug = next(r for r in hard["rows"] if r["name"] == "windows" and not r["passed"])
    fix = next(r for r in good["rows"] if r["name"] == "windows")["code"]

    root = Path(a.work)
    C.build_repo(root, bug["code"], bug["tests"])
    print(f"case: windows (phi4-mini), {len(bug['tests'])} tests; a correct patch that raises on a "
          f"fraction of calls\n", flush=True)

    rows, t0 = [], time.time()
    print(f"{'flake/call':>11}  {'confirm=0':>10} {'confirm=1':>10} {'confirm=2':>10} {'confirm=4':>10}"
          "   (false accepts out of %d)" % a.trials, flush=True)
    for p in (0.02, 0.05, 0.10, 0.25):
        patch = ("import random as _ffr\n" + fix.rstrip("\n") + "\n\n_ff_inner = windows\n\n\n"
                 "def windows(*a, **k):\n"
                 f"    if _ffr.random() < {p}:\n"
                 "        raise RuntimeError('intermittent')\n"
                 "    return _ff_inner(*a, **k)\n")
        line, row = [], {"p": p}
        for confirm in (0, 1, 2, 4):
            accepted = sum(C.certify(root, patch, confirm=confirm).ok for _ in range(a.trials))
            row[f"confirm{confirm}"] = accepted
            line.append(f"{accepted:>10}")
        rows.append(row)
        print(f"{p:>11.0%}  " + " ".join(line), flush=True)

    (HERE / "flake_results.json").write_text(json.dumps({"trials": a.trials, "rows": rows}, indent=1))
    print(f"\n{round(time.time() - t0, 1)}s. A false accept is a patch that raises intermittently and was "
          f"nevertheless certified.\nFLAKE_DONE")


if __name__ == "__main__":
    main()
