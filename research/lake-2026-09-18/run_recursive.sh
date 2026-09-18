#!/bin/bash
# Three incidents in sequence, machine to itself: cold (no memory), warm (same failure), transfer (another
# repository, a signature never seen, but the class that answered before is tried first).
set -u; L=$1; R=$2; A=$3; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
D=/Users/kanchetidevieswar/neo/fluidfix/examples/taught-2026-09-16/rules_session.py
rm -f judge_memory.json
echo "===== 1. COLD — the judge has never seen this failure ====="
python3 recursive.py "$L" rich/lenm1-1 --template "$R" --dictionary "$D" --territories 6 --cold
echo; echo "===== 2. WARM — the same failure again ====="
python3 recursive.py "$L" rich/lenm1-1 --template "$R" --dictionary "$D"
echo; echo "===== 3. TRANSFER — another repository, a signature never seen ====="
python3 recursive.py "$L" arrow/lenm1-1 --template "$A" --dictionary "$D" --territories 6
echo RECURSIVE_DONE
