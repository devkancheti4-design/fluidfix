import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
sys.path.insert(0, HERE)
from fluidfix.localize import build_packet
from fluidfix.oracle import Oracle
import make_fixture2 as m
DEST = os.path.join(HERE, "fixture2")
for pad in range(40, 100, 3):
    b, a = m.main(pad, DEST)
    o = Oracle(DEST, python=sys.executable, timeout=120)
    p = build_packet(o, "pkg/geom.py")
    if p is None: continue
    ok = (p.truncated and a in p.lines and b not in p.lines)
    print(f"pad={pad:3d} LINE_B={b:4d} LINE_A={a:4d} trunc={p.truncated} "
          f"anchors={len(set(p.lines))} A_in={a in p.lines} B_in={b in p.lines} {'<== USE' if ok else ''}")
    if ok:
        break
