#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The real test: replay a maintainer's own regression test against the bug, and let fluidfix try.

String-matching the committed line was the wrong question twice over. It demanded fluidfix reproduce the
maintainer's exact characters, when all it has to do is produce a line THE TESTS ACCEPT — and it drew on a
corpus biased toward fixes too trivial to ship a test.

198 of the mined commits fix one source file AND add or change a test. Those carry their own judge, so the
whole thing can be run for real:

    checkout the PARENT commit                      the bug, as it shipped
    take ONLY the test files from the fix commit    the maintainer's own regression test
    confirm the suite is now RED                    the test really does catch this bug
    hand the source file to fluidfix                shipped + taught vocabulary, nothing else
    the suite decides                               and the tree is restored either way

Nothing here is compared to what the maintainer typed. A repair counts when the test that caught the bug
accepts it.

  python3 run_real.py <repos-root> --repo python-sortedcontainers [--limit 12]
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
DICTS = [HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py",
         HERE.parents[1] / "examples" / "taught-2026-09-18" / "kinds_from_ladder.py"]

GUARD = """
import sys
src, rel, d1, d2 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
for d in (d1, d2):
    if d: load_dictionary(d)
o = Oracle(".", python=sys.executable, timeout=240)
red, out = o.failing_output()
if not red:
    print("RESULT=NOT-RED"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10**9)
if pk is None:
    print("RESULT=NO-PACKET"); raise SystemExit(3)
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
if not obs:
    print("RESULT=NO-OBSERVATIONS"); raise SystemExit(2)
res = repair(o, rel, obs)
print(f"suite_runs={res.suite_runs}")
print("RESULT=" + ("REPAIRED" if res.repaired else "REFUSED"))
print("RULING=" + (res.ruling or ""))
"""


def sh(args, cwd=None, env=None, t=900):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("--repo", required=True)
    ap.add_argument("--limit", type=int, default=12); ap.add_argument("--work", default=None)
    a = ap.parse_args()

    rows = [r for r in json.load(open(HERE / "remine.json"))["rows"]
            if r["repo"] == a.repo and r["tests"]]
    print(f"{a.repo}: {len(rows)} fix commits that ship their own regression test\n")

    work = Path(a.work or f"/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
                          f"7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/replay_{a.repo}")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(Path(a.root) / a.repo, work)
    venv = work / ".venv"
    sh([sys.executable, "-m", "venv", str(venv)])
    py = str(venv / "bin" / "python")
    # pytest-cov is not optional here: build_packet ranks EXECUTED lines, and without coverage the
    # packet comes back empty and every case returns NO-OBSERVATIONS. The first run of this file
    # did exactly that and looked like a result.
    sh([py, "-m", "pip", "-q", "install", "pytest", "pytest-cov", "coverage"], t=900)
    sh([py, "-m", "pip", "-q", "install", "-e", "."], cwd=work, t=900)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)

    out, t0 = [], time.time()
    print(f"{'commit':12} {'file':34} {'baseline':>10}  outcome")
    for r in rows[: a.limit]:
        sha, rel = r["sha"], r["file"]
        sh(["git", "checkout", "-q", "-f", sha + "^"], cwd=work)
        sh(["git", "clean", "-qfd"], cwd=work)
        got = sh(["git", "checkout", sha, "--"] + r["tests"], cwd=work)
        if got.returncode != 0:
            out.append({"sha": sha[:10], "outcome": "TEST-CHECKOUT-FAILED"}); continue
        base = sh([py, "-m", "pytest", "-x", "-q", "--no-header", "-p", "no:cacheprovider"] + r["tests"],
                  cwd=work, t=600)
        if base.returncode == 0:
            print(f"{sha[:10]:12} {rel[-34:]:34} {'GREEN':>10}  skipped — the test does not catch it here")
            out.append({"sha": sha[:10], "file": rel, "outcome": "BASELINE-GREEN"}); continue
        if base.returncode in (2, 3, 4, 5):
            print(f"{sha[:10]:12} {rel[-34:]:34} {'ERROR':>10}  skipped — suite will not run at this revision")
            out.append({"sha": sha[:10], "file": rel, "outcome": "BASELINE-ERROR"}); continue

        g = sh([py, "-c", GUARD, str(SRC), rel, str(DICTS[0]), str(DICTS[1])], cwd=work, env=env, t=900)
        txt = (g.stdout or "") + (g.stderr or "")
        verdict = next((l.split("=", 1)[1] for l in txt.split("\n") if l.startswith("RESULT=")), "CRASH")
        runs = next((l.split("=", 1)[1] for l in txt.split("\n") if l.startswith("suite_runs=")), "0")
        mark = {"REPAIRED": "REPAIRED — the maintainer's own test accepts it"}.get(verdict, verdict.lower())
        print(f"{sha[:10]:12} {rel[-34:]:34} {'RED':>10}  {mark} ({runs} suite runs)")
        out.append({"sha": sha[:10], "file": rel, "subject": r["subject"], "one_line": r["one_line"],
                    "outcome": verdict, "suite_runs": int(runs or 0)})

    sh(["git", "checkout", "-q", "-f", "HEAD"], cwd=work)
    ran = [o for o in out if o["outcome"] in ("REPAIRED", "REFUSED", "NO-OBSERVATIONS")]
    rep = [o for o in ran if o["outcome"] == "REPAIRED"]
    print(f"\njudged: {len(ran)} of {min(a.limit, len(rows))} attempted "
          f"({len(out)-len(ran)} skipped: baseline green, or the suite would not run)")
    print(f"repaired, accepted by the maintainer's own regression test: {len(rep)} of {len(ran)}")
    (HERE / f"replay_{a.repo}.json").write_text(json.dumps({"repo": a.repo, "rows": out}, indent=1))
    print(f"{round(time.time()-t0,1)}s  REPLAY_DONE")


if __name__ == "__main__":
    main()
