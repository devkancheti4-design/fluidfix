"""Two sensitivity questions.

A. How much does the headline "60% -> N files" move as HEAD moves? The record
   says 1,383 commits; this clone has 1,377. If N is stable, 57 vs the recorded
   58 is not drift; if N wobbles by 1-2 over a handful of commits, it is.

B. hotspots.py's own docstring records a DIFFERENT run (207 bug-fix commits,
   201 files, 60% -> 61) than CHANGELOG/README (60% -> 58). Can any narrower
   _FIX regex reproduce 207/201 on this history?
"""
import collections
import re
import subprocess
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import _CODE, _FIX, _SKIP, coverage_to_reach  # noqa: E402

root = sys.argv[1]
LOG = subprocess.run(
    ["git", "-C", root, "log", "-n4000", "--format=@@@%s", "--name-only"],
    capture_output=True, text=True, errors="replace", timeout=300).stdout


def churn_from(text, fix_re=_FIX):
    churn = collections.Counter()
    scanned = fixes = 0
    is_fix = False
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("@@@"):
            scanned += 1
            is_fix = bool(fix_re.search(line[3:]))
            fixes += is_fix
            continue
        if not is_fix or not line.endswith(_CODE) or _SKIP.search(line):
            continue
        churn[line] += 1
    return churn, scanned, fixes


print("A. headline vs how far back HEAD sits (rev = HEAD~k)")
print("   k  commits  fixes  files   30%   50%   60%   80%")
for k in (0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50):
    text = subprocess.run(
        ["git", "-C", root, "log", f"HEAD~{k}" if k else "HEAD", "-n4000",
         "--format=@@@%s", "--name-only"], capture_output=True, text=True,
        errors="replace", timeout=300).stdout
    ch, sc, fx = churn_from(text)
    d = dict(coverage_to_reach(ch))
    print(f"  {k:2d}  {sc:7d}  {fx:5d}  {len(ch):5d}  "
          f"{d[0.3]:4d}  {d[0.5]:4d}  {d[0.6]:4d}  {d[0.8]:4d}")

print("\nB. can a narrower _FIX reproduce the docstring's 207 fixes / 201 files?")
cands = {
    "shipped _FIX": _FIX,
    r"\bfix(e[sd])?\b": re.compile(r"\bfix(e[sd])?\b", re.I),
    r"^fix": re.compile(r"^\s*fix", re.I),
    r"\bfix(e[sd])?|bug\b": re.compile(r"\b(fix(e[sd])?|bug)\b", re.I),
    r"\bfix|bug|crash\b": re.compile(r"\b(fix(e[sd])?|bug|crash)\b", re.I),
}
for name, rx in cands.items():
    ch, sc, fx = churn_from(LOG, rx)
    d = dict(coverage_to_reach(ch))
    print(f"  {name:28s} fixes={fx:4d} files={len(ch):4d} "
          f"60%->{d[0.6]:4d}  (docstring wants fixes=207 files=201 60%->61)")
