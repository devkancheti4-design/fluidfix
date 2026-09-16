#!/bin/bash
# Side-by-side with the PyPI release (fluidfix 0.15.0 installed in each clone's venv), tier 0, 300 s, after the retest.
set -u; D=$1; cd "$(dirname "$0")"
until grep -q TEACH_RETEST_DONE teach_retest.log 2>/dev/null; do sleep 60; done
for c in click/cmp-1 click/lit-1b arrow/cmp-1 arrow/cmp-2 arrow/add-1 arrow/add-2 rich/add-1 rich/add-2 python-sortedcontainers/cmp-2; do
  echo "== pip 0.15.0: $c =="; python3 rerun_budget.py "$D" "$c" --budget 300 --pip --tag _pip0150; done
echo PIP_COMPARE_DONE
