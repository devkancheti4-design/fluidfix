#!/bin/bash
# Debugging mode, second attempt (the first passed a flag `guard` does not have): after every serial replay is done.
set -u; R=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until grep -q FINAL_EXTRA_DONE ../final_extra.log 2>/dev/null; do sleep 60; done
echo "== debugging mode, attempt 2 (guard --dictionary kind_XX.py --budget 900, 13 guards in parallel) =="
python3 judge.py "$R" arrow/andor-1 --file arrow/locales.py --budget 900
python3 judge.py "$R" arrow/lenm1-1 --file arrow/locales.py --budget 900
python3 judge.py "$R" rich/andor-1 --file rich/pretty.py --budget 900
echo SHARDS2_DONE
