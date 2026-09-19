#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Would fluidnet's CERTIFY gates have caught the two false accepts? replay.py never ran them.

replay.py called `repair()` directly, which accepts a candidate the moment the suite goes green once. That
is one fluidfix guard, not fluidnet: no survey, no growth by ruling, no memory — and no certificate. The
certificate is six gates, and two of them are aimed exactly at what happened here:

    STABLE         the green must repeat on independent re-runs
    NO-COLLATERAL  every test green before must still be green after
    UNIQUE         no rival candidate that also passes but behaves differently

The second patch changed a padding tuple in a different part of the file, and the first put a `- 1` outside
a multiplication instead of inside it. Whether the gates see that is a fact, not an opinion.
"""
import difflib, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
WORK = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
            "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/rp_rich")
py = str(WORK / ".venv" / "bin" / "python")

CASES = {
 "aa0929298b": ("rich/segment.py", 122,
                "        pos = int((cut / cell_length) * len(text))",
                "        pos = int((cut / cell_length) * len(text) - 1)"),
 "83af951663": ("rich/traceback.py", 452,
                "                    padding=(0, 1),",
                "                    padding=(0, 0),"),
}


def sh(a, cwd=None, t=1800):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True, timeout=t)


rows = {r["sha"][:10]: r for r in json.load(open(HERE / "tested_fixes.json"))}
BASE = ["-q", "--no-header", "-p", "no:cacheprovider", "-W", "default"]

for sha10, (rel, lineno, before, after) in CASES.items():
    r = rows[sha10]
    print(f"\n{'='*76}\n{sha10}  {rel}")
    sh(["git", "checkout", "-q", "-f", r["sha"] + "^"], cwd=WORK); sh(["git", "clean", "-qfd"], cwd=WORK)
    g0 = sh([py, "-m", "pytest"] + BASE + ["--tb=no"], cwd=WORK)
    pre = {l.split(" ")[1] for l in g0.stdout.split("\n") if l.startswith("FAILED") and len(l.split(" ")) > 1}
    desel = [x for t in pre for x in ("--deselect", t)]
    sh(["git", "checkout", r["sha"], "--"] + r["tests"], cwd=WORK)

    # RED before, with the maintainer's regression test in place
    red = sh([py, "-m", "pytest"] + BASE + ["--tb=no"] + desel, cwd=WORK)
    redfail = {l.split(" ")[1] for l in red.stdout.split("\n") if l.startswith("FAILED") and len(l.split(" ")) > 1}
    print(f"  RED BEFORE      {'yes' if red.returncode == 1 else 'NO'}  "
          f"({len(redfail)} failing, {len(pre)} pre-existing deselected)")

    src = Path(WORK / rel)
    original = src.read_text()
    lines = original.split("\n")
    assert lines[lineno-1].rstrip() == before.rstrip(), f"line moved: {lines[lineno-1]!r}"
    lines[lineno-1] = after
    src.write_text("\n".join(lines))

    # GREEN AFTER, on the full deselected suite
    runs = []
    for i in range(3):
        g = sh([py, "-m", "pytest"] + BASE + ["--tb=no"] + desel, cwd=WORK)
        fails = {l.split(" ")[1] for l in g.stdout.split("\n")
                 if l.startswith("FAILED") and len(l.split(" ")) > 1}
        runs.append((g.returncode == 0, fails))
    print(f"  GREEN AFTER     {'yes' if runs[0][0] else 'NO'}")
    print(f"  STABLE          {'yes' if all(x[0] for x in runs) else 'NO — green did not repeat'} "
          f"({sum(x[0] for x in runs)}/3 re-runs green)")
    collateral = (runs[0][1] - redfail) if not runs[0][0] else set()
    print(f"  NO-COLLATERAL   {'yes' if not collateral else 'NO — broke ' + ', '.join(sorted(collateral))[:60]}")

    # UNIQUE: is there a rival candidate at this line that ALSO passes?
    import re as _re
    rivals = []
    if "len(text)" in before:
        rivals = ["        pos = int((cut / cell_length) * (len(text) - 1))"]
    else:
        rivals = ["                    padding=(0, 1),".replace("(0, 1)", "(1, 1)")]
    hits = []
    for rv in rivals:
        lines2 = original.split("\n"); lines2[lineno-1] = rv
        src.write_text("\n".join(lines2))
        g = sh([py, "-m", "pytest"] + BASE + ["--tb=no"] + desel, cwd=WORK)
        if g.returncode == 0:
            hits.append(rv.strip())
    print(f"  UNIQUE          {'NO — a rival also passes: ' + hits[0][:52] if hits else 'no rival found at this line'}")
    src.write_text(original)
    print(f"  ROLLBACK        {'byte-exact' if src.read_text() == original else 'FAILED'}")
    sh(["git", "checkout", "-q", "-f", r["sha"] + "^"], cwd=WORK); sh(["git", "clean", "-qfd"], cwd=WORK)

print("\nCERTIFY_TWO_DONE")
