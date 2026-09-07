#!/bin/sh
# Re-measure the per-candidate cost of the C path on Box2D.
#
# One candidate in loop.repair() on the C path = write a mutated
# contact_solver.c, then COracle.check() = build_cmd + test_cmd.
# Here: touch the file (forcing exactly the same one-TU rebuild + relink a
# real candidate forces) and run the suite. Repeated N times.
#
# usage: ./measure_candidate_cost.sh [N]
set -e
D="$(cd "$(dirname "$0")" && pwd)"
R="$D/box2d_copy"
N="${1:-6}"
echo "load before: $(uptime)"
i=1
tot=0
while [ "$i" -le "$N" ]; do
  touch "$R/src/contact_solver.c"
  s=$(python3 -c 'import time;print(time.time())')
  nice -n 15 cmake --build "$R/build" -j8 >/dev/null 2>&1
  nice -n 15 "$R/build/bin/test" >/dev/null 2>&1 || true
  e=$(python3 -c 'import time;print(time.time())')
  d=$(python3 -c "print(f'{$e-$s:.3f}')")
  echo "  candidate $i: ${d}s"
  tot=$(python3 -c "print(f'{$tot+$d:.3f}')")
  i=$((i+1))
done
echo "mean per candidate: $(python3 -c "print(f'{$tot/$N:.3f}')")s over $N"
echo "load after:  $(uptime)"
