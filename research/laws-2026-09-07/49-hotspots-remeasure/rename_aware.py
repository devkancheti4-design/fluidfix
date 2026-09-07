"""hotspots' churn, but with git rename detection ON.

bugfix_churn uses `git log --name-only`, which does NOT follow renames, so one
logical file appears under every path it has ever had. This replays the same
log with `--name-status -M` and canonicalises every historical path forward to
the name it carries at HEAD, then recomputes the same headline number.
"""
import collections
import os
import subprocess
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import _CODE, _FIX, _SKIP, coverage_to_reach  # noqa: E402

root = sys.argv[1]
out = subprocess.run(
    ["git", "-C", root, "log", "-n4000", "--format=@@@%s", "--name-status",
     "-M"], capture_output=True, text=True, errors="replace",
    timeout=300).stdout

cur: dict[str, str] = {}          # historical path -> present-day path
churn: collections.Counter = collections.Counter()
scanned = fixes = renames = 0
is_fix = False
for line in out.split("\n"):
    if not line.strip():
        continue
    if line.startswith("@@@"):
        scanned += 1
        is_fix = bool(_FIX.search(line[3:]))
        fixes += is_fix
        continue
    parts = line.split("\t")
    st = parts[0]
    if st.startswith("R") and len(parts) >= 3:
        old, new = parts[1], parts[2]
        renames += 1
        cur[old] = cur.get(new, new)          # walking newest -> oldest
        path = old
    else:
        path = parts[-1]
    if not is_fix:
        continue
    canon = cur.get(path, path)
    if not canon.endswith(_CODE) or _SKIP.search(canon):
        continue
    churn[canon] += 1

alive = {f: n for f, n in churn.items()
         if os.path.exists(os.path.join(root, f))}
print(f"scanned={scanned} bugfix_commits={fixes} rename_records={renames}")
print(f"rename-aware churn: {len(churn)} files, {sum(churn.values())} touches")
print(f"  of which still on disk: {len(alive)} files, "
      f"{sum(alive.values())} touches")
print("\nheadline recomputed, rename-aware, all paths:")
for share, n in coverage_to_reach(collections.Counter(churn)):
    print(f"  guard {share:.0%} -> test {n:3d} files "
          f"({n/len(churn):.0%} of {len(churn)})")
print("\nheadline recomputed, rename-aware, files that EXIST today:")
for share, n in coverage_to_reach(collections.Counter(alive)):
    print(f"  guard {share:.0%} -> test {n:3d} files "
          f"({n/len(alive):.0%} of {len(alive)})")
print("\ntop 12 rename-aware, extant:")
for f, n in collections.Counter(alive).most_common(12):
    print(f"  {n:4d}  {f}")
