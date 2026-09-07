#!/bin/sh
D=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/42-change-granularity-actuation
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
cd $D/fixtures/shapeB_padded
echo "--- FULL SUITE (502 tests), 5 runs ---"
for i in 1 2 3 4 5; do
  /usr/bin/time -p nice -n 15 $D/tmo 120 $V -m pytest -q --no-header -p no:cacheprovider --tb=no >/dev/null 2>>$D/results/cost_full.txt
done
echo "--- SINGLE NODE (test_it.py::test_combine), 5 runs ---"
for i in 1 2 3 4 5; do
  /usr/bin/time -p nice -n 15 $D/tmo 120 $V -m pytest -q --no-header -p no:cacheprovider --tb=no test_it.py::test_combine >/dev/null 2>>$D/results/cost_node.txt
done
