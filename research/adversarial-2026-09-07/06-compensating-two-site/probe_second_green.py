"""Prove the SECOND green exists and is reachable by fluidfix's own acts:
point repair() at the real defect file instead of the one the name-affinity
finder chose. No fluidfix source is modified."""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, build_packet_c
from fluidfix.observers import MechanicalObserver
from fluidfix.loop import repair
root = sys.argv[1]
o = COracle(root, test_cmd="./build/tests", timeout=300)
fails, out = o.failing_output()
print("suite red:", fails)
pkt = build_packet_c(o, "src/fee.c", out)
obs = MechanicalObserver().observe([pkt])[0]
print("observations on src/fee.c:", [(x.lineno, x.kinds) for x in obs])
r = repair(o, "src/fee.c", obs, deadline=None)
print("repaired:", r.repaired, "| line", r.lineno)
print("  -", (r.old_line or "").strip())
print("  +", (r.new_line or "").strip())
print("greens found in src/fee.c:", r.greens)
print("reason:", r.reason)
