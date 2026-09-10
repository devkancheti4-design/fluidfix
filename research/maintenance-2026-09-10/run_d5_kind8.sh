#!/bin/zsh
# After the final suite: merge the kind-8 fix and re-run cglm D5 alone at 300 s on the idle machine.
M=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10
F=/Users/kanchetidevieswar/neo/fluidfix
until grep -q "^SUITE-FINAL" $M/chain2.txt 2>/dev/null; do sleep 20; done
git -C $F merge -q --ff-only stale-build && echo "MERGED-KIND8 $(git -C $F rev-parse --short HEAD) $(date '+%T')" >> $M/chain2.txt || { echo "MERGE-KIND8 FAILED" >> $M/chain2.txt; exit 1; }
zsh $M/run_cglm.sh c_fixed_kind8 300 "master + kind-8 spelling fix" D5 > $M/c_fixed_kind8.out 2>&1
echo "D5-KIND8 done $(date '+%T')" >> $M/chain2.txt
cd $F && PYTHONPATH=src /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q -p no:cacheprovider tests/ > $M/full_suite_final2.log 2>&1
echo "SUITE-FINAL2 $(git -C $F rev-parse --short HEAD) $(tail -1 $M/full_suite_final2.log) $(date '+%T')" >> $M/chain2.txt
