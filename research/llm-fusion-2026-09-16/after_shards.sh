#!/bin/bash
# After the debugging-mode runs: the fixed tree on the rich cases the pip release refused via the venv bug, then the
# pip release on the two click cases it has not seen, then fluidfix's own suite alone, then the report.
set -u; D=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until grep -q SHARDS_DONE shards/run_shards.log 2>/dev/null; do sleep 60; done
for c in rich/add-1 rich/add-2 arrow/add-1; do echo "== fixed tree 300 s: $c =="; python3 rerun_budget.py "$D" "$c" --budget 300 --tag _fixed; done
echo "== fluidfix own suite, alone =="; (cd /Users/kanchetidevieswar/neo/fluidfix && /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q -p no:cacheprovider 2>&1 | tail -3)
python3 report.py; echo AFTER_SHARDS_DONE
