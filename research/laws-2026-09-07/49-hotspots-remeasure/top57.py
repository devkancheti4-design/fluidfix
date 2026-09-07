"""Dump the 57 files coverage_to_reach() counts for the 60% claim, marking
which exist in the working tree, and recompute the claim over EXTANT files
only (the universe rank_hotspots actually reports)."""
import os
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import bugfix_churn, coverage_to_reach  # noqa: E402
import collections  # noqa: E402

root = sys.argv[1]
churn, scanned, fixes = bugfix_churn(root)
top = churn.most_common(57)
print("rank count exists file")
for i, (f, n) in enumerate(top, 1):
    print(f"{i:4d} {n:5d} {'Y' if os.path.exists(os.path.join(root,f)) else '.'}      {f}")

alive = collections.Counter({f: n for f, n in churn.items()
                             if os.path.exists(os.path.join(root, f))})
dead = collections.Counter({f: n for f, n in churn.items()
                            if not os.path.exists(os.path.join(root, f))})
print(f"\nall history:   {len(churn):4d} files, {sum(churn.values()):5d} touches")
print(f"  extant:      {len(alive):4d} files, {sum(alive.values()):5d} touches")
print(f"  vanished:    {len(dead):4d} files, {sum(dead.values()):5d} touches")
print("\nsame claim recomputed over EXTANT files only:")
for share, n in coverage_to_reach(alive):
    print(f"  guard {share:.0%} -> test {n:3d} files "
          f"({n/len(alive):.0%} of the {len(alive)} extant files that ever broke)")
