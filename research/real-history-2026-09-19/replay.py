#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Replay real fixes against the maintainer's own regression test. The judge is their test, not their text.

198 mined commits fix exactly one source file AND add or change a test. Each therefore carries its own
judge, so the question can be asked properly: not "does fluidfix type what the maintainer typed", but
**does it produce something that maintainer's test accepts**.

Restricted to 2022 onward. Older revisions do not collect under a modern pytest, which is toolchain drift
rather than a result — and a guard whose coverage came back empty returns NO-OBSERVATIONS after zero suite
runs, which looks exactly like a refusal and is not one. That mistake is what this file exists to avoid, so
every case must clear three preconditions before the guard is allowed to run at all:

    COLLECTS     the suite at the parent revision collects without error
    GREEN        with the fix's test files REMOVED, the suite passes — a stable starting point
    RED          with the fix's test files ADDED, it fails — the regression test really does catch this bug

Only then is the source file handed over, with the shipped and taught vocabulary and nothing else. Anything
that fails a precondition is reported as skipped with the reason, never counted as a refusal.

  python3 replay.py <repos-root> --repo rich [--limit 50] [--since 2022]
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
# loaded in order; a later file re-registering a slot wins. rules_placed.py re-authors class 7 so the
# PLACEMENT LAW decides where the inserted token goes, instead of the applier trailing it after the paren.
DICTS = [HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py",
         HERE.parents[1] / "examples" / "taught-2026-09-18" / "kinds_from_ladder.py",
         HERE.parents[1] / "examples" / "taught-2026-09-19" / "rules_placed.py"]

GUARD = """
import sys
src, rel = sys.argv[1], sys.argv[2]
dicts = [d for d in sys.argv[3:6] if d]
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
for d in dicts:
    load_dictionary(d)
extra = sys.argv[6].split("\x01") if len(sys.argv) > 6 and sys.argv[6] else []
o = Oracle(".", python=sys.executable, timeout=600, per_test_timeout=60, extra_args=extra)
red, out = o.failing_output()
if not red:
    print("RESULT=NOT-RED"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10**9)
if pk is None:
    print("RESULT=NO-PACKET"); raise SystemExit(3)
print("executed=%d" % len(pk.lines))
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
print("observations=%d" % len(obs))
if not obs:
    print("RESULT=NO-OBSERVATIONS"); raise SystemExit(2)
res = repair(o, rel, obs)
print("suite_runs=%d" % res.suite_runs)
print("RESULT=" + ("REPAIRED" if res.repaired else "REFUSED"))
print("RULING=" + (res.ruling or ""))
"""


def sh(args, cwd=None, env=None, t=1200):
    try:
        return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=t)
    except subprocess.TimeoutExpired:
        class R: returncode, stdout, stderr = 124, "", "TIMEOUT"
        return R()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("--repo", required=True)
    ap.add_argument("--limit", type=int, default=50); ap.add_argument("--since", default="2022")
    ap.add_argument("--only", help="comma-separated sha prefixes, for re-running specific cases")
    a = ap.parse_args()

    rows = [r for r in json.load(open(HERE / "tested_fixes.json"))
            if r["repo"] == a.repo and r["date"][:4] >= a.since]
    if a.only:
        want = set(a.only.split(","))
        rows = [r for r in rows if any(r["sha"].startswith(w) for w in want)]
    rows.sort(key=lambda r: r["date"], reverse=True)
    print(f"{a.repo}: {len(rows)} fixes from {a.since} onward that ship their own regression test",
          flush=True)

    work = Path(f"/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
                f"7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/rp_{a.repo}")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(Path(a.root) / a.repo, work)
    venv = work / ".venv"
    sh([sys.executable, "-m", "venv", str(venv)])
    py = str(venv / "bin" / "python")
    # A repository's dependency set changes across its own history: rich needed `commonmark` before it
    # moved to markdown-it-py, and installing once at HEAD leaves older revisions unable to even import
    # their tests. Install the union rather than reinstalling per revision.
    sh([py, "-m", "pip", "-q", "install", "pytest", "pytest-cov", "coverage",
        "commonmark", "markdown-it-py", "pygments", "typing-extensions", "attrs"], t=1200)
    inst = sh([py, "-m", "pip", "-q", "install", "-e", "."], cwd=work, t=1200)
    print(f"environment: pip install -e . -> {'ok' if inst.returncode==0 else 'FAILED'}", flush=True)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)

    out, t0 = [], time.time()
    print(f"\n{'#':>3} {'commit':11} {'file':30} {'1L':>3}  outcome", flush=True)
    for i, r in enumerate(rows[: a.limit], 1):
        sha, rel = r["sha"], r["file"]
        rec = {"sha": sha[:10], "file": rel, "date": r["date"][:10], "subject": r["subject"],
               "one_line": r["one_line"]}
        sh(["git", "checkout", "-q", "-f", sha + "^"], cwd=work); sh(["git", "clean", "-qfd"], cwd=work)

        # A repository's own `filterwarnings = error` turns a pytest deprecation into a collection ERROR,
        # which looks exactly like "this revision is too old to run". It is not: `-W default` restores the
        # ordinary behaviour and click's suite collects 583 tests instead of none.
        BASE = ["-q", "--no-header", "-p", "no:cacheprovider", "-W", "default"]
        col = sh([py, "-m", "pytest"] + BASE + ["--collect-only"], cwd=work, t=600)
        if col.returncode != 0:
            rec["outcome"] = "SKIP-NO-COLLECT"
        else:
            g0 = sh([py, "-m", "pytest"] + BASE + ["--tb=no"], cwd=work, t=900)
            # Tests already failing at the parent revision are almost always interpreter drift, and they
            # make the suite un-greenable, so no candidate could ever be accepted. Deselect exactly those
            # and record how many were set aside.
            pre = [l.split(" ")[1] for l in g0.stdout.split("\n")
                   if l.startswith("FAILED") and len(l.split(" ")) > 1]
            desel = []
            for t_id in pre:
                desel += ["--deselect", t_id]
            rec["pre_existing_failures"] = len(pre)
            if pre:
                g0 = sh([py, "-m", "pytest"] + BASE + ["--tb=no"] + desel, cwd=work, t=900)
            if g0.returncode != 0:
                rec["outcome"] = "SKIP-BASELINE-NOT-GREEN"
            else:
                sh(["git", "checkout", sha, "--"] + r["tests"], cwd=work)
                g1 = sh([py, "-m", "pytest"] + BASE + ["--tb=no"] + desel, cwd=work, t=900)
                if g1.returncode == 0:
                    rec["outcome"] = "SKIP-TEST-DOES-NOT-CATCH"
                elif g1.returncode != 1:
                    rec["outcome"] = "SKIP-SUITE-ERROR"
                else:
                    extra = "\x01".join(["-W", "default"] + desel)
                    gr = sh([py, "-c", GUARD, str(SRC), rel, str(DICTS[0]), str(DICTS[1]), str(DICTS[2]), extra],
                            cwd=work, env=env, t=1500)
                    txt = (gr.stdout or "") + (gr.stderr or "")
                    def field(k, d=""):
                        return next((l.split("=", 1)[1] for l in txt.split("\n") if l.startswith(k + "=")), d)
                    rec["outcome"] = field("RESULT", "CRASH")
                    rec["executed"] = int(field("executed", "0") or 0)
                    rec["observations"] = int(field("observations", "0") or 0)
                    rec["suite_runs"] = int(field("suite_runs", "0") or 0)
                    rec["ruling"] = field("RULING")
        out.append(rec)
        extra = (f"  ({rec.get('suite_runs',0)} runs, {rec.get('observations',0)} obs)"
                 if rec["outcome"] in ("REPAIRED", "REFUSED", "NO-OBSERVATIONS") else "")
        print(f"{i:>3} {sha[:10]:11} {rel[-30:]:30} {'y' if r['one_line'] else '·':>3}  "
              f"{rec['outcome']}{extra}", flush=True)
        (HERE / f"replay2_{a.repo}{'_only' if a.only else ''}.json").write_text(json.dumps({"repo": a.repo, "rows": out}, indent=1))

    sh(["git", "checkout", "-q", "-f", "HEAD"], cwd=work)
    judged = [o for o in out if o["outcome"] in ("REPAIRED", "REFUSED")]
    rep = [o for o in judged if o["outcome"] == "REPAIRED"]
    print(f"\nattempted {len(out)} · judged {len(judged)} · "
          f"repaired and accepted by the maintainer's own test: {len(rep)}", flush=True)
    from collections import Counter
    for k, v in Counter(o["outcome"] for o in out).most_common():
        print(f"    {k:26} {v}", flush=True)
    print(f"{round(time.time()-t0,1)}s  REPLAY_DONE", flush=True)


if __name__ == "__main__":
    main()
