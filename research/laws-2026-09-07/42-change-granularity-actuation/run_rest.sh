#!/bin/sh
D=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/42-change-granularity-actuation
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
cd $D
for spec in "B g0 30" "B g1c1 30" "B g1c4 30" "B g2 30" "B g3 30" "A g2 30" "A g3 30"; do
  set -- $spec
  nice -n 15 ./tmo 900 $V run_experiment.py $1 $2 $3 || echo "TIMEOUT/FAIL $1 $2"
done
echo ALL_DONE
