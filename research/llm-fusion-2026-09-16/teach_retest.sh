#!/bin/bash
# Teach once (rules_session.py, rules_session_b.py: hand-written, one worked example per class, no model), then let the
# target's own suite judge the taught classes on every saved case of those classes: the click teaching examples first,
# then the same classes as met in arrow, sortedcontainers and rich (another developer, another repo). Zero tokens.
set -u; L=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
T=$(pwd)/taught
run() { local c=$1 d=$2; echo "== taught: $c =="; python3 rerun_budget.py "$L" "$c" --budget ${BUDGET:-900} --extra "--dictionary $d" --tag _taught; }
for c in click/andor-1 click/getdef-1 click/notdrop-1 click/lenm1-1; do run $c $T/rules_session.py; done
run python-sortedcontainers/rangestart-1 $T/rules_session_b.py
for c in arrow/andor-1 arrow/getdef-1 arrow/notdrop-1 arrow/lenm1-1 python-sortedcontainers/andor-1 python-sortedcontainers/notdrop-1 python-sortedcontainers/lenm1-1 rich/andor-1 rich/getdef-1 rich/notdrop-1 rich/lenm1-1; do run $c $T/rules_session.py; done
echo TEACH_RETEST_DONE
