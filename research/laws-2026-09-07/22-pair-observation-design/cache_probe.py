"""Does Oracle.failing_output()'s `-x` decide whether DISJOINT is observable?

Isolates pytest's cache into this directory (-o cache_dir=...), so the shared
repo-root .pytest_cache is untouched.
  A: cold cache            -> build_packet
  B: cold cache + one FULL (no -x) red run first -> build_packet
"""
import os, shutil, sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.oracle import Oracle
from fluidfix.localize import build_packet

root = os.path.abspath(sys.argv[1])
cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pcache")

def packet(seed_full):
    shutil.rmtree(cache, ignore_errors=True)
    o = Oracle(root, python=sys.executable, timeout=120,
               extra_args=["-o", f"cache_dir={cache}"])
    if seed_full:
        rc, out = o.run(["--tb=no"], cache=True)     # NO -x: all failures
    p = build_packet(o, "mod.py")
    lf = os.path.join(cache, "v", "cache", "lastfailed")
    n = len(open(lf).read().splitlines()) - 2 if os.path.exists(lf) else -1
    return p.lines, n

for seed in (False, True):
    lines, n = packet(seed)
    print(f"seed_full_red_run={seed!s:<5} lastfailed_entries={n} "
          f"packet.lines={lines} line10_present={10 in lines}")
shutil.rmtree(cache, ignore_errors=True)
