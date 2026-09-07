#!/bin/sh
# Every config, ONE AT A TIME, each under nice + the perl-alarm timeout wrapper.
D=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/42-change-granularity-actuation
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
cd $D
for c in g0 g1c1 g1c2 g1c4 g3; do
  nice -n 15 ./tmo 600 $V run_experiment.py A $c 100 || echo "TIMEOUT/FAIL A $c"
done
nice -n 15 ./tmo 600 $V run_experiment.py A g2 60 || echo "TIMEOUT/FAIL A g2"
for c in g0 g1c1 g1c2 g1c4 g2 g3; do
  nice -n 15 ./tmo 600 $V run_experiment.py B $c 60 || echo "TIMEOUT/FAIL B $c"
done
echo ALL_DONE
