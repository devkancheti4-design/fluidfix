"""Independent re-derivation of `fluidfix hotspots`' headline number on Box2D.

Does NOT trust hotspots.coverage_to_reach: recomputes the cumulative-share
walk from the raw `git log` output, then cross-checks against the module.
Also reports the denominators the README/CHANGELOG use, and how many of the
counted files still exist in the working tree.

usage: python3 remeasure.py <repo> [<rev>]
"""
import collections
import os
import subprocess
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import _CODE, _FIX, _SKIP, bugfix_churn, coverage_to_reach  # noqa: E402

root = sys.argv[1]
rev = sys.argv[2] if len(sys.argv) > 2 else "HEAD"


def churn_at(rev):
    """bugfix_churn, but at an arbitrary revision (read-only, no checkout)."""
    out = subprocess.run(
        ["git", "-C", root, "log", rev, "-n4000", "--format=@@@%s",
         "--name-only"], capture_output=True, text=True,
        errors="replace", timeout=300).stdout
    churn = collections.Counter()
    scanned = fixes = 0
    is_fix = False
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("@@@"):
            scanned += 1
            is_fix = bool(_FIX.search(line[3:]))
            fixes += is_fix
            continue
        if not is_fix or not line.endswith(_CODE) or _SKIP.search(line):
            continue
        churn[line] += 1
    return churn, scanned, fixes


def files_to_reach(churn, share):
    """Independent walk: how many top files to cover `share` of all touches."""
    total = sum(churn.values())
    run = 0
    for n_files, (_f, n) in enumerate(churn.most_common(), 1):
        run += n
        if run / total >= share:
            return n_files, total
    return len(churn), total


def engine_files(root):
    """Files in the CURRENT tree that hotspots would ever count."""
    out = []
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), root)
            if rel.endswith(_CODE) and not _SKIP.search(rel):
                out.append(rel)
    return sorted(out)


churn, scanned, fixes = churn_at(rev)
mod_churn, mod_scanned, mod_fixes = bugfix_churn(root)
print(f"rev={rev}  scanned={scanned}  bugfix_commits={fixes}  "
      f"files_touched={len(churn)}  total_touches={sum(churn.values())}")
if rev == "HEAD":
    print(f"module bugfix_churn agrees: "
          f"{(mod_scanned, mod_fixes, len(mod_churn)) == (scanned, fixes, len(churn))}")

print("\nindependent walk vs hotspots.coverage_to_reach:")
mod = dict(coverage_to_reach(churn))
for share in (0.3, 0.5, 0.6, 0.8):
    n, total = files_to_reach(churn, share)
    print(f"  {share:.0%}: mine={n:4d}  module={mod[share]:4d}  "
          f"agree={n == mod[share]}")

n60, total = files_to_reach(churn, 0.6)
top = [f for f, _ in churn.most_common(n60)]
tree = set(engine_files(root))
alive = [f for f in top if os.path.exists(os.path.join(root, f))]
print(f"\n60% costs {n60} files.  denominators:")
print(f"  files that have ever broken (what the CLI prints): {len(churn)}"
      f"  -> {n60/len(churn):.0%}")
eng = engine_files(root)
print(f"  code files in the CURRENT tree (the 'engine'):      {len(eng)}"
      f"  -> {n60/len(eng):.0%}")
print(f"  of those {n60} files, still present on disk: {len(alive)}"
      f"  ({len(alive)/n60:.0%});  vanished: {n60 - len(alive)}")
gone = [f for f in top if not os.path.exists(os.path.join(root, f))]
print("  vanished sample:", gone[:8])
