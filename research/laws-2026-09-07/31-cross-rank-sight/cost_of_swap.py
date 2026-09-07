"""31-cross-rank-sight, probe 3: WHAT WOULD THE SWAP COST?

Consulting RANK before SIGHT is not a reordering of two calls: RANK is only
ever asked about ONE file's lines, and only after that file has been chosen.
To ask it first, the body must build a packet and observe EVERY candidate
file before any candidate is tried. This measures that up-front cost
(seconds, and suite/coverage subprocess runs) against the suite runs saved.

Usage: python cost_of_swap.py <fixture> <workdir>
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fixtures  # noqa: E402

RUNS = []


def main():
    name, work = sys.argv[1], sys.argv[2]
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    fixtures.ALL[name](work)

    import fluidfix.oracle as O
    _run = O.Oracle.run

    def run(self, *a, **kw):
        t = time.time()
        r = _run(self, *a, **kw)
        RUNS.append({"args": list(a[0]) if a else [], "cached": kw.get("cache"),
                     "s": round(time.time() - t, 3)})
        return r
    O.Oracle.run = run

    from fluidfix import MechanicalObserver, Oracle
    from fluidfix.guard import find_candidate_files, rank_observations
    from fluidfix.localize import build_packet

    oracle = Oracle(work, python=sys.executable)
    t0 = time.time()
    fails, out = oracle.failing_output()
    t_fail = time.time() - t0
    n_after_fail = len(RUNS)

    t1 = time.time()
    files = find_candidate_files(oracle, out, limit=999)
    t_sight = time.time() - t1
    n_after_sight = len(RUNS)

    observer = MechanicalObserver()
    per_file = []
    for rel in files:
        t2 = time.time()
        n0 = len(RUNS)
        p = build_packet(oracle, rel)
        if p is None:
            continue
        obs = observer.observe([p])[0]
        rank_observations("\n".join(p.src_lines), obs, out,
                          root=work, rel=rel)
        per_file.append({"file": rel, "s": round(time.time() - t2, 3),
                         "subprocess_runs": len(RUNS) - n0,
                         "observations": len(obs)})

    print(json.dumps({
        "fixture": name,
        "failing_output_s": round(t_fail, 3),
        "failing_output_runs": n_after_fail,
        "find_candidate_files_s": round(t_sight, 3),
        "find_candidate_files_runs": n_after_sight - n_after_fail,
        "files": files,
        "per_file_packet_and_rank": per_file,
        "upfront_extra_s_for_all_but_first": round(
            sum(f["s"] for f in per_file[1:]), 3),
        "upfront_extra_subprocess_runs": sum(
            f["subprocess_runs"] for f in per_file[1:]),
        "all_subprocess_runs": RUNS,
    }, indent=1))


if __name__ == "__main__":
    main()
