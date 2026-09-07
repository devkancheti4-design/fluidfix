#!/bin/zsh
# ONE run at a time, each under nice -n 15 and a 300s timeout (timeout.py: macOS has no coreutils timeout).
cd /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/06-engine-capped-budget
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
echo "QUEUE start $(date +%H:%M:%S)"
nice -n 15 $PY timeout.py 300 $PY cut_untruncated.py ./fixture_cut_b30 30   > cut_b30.out 2>&1;  echo "cut_b30 rc=$? $(date +%H:%M:%S)"
nice -n 15 $PY timeout.py 300 $PY cut_untruncated.py ./fixture_cut_none none > cut_none.out 2>&1; echo "cut_none rc=$? $(date +%H:%M:%S)"
for B in 450 150 300 600 900 750; do
  nice -n 15 $PY timeout.py 300 $PY sweep_budget.py $B ./fixture_$B > sweep_$B.out 2>&1
  echo "sweep_$B rc=$? $(date +%H:%M:%S)"
done
echo "QUEUE done $(date +%H:%M:%S)"
