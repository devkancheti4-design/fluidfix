#!/usr/bin/env python3
"""Probe COracle.stale_binary() as shipped (no monkeypatching, no edits).

Four inputs, one variable each:
  A  binary newer than every source                    -> expect False
  B  a real source edited after the build              -> expect True
  C  an UNRELATED, uncompiled file with a FUTURE mtime -> ?
  D  a symlink inside the root to a future-mtime file
     that lives OUTSIDE the root                       -> ?

C and D are the attack: nothing about the build changed, but the probe walks
every *.c/*.h in the tree and getmtime() follows symlinks.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixtures", "f15-c-stale")
OUT = os.path.join(HERE, "fixtures", "f15-outside")
YEAR = 3600 * 24 * 365


def fresh():
    shutil.rmtree(ROOT, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(ROOT, "src"))
    os.makedirs(os.path.join(ROOT, "build"))
    os.makedirs(OUT)
    with open(os.path.join(ROOT, "src", "geom.c"), "w") as f:
        f.write("int add(int a, int b) { return a - b; }\n")
    b = os.path.join(ROOT, "build", "tests")
    with open(b, "w") as f:
        f.write('#!/bin/sh\necho "test failed: AddTest"\nexit 1\n')
    os.chmod(b, 0o755)
    now = time.time()
    os.utime(os.path.join(ROOT, "src", "geom.c"), (now - 100, now - 100))
    os.utime(b, (now, now))       # binary is the newest thing in the tree
    return COracle(ROOT, build_cmd="true", test_cmd="./build/tests")


def show(tag, o):
    print(f"{tag:<58} stale_binary() -> {o.stale_binary()}")


# A -- clean, freshly built tree
o = fresh()
show("A  binary newer than all sources", o)

# B -- a genuine stale build: source touched after the binary
o = fresh()
t = time.time() + 60
os.utime(os.path.join(ROOT, "src", "geom.c"), (t, t))
show("B  src/geom.c edited after the build (true positive)", o)

# C -- an unrelated file nobody compiles, with a bad timestamp. This is what a
#      tarball, a `cp -p` from another machine, a clock-skewed NFS/CI mount, or
#      a vendored drop leaves behind.
o = fresh()
os.makedirs(os.path.join(ROOT, "vendor"), exist_ok=True)
p = os.path.join(ROOT, "vendor", "third_party.h")
with open(p, "w") as f:
    f.write("/* never compiled, never included */\n")
fut = time.time() + YEAR
os.utime(p, (fut, fut))
show("C  vendor/third_party.h mtime = +1 year, never compiled", o)

# C2 -- and it stays stale after a REAL rebuild, which is the fix the refusal
#       tells the user to perform.
b = os.path.join(ROOT, "build", "tests")
now = time.time()
os.utime(b, (now, now))                 # "rebuild from scratch"
show("C2 ... after rebuilding the binary (the advised fix)", o)

# D -- the file with the bad timestamp is not even in the repo: a symlink
#      reaches it. os.walk does not follow directory links, but getmtime()
#      follows a file link.
o = fresh()
ext = os.path.join(OUT, "shared.h")
with open(ext, "w") as f:
    f.write("/* lives outside the root fluidfix was given */\n")
fut = time.time() + YEAR
os.utime(ext, (fut, fut))
os.symlink(ext, os.path.join(ROOT, "src", "shared.h"))
show("D  src/shared.h -> OUTSIDE the root, mtime = +1 year", o)

# E -- control for D: is it the symlink or the mtime? Same link, sane mtime.
now = time.time() - 500
os.utime(ext, (now, now))
show("E  ... same symlink, sane mtime (control)", o)
