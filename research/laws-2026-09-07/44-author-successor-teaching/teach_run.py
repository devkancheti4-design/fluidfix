#!/usr/bin/env python3
"""teach_run.py <site> <dictfile> [--pin]

Stage-2: the end-to-end teaching claim, suite as judge.

Injects the historical defect into the cglm copy, loads the dictionary that
was taught from THAT one worked example, and runs one C guard pass.

--pin replaces the C file-localiser with an oracle-perfect one that returns
the true defect file. It changes nothing about the taught class; it isolates
"did the taught class repair it" from "did SIGHT find the file", which is
the distinction the brief asks for. Without --pin the shipped localiser runs.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from inject import flip                                    # noqa: E402
from sites import SITES                                    # noqa: E402

from fluidfix import ACTS, KINDS, MechanicalObserver        # noqa: E402
from fluidfix import coracle                                # noqa: E402
from fluidfix.acts import load_dictionary                   # noqa: E402

ROOT = HERE / "cglm"


def main():
    site, dictfile = sys.argv[1], sys.argv[2]
    pin = "--pin" in sys.argv
    budget = int(next((a.split("=")[1] for a in sys.argv
                       if a.startswith("--budget=")), 300))
    s = SITES[site]
    saved = dict(KINDS), dict(ACTS)
    assert flip(site, "defect") == 0
    try:
        if dictfile != "none":
            n = load_dictionary(str(HERE / "dicts" / dictfile))
            print(f"dictionary {dictfile}: {n} class(es) registered")
        if pin:
            coracle.find_candidate_files_c = lambda o, out, limit=5: [s["file"]]
            print(f"SIGHT pinned to {s['file']}")
        oracle = coracle.COracle(str(ROOT), build_cmd="cmake --build build -j4",
                                 test_cmd="./build/tests", timeout=300)
        t0 = time.time()
        rep = coracle.cguard_once(oracle, MechanicalObserver(), budget=budget)
        print(f"STATUS={rep.status}  seconds={time.time() - t0:.1f}")
        print(rep.summary()[:900])
        line = (ROOT / s["file"]).read_text().split("\n")
        print("line now:", next((l for l in line
                                 if l in (s['fixed'], s['defect'])), "?"))
        print("REPAIRED_CORRECTLY=",
              s["fixed"] in (ROOT / s["file"]).read_text())
    finally:
        KINDS.clear(); KINDS.update(saved[0])
        ACTS.clear(); ACTS.update(saved[1])
        flip(site, "fixed")


if __name__ == "__main__":
    main()
