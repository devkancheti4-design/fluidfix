import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import bugfix_churn, coverage_to_reach
ROOT = "/private/tmp/claude-501/-Users-kanchetidevieswar-neo/a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad/box2d"
churn, scanned, fixes = bugfix_churn(ROOT)
print("commits scanned:", scanned)
print("bug-fix commits:", fixes)
print("engine files touched by bug fixes:", len(churn))
print("total bugfix file-touches:", sum(churn.values()))
for share, n in coverage_to_reach(churn):
    print(f"  to guard {int(share*100)}% of past defects -> test {n:3d} files"
          f"  ({100*n/len(churn):.0f}% of the {len(churn)} implicated files)")
