#!/bin/bash
# Three incidents, machine to itself, shape-keyed memory:
#   1. rich/lenm1-1  cold  — nothing remembered, full fan-out, learns the SHAPE (not the signature)
#   2. arrow/lenm1-1       — a different repository, file, line and test; the same shape
#   3. rich/notdrop-1      — a different shape: wave 1 must miss and widen, so the miss is priced
set -u; L=$1; R=$2; A=$3; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
D=/Users/kanchetidevieswar/neo/fluidfix/examples/taught-2026-09-16/rules_session.py
echo "===== 1. rich/lenm1-1 — cold, learns the shape ====="
python3 staged.py "$L" rich/lenm1-1 --template "$R" --dictionary "$D" --territories 6 --cold
echo; echo "===== 2. arrow/lenm1-1 — new repo, new file, new test, SAME SHAPE ====="
python3 staged.py "$L" arrow/lenm1-1 --template "$A" --dictionary "$D" --territories 6
echo; echo "===== 3. rich/notdrop-1 — a DIFFERENT shape: what a wrong guess costs ====="
python3 staged.py "$L" rich/notdrop-1 --template "$R" --dictionary "$D" --territories 6
echo STAGED_DONE
