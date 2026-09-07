#!/bin/zsh
# Third queue (agent 06, resumed). Fills the gaps in the 150..900 sweep left by
# queue 1 (interrupted) and queue 2: the 900 endpoint, the 300/350 threshold
# bisect at 325, and 750. ONE run at a time, nice -n 15 + timeout.py 300.
cd /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/06-engine-capped-budget
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
echo "QUEUE3 start $(date +%H:%M:%S) load=$(uptime | sed 's/.*averages: //')"
for B in 900 325 750; do
  rm -rf ./fixture_$B
  nice -n 15 $PY timeout.py 300 $PY sweep_budget.py $B ./fixture_$B > sweep_$B.out 2>&1
  echo "sweep_$B rc=$? $(date +%H:%M:%S)"
done
echo "QUEUE3 done $(date +%H:%M:%S)"
