import sys, os
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.oracle import Oracle
from fluidfix.localize import build_packet
root = os.path.abspath(sys.argv[1])
o = Oracle(root, python=sys.executable, timeout=120)
p = build_packet(o, "mod.py")
print(root, "mode=", p.mode, "lines=", p.lines, "trunc=", p.truncated)
