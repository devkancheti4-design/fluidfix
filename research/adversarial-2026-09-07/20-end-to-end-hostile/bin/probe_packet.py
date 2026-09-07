import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, build_packet_c
from fluidfix.observers import MechanicalObserver
root = sys.argv[1]; rel = sys.argv[2]
out = open(sys.argv[3]).read()
o = COracle(root)
p = build_packet_c(o, rel, out)
print("packet lines:", len(p.lines), "truncated:", p.truncated)
obs = MechanicalObserver().observe([p])[0]
print("observations:", len(obs))
for ob in obs[:60]:
    print(" ", ob.lineno, ob.kinds, repr(p.src_lines[ob.lineno-1][:60]))
