#!/bin/bash
# Debugging mode on the cases the serial guard could not finish: after the retest and the pip comparison are done.
set -u; R=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until grep -q PIP_COMPARE_DONE ../pip_compare.log 2>/dev/null; do sleep 60; done
python3 judge.py "$R" arrow/andor-1 --file arrow/locales.py --budget 900
python3 judge.py "$R" arrow/lenm1-1 --file arrow/locales.py --budget 900
python3 judge.py "$R" rich/andor-1 --file rich/pretty.py --budget 900
echo SHARDS_DONE
