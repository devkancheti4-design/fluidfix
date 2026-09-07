"""The TEACHABLE ceiling, not the shipped vocabulary's share.

recurrence.py asked "how many fixes match the six classes fluidfix ships".
That is the wrong denominator for what the tool can do, because a class is
TAUGHT: register() one worked example and its whole family becomes repairable,
including values the vocabulary has never seen.

So this asks the bigger question: how many real bug fixes are a SINGLE LINE at
all — the shape a single-edit search can reach, whatever the token turns out to
be — and how many of those change only one token, of ANY kind.
"""
import collections, difflib, re, subprocess, sys

root = sys.argv[1]
TOK = re.compile(r"[A-Za-z_]\w*|\d+\.?\d*[fF]?|>=|<=|==|!=|&&|\|\||<<|>>|[-+*/<>=!&|^%(),;\[\]{}.]")
FIX = re.compile(r"fix|bug|crash|wrong|incorrect|regress|issue|broken|error", re.I)
SKIP = re.compile(r"(^|/)(test|tests|third_party|external|vendor|deps|examples?|samples?)/", re.I)

log = subprocess.run(
    ["git", "-C", root, "log", "--no-merges", "-U0", "--format=COMMIT\t%H\t%s",
     "-p", "--", "*.c", "*.cpp", "*.h", "*.hpp", "*.cc", "*.m"],
    capture_output=True, text=True, errors="replace").stdout

cur = subj = None; curfile = ""; minus = []; plus = []
stats = collections.Counter(); kinds = collections.Counter()
per_commit_single_line = False; per_commit_single_token = False

def flush():
    global per_commit_single_line, per_commit_single_token
    if cur is None or SKIP.search(curfile or ""):
        return
    if len(minus) == 1 and len(plus) == 1:
        per_commit_single_line = True
        ta, tb = TOK.findall(minus[0]), TOK.findall(plus[0])
        if ta and tb and ta != tb:
            ops = [o for o in difflib.SequenceMatcher(None, ta, tb).get_opcodes()
                   if o[0] != "equal"]
            if len(ops) == 1:
                tag, i1, i2, j1, j2 = ops[0]
                if max(i2 - i1, j2 - j1) == 1:
                    per_commit_single_token = True
                    x = (ta[i1:i2] or [""])[0]; y = (tb[j1:j2] or [""])[0]
                    kinds[f"{x or '(none)'} -> {y or '(none)'}"] += 1

def endcommit():
    global per_commit_single_line, per_commit_single_token
    flush()
    if cur is not None:
        isfix = bool(FIX.search(subj))
        stats["commits"] += 1
        if isfix:
            stats["fix"] += 1
            # a fix whose ENTIRE source change is one line (one hunk, one line)
            if per_commit_single_line and hunks == 1:
                stats["fix_1line"] += 1
                if per_commit_single_token:
                    stats["fix_1token"] += 1
    per_commit_single_line = per_commit_single_token = False

hunks = 0
for line in log.splitlines():
    if line.startswith("COMMIT\t"):
        endcommit(); _, cur, subj = line.split("\t", 2); minus = []; plus = []; hunks = 0
    elif line.startswith("+++ "):
        curfile = line[4:]
    elif line.startswith("@@"):
        flush(); minus = []; plus = []; hunks += 1
    elif line.startswith("+") and not line.startswith("+++"): plus.append(line[1:])
    elif line.startswith("-") and not line.startswith("---"): minus.append(line[1:])
endcommit()

name = root.rstrip("/").rsplit("/", 1)[-1]
f = stats["fix"] or 1
print(f"{name}: {stats['commits']} source commits, {stats['fix']} fix-worded")
print(f"  fix commits whose WHOLE source change is ONE LINE : {stats['fix_1line']:>5}"
      f"  ({100*stats['fix_1line']/f:.1f}% of fixes)")
print(f"  ...of which the change is ONE TOKEN, ANY kind     : {stats['fix_1token']:>5}"
      f"  ({100*stats['fix_1token']/f:.1f}% of fixes)")
print("  the ten commonest single-token substitutions (NOT limited to shipped classes):")
for k, n in kinds.most_common(10):
    print(f"      {n:>4}  {k}")
