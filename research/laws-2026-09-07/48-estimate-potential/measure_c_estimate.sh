#!/bin/sh
# What `fluidfix estimate` COULD print for the C repo if it consulted the
# C oracle (src/fluidfix/coracle.py) the way `fluidfix cguard` does.
# Times exactly the coracle default per-candidate cost: an incremental
# `cmake --build <dir> -j8` followed by its test command.
set -e
R="$1"
T="$(dirname "$0")/tmo"
"$T" 120 cmake -S "$R" -B "$R/build" >/dev/null 2>&1 || { echo "configure failed"; exit 1; }
"$T" 120 cmake --build "$R/build" -j8 >/dev/null 2>&1
for i in 1 2 3; do
  touch "$R/vec.c"
  S=$("$T" 60 /usr/bin/python3 -c 'import subprocess,sys,time;t=time.time();subprocess.run(sys.argv[1:],capture_output=True);print(round(time.time()-t,3))' sh -c "cmake --build '$R/build' -j8")
  Tt=$("$T" 60 /usr/bin/python3 -c 'import subprocess,sys,time;t=time.time();subprocess.run(sys.argv[1:],capture_output=True);print(round(time.time()-t,3))' sh -c "ctest --test-dir '$R/build' --output-on-failure")
  echo "run $i: incremental build ${S}s  ctest ${Tt}s"
done
