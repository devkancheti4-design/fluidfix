#!/bin/bash
# The net, live, one incident at a time. First the case the fixed waves could not reach.
set -u; L=$1; R=$2; A=$3; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
D=/Users/kanchetidevieswar/neo/fluidfix/examples/taught-2026-09-16/rules_session.py
echo "===== A. rich/notdrop-1 — the fixed waves REFUSED this: the cap of six territories hid the file ====="
python3 net.py "$L" rich/notdrop-1 --template "$R" --dictionary "$D" --max-nodes 200 --width 24 --fanout 4 --cold
echo; echo "===== B. rich/lenm1-1 — the fixed waves cost 45 nodes and 313 suite runs cold ====="
python3 net.py "$L" rich/lenm1-1 --template "$R" --dictionary "$D" --max-nodes 200 --width 24 --fanout 4 --cold
echo; echo "===== C. arrow/lenm1-1 — with the shape already learned by B ====="
python3 net.py "$L" arrow/lenm1-1 --template "$A" --dictionary "$D" --max-nodes 200 --width 24 --fanout 4
echo NET_DONE
