#!/usr/bin/env python
"""08-engine-monotonicity: does a bit the body OBSERVES mid-search reach the
byte the SHIP ruling is made on?

loop.py:381-395 measures HIDDEN per candidate (green once, red on re-check),
rules decide(situation(HIDDEN=True)) for the message only, and drops the
candidate. loop.py:217 then rules on BUILT/AMB/CAPPED alone. The law rules
BUILT+HIDDEN -> CHANGE_GRANULARITY (a refusal); BUILT -> SHIP.

Fixture: one candidate set [K = 1, K = 2]; K=1 always green, K=2 green
with p=0.5 per run. With FLUIDFIX_CONFIRM=1 (default) the expected trial
outcomes are: K=2 red first run (p=.5) -> SHIP with no HIDDEN seen;
K=2 green then red on re-check (p=.25) -> HIDDEN observed, then SHIP on a
byte that says BUILT only; K=2 green twice (p=.25) -> AMB refusal.

Run:  nice -n 15 perl -e 'alarm 300; exec @ARGV' .venv/bin/python hidden_dropped.py
Writes nothing outside this directory.
"""
import os
import re
import shutil
import sys
from collections import Counter

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import MechanicalObserver, Oracle, guard_once  # noqa: E402
from fluidfix.acts import register  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "fixtures", "hidden_dropped")
N = int(os.environ.get("TRIALS", "24"))

SRC = "K = 0\n\ndef f():\n    return K\n"
TEST = ("import random\nfrom mod import f\n\n"
        "def test_f():\n    v = f()\n    assert v >= 1\n"
        "    if v == 2 and random.random() < 0.5:\n"
        "        assert False, 'flake'\n")


def main() -> None:
    register(4, "hidden-demo", "two candidates, second one flaky-green",
             re.compile(r"K = "), lambda line, o: ["K = 1", "K = 2"])
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    tally = Counter()
    lines = [f"FLUIDFIX_CONFIRM={os.environ.get('FLUIDFIX_CONFIRM', '(unset -> 1)')}, trials={N}"]
    sample_why = None
    for i in range(N):
        d = os.path.join(WORK, f"run_{i:02d}")
        os.makedirs(d)
        with open(os.path.join(d, "mod.py"), "w") as f:
            f.write(SRC)
        with open(os.path.join(d, "test_mod.py"), "w") as f:
            f.write(TEST)
        oracle = Oracle(d, python=sys.executable)
        rep = guard_once(oracle, MechanicalObserver())
        res = rep.result
        hidden_seen = any("HIDDEN" in (e.get("why") or "") for e in (res.tried_log if res else []))
        if hidden_seen and sample_why is None:
            sample_why = next(e["why"] for e in res.tried_log if "HIDDEN" in e["why"])
        new_line = (res.new_line or "").strip() if res else ""
        key = (rep.status, "HIDDEN observed" if hidden_seen else "no HIDDEN", new_line or "-")
        tally[key] += 1
        lines.append(f"run_{i:02d}: status={rep.status} hidden_seen={hidden_seen} "
                     f"greens={len(res.greens) if res else 0} new_line={new_line!r} "
                     f"reason={(res.reason if res else rep.hint)[:90]!r}")
    lines.append("")
    lines.append("tally (status, HIDDEN observed in tried_log?, shipped line):")
    for k, v in sorted(tally.items()):
        lines.append(f"  {v:3d}  {k}")
    if sample_why:
        lines.append("")
        lines.append("one HIDDEN `why` as logged (the ruling reaches only this string):")
        lines.append("  " + sample_why[:300])
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(HERE, "hidden_dropped.out"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
