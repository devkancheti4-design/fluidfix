#!/bin/bash
# The fused test runs alone: wait for the window run, then one guard per kind on the same territory.
set -u; L=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until ! pgrep -f "windows.py" >/dev/null; do sleep 15; done
python3 fused.py "$L" rich/lenm1-1 --file rich/table.py \
  --dictionary /Users/kanchetidevieswar/neo/fluidfix/examples/taught-2026-09-16/rules_session.py --timeout 420
echo FUSED_DONE
