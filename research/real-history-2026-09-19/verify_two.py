#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Re-run the two repairs and check WHAT they changed — 22 to 24 tests were deselected, so the judge was
weakened, and a repair a weakened suite accepts is worth less than one it does not.

Both maintainer fixes land inside the vocabulary:
    rich/segment.py    len(text)          ->  (len(text) - 1)     taught class 7, learned on click
    rich/traceback.py  frame_index == 1   ->  frame_index == 0    shipped class 1
so the question is whether fluidfix produced those exact lines or merely something the thinned suite let
through. This prints the diff it actually shipped, and compares it to the maintainer's.
"""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
REPOS = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
             "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/repos")
WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/rp_rich")
DICTS = [HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py",
         HERE.parents[1] / "examples" / "taught-2026-09-18" / "kinds_from_ladder.py"]

GUARD = """
import sys
src, rel, d1, d2 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
extra = sys.argv[5].split("\\x01") if len(sys.argv) > 5 and sys.argv[5] else []
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary, KINDS
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
for d in (d1, d2):
    if d: load_dictionary(d)
o = Oracle(".", python=sys.executable, timeout=600, per_test_timeout=60, extra_args=extra)
red, out = o.failing_output()
pk = build_packet(o, rel, max_lines=10**9)
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
res = repair(o, rel, obs)
print("REPAIRED=%s" % bool(res.repaired))
print(res.summary())
"""


def sh(a, cwd=None, env=None, t=1800):
    return subprocess.run(a, cwd=cwd, env=env, capture_output=True, text=True, timeout=t)


py = str(WORK / ".venv" / "bin" / "python")
env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
rows = {r["sha"][:10]: r for r in json.load(open(HERE / "tested_fixes.json"))}

for sha10 in ("aa0929298b", "83af951663"):
    r = rows[sha10]
    sha, rel = r["sha"], r["file"]
    print(f"\n{'='*78}\n{sha10}  {rel}  —  {r['subject'][:50]}")
    want = sh(["git", "show", "--format=", "-U0", sha, "--", rel], cwd=REPOS / "rich").stdout
    print("the maintainer's fix:")
    for l in want.split("\n"):
        if l[:1] in "+-" and l[1:2] not in "+-":
            print("   ", l.strip()[:90])

    sh(["git", "checkout", "-q", "-f", sha + "^"], cwd=WORK); sh(["git", "clean", "-qfd"], cwd=WORK)
    BASE = ["-q", "--no-header", "-p", "no:cacheprovider", "-W", "default"]
    g0 = sh([py, "-m", "pytest"] + BASE + ["--tb=no"], cwd=WORK)
    pre = [l.split(" ")[1] for l in g0.stdout.split("\n") if l.startswith("FAILED") and len(l.split(" ")) > 1]
    desel = [x for t in pre for x in ("--deselect", t)]
    sh(["git", "checkout", sha, "--"] + r["tests"], cwd=WORK)
    before = (WORK / rel).read_text()

    g = sh([py, "-c", GUARD, str(SRC), rel, str(DICTS[0]), str(DICTS[1]),
            "\x01".join(["-W", "default"] + desel)], cwd=WORK, env=env)
    after = (WORK / rel).read_text()
    print(f"deselected {len(pre)} pre-existing failures")
    print("what fluidfix shipped:")
    if before == after:
        print("    (file unchanged — rolled back)")
    else:
        import difflib
        for l in difflib.unified_diff(before.split("\n"), after.split("\n"), lineterm="", n=0):
            if l[:1] in "+-" and l[1:2] not in "+-":
                print("   ", l.strip()[:90])
    tail = [l for l in (g.stdout or "").split("\n") if l.strip()][-3:]
    print("   ", " | ".join(tail)[:150])
    sh(["git", "checkout", "-q", "-f", sha + "^"], cwd=WORK); sh(["git", "clean", "-qfd"], cwd=WORK)
print("\nVERIFY_DONE")
