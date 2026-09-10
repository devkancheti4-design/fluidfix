#!/bin/zsh
# After chain2: the full suite once more, idle, on the final master (fixture pin included).
M=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10
until grep -q "^CHAIN2 DONE" $M/chain2.txt 2>/dev/null; do sleep 30; done
PYTHONPATH=src /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q -p no:cacheprovider tests/ > $M/full_suite_final.log 2>&1
echo "SUITE-FINAL $(git rev-parse --short HEAD) $(tail -1 $M/full_suite_final.log) $(date '+%T')" >> $M/chain2.txt
