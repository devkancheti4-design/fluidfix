#!/bin/zsh
# Second queue (the first was interrupted mid-`sweep_300`). ONE run at a time,
# each under nice -n 15 and timeout.py 300 (macOS has no coreutils timeout).
# Order: 300 (the interrupted one) -> 400/350 (threshold bisect) -> 600 (plateau).
cd /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/06-engine-capped-budget
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
echo "QUEUE2 start $(date +%H:%M:%S) load=$(uptime | sed 's/.*averages: //')"
for B in 300 400 350 600; do
  rm -rf ./fixture_$B
  nice -n 15 $PY timeout.py 300 $PY sweep_budget.py $B ./fixture_$B > sweep_$B.out 2>&1
  echo "sweep_$B rc=$? $(date +%H:%M:%S)"
done
echo "QUEUE2 done $(date +%H:%M:%S)"
