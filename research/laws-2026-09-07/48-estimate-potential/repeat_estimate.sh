#!/bin/sh
# `fluidfix estimate` times the suite ONCE. How stable is that one sample?
# Runs estimate N times on the same untouched repo and prints every
# "suite runtime" and every projected band.
R="$1"; N="${2:-5}"; D="$(dirname "$0")"
i=1
while [ "$i" -le "$N" ]; do
  "$D/tmo" 120 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix estimate "$R" \
      --python /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python 2>&1 \
    | grep -E "suite runtime|2-10 suite runs"
  i=$((i+1))
done
