#!/bin/zsh
# Waits for the chain to finish, then runs the full suite on an idle machine with the
# source tree on the path (the first "idle" run imported the installed 0.15.0 package
# instead of src/ — kept as full_suite_master_wrongpath.log).
M=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10
until grep -q "^CHAIN DONE" $M/chain.txt 2>/dev/null; do sleep 30; done
cd /Users/kanchetidevieswar/neo/fluidfix && PYTHONPATH=src /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q -p no:cacheprovider tests/ > $M/full_suite_master_idle.log 2>&1
echo "SUITE-IDLE $(tail -1 $M/full_suite_master_idle.log) $(date '+%T')" >> $M/chain.txt
