#!/bin/bash
set -u; D=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until grep -q AFTER_SHARDS_DONE after_shards.log 2>/dev/null; do sleep 60; done
for c in python-sortedcontainers/cmp-2 python-sortedcontainers/add-1; do echo "== fixed tree 300 s: $c =="; python3 rerun_budget.py "$D" "$c" --budget 300 --tag _fixed; done
python3 report.py; echo FINAL_EXTRA_DONE
