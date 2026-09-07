"""How big is a real bug fix? The cumulative curve, and where it crosses 50%.

fluidfix's architecture reaches: one FILE, a small number of LINES, in a shape a
taught class can express (SpanEdit already does multi-line). So the ceiling is
not "single token" — it is "how many fixes are small and local enough".

This measures the distribution and reports where the cumulative share crosses
50%, so the claim "more than half of bugs, when the classes are shaped well"
can be checked rather than asserted.
"""
import collections, re, subprocess, sys

root = sys.argv[1]
FIX = re.compile(r"fix|bug|crash|wrong|incorrect|regress|issue|broken|error", re.I)
SKIP = re.compile(r"(^|/)(test|tests|third_party|external|vendor|deps|examples?|samples?)/", re.I)

log = subprocess.run(
    ["git", "-C", root, "log", "--no-merges", "-U0", "--format=COMMIT\t%H\t%s",
     "-p", "--", "*.c", "*.cpp", "*.h", "*.hpp", "*.cc", "*.m"],
    capture_output=True, text=True, errors="replace").stdout

cur = subj = None; curfile = ""
files = set(); changed = 0; hunks = 0
rows = []

def end():
    if cur is not None and FIX.search(subj) and files:
        rows.append((len(files), hunks, changed))

for line in log.splitlines():
    if line.startswith("COMMIT\t"):
        end(); _, cur, subj = line.split("\t", 2)
        files, changed, hunks, curfile = set(), 0, 0, ""
    elif line.startswith("+++ "):
        curfile = line[4:]
    elif line.startswith("@@"):
        if curfile and not SKIP.search(curfile): hunks += 1
    elif line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
        if curfile and not SKIP.search(curfile):
            files.add(curfile); changed += 1
end()

n = len(rows) or 1
name = root.rstrip("/").rsplit("/", 1)[-1]
print(f"{name}: {n} fix commits touching source")
one_file = [r for r in rows if r[0] == 1]
print(f"  touch exactly ONE file           : {len(one_file):>5}  {100*len(one_file)/n:5.1f}%")
print(f"  ONE file AND ONE contiguous hunk : "
      f"{sum(1 for r in one_file if r[1] == 1):>5}  "
      f"{100*sum(1 for r in one_file if r[1] == 1)/n:5.1f}%")
print("  cumulative share of ALL fix commits, by changed lines in one file:")
cum = 0
for k in (1, 2, 3, 5, 8, 12, 20, 40):
    c = sum(1 for r in one_file if r[1] == 1 and r[2] <= k)
    print(f"      <= {k:>2} lines, one hunk : {c:>5}  {100*c/n:5.1f}%")
# where does one-file cross 50%?
for k in range(1, 400):
    c = sum(1 for r in one_file if r[2] <= k)
    if 100*c/n >= 50:
        print(f"  ONE file crosses 50% of all fix commits at <= {k} changed lines")
        break
else:
    c = 100*len(one_file)/n
    print(f"  ONE file NEVER reaches 50% (tops out at {c:.1f}%)")
