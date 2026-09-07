#!/usr/bin/env python
"""Resumable second-round retry driver (agent 17, continuation run).

measure.py --retry <file> always restarts that file's alternate list at
index 0, so it re-runs alternates already known green.  This driver reads
results.jsonl first, skips every (file, line) pair already measured, and
stops at the first alternate whose injection actually turns the suite red
(status != "green").  One file per invocation; each invocation is wrapped
by nice -n 15 + bin/timeout 300 in run_retry2.sh.

Run:  nice -n 15 bin/timeout 300 .venv/bin/python retry2.py <src/foo.c>
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure  # noqa: E402  (reuses run_one / log unchanged)


def tried_lines(rel):
    seen, red = set(), False
    p = os.path.join(HERE, "results.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line)
            if r["file"] == rel:
                seen.add(r["line"])
                if r["status"] != "green":
                    red = True
    return seen, red


def main(rel, altfile="alt_defects.json"):
    seen, already_red = tried_lines(rel)
    if already_red:
        measure.log(f"--- [retry2 {rel}] already has a red measurement; skipping")
        return
    alts = json.load(open(os.path.join(HERE, altfile))).get(rel, [])
    todo = [d for d in alts if d["line"] not in seen]
    if not todo:
        measure.log(f"--- [retry2 {rel}] no untried alternates left; UNMEASURED")
        return
    for k, d in enumerate(todo):
        measure.log(f"--- [retry2 {rel} alt L{d['line']}] {d['old']!r}->{d['new']!r}")
        rec = measure.run_one(200 + k, d)
        rec["retry2"] = True
        with open(os.path.join(HERE, "results.jsonl"), "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        measure.log(
            f"    status={rec.get('status')} body_rank={rec.get('body_rank')} "
            f"law_rank={rec.get('law_rank')} fails={rec.get('fail_tests')} {rec.get('seconds')}s"
        )
        if rec.get("status") != "green":
            return


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "alt_defects.json")
