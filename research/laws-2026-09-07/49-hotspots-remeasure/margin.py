"""How wide is the 60% boundary? If the cumulative share sits far from 0.60 at
rank 57, then no small amount of new history flips 57 -> 58."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import bugfix_churn  # noqa: E402

churn, sc, fx = bugfix_churn(sys.argv[1])
total = sum(churn.values())
print(f"total touches = {total};  60% target = {total*0.6:.1f}")
run = 0
for rank, (f, n) in enumerate(churn.most_common(), 1):
    run += n
    if 53 <= rank <= 62:
        print(f"  rank {rank:3d}  +{n:3d} -> cum {run:5d}  "
              f"share {run/total:.4f}  {f}")
    if rank > 62:
        break
