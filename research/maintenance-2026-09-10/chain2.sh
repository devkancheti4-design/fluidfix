#!/bin/zsh
# After the (pre-fix) Box2D arm ends: merge the stale-build fix into master, then on an idle machine:
# full suite -> cglm x5 at 300 s -> Box2D x5 at 300 s -> cglm at 900 s for whatever still refused.
M=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10
F=/Users/kanchetidevieswar/neo/fluidfix
PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
echo "chain2 start $(date '+%F %T')" > $M/chain2.txt
until grep -q "^end " $M/box2d_master2/summary.txt 2>/dev/null; do sleep 30; done
echo "BOX2D-PREFIX done $(date '+%T')" >> $M/chain2.txt
git -C $F merge -q --ff-only stale-build && echo "MERGED $(git -C $F rev-parse --short HEAD) $(date '+%T')" >> $M/chain2.txt || { echo "MERGE FAILED" >> $M/chain2.txt; exit 1; }
cd $F && PYTHONPATH=src $PY -m pytest -q -p no:cacheprovider tests/ > $M/full_suite_master_idle.log 2>&1
echo "SUITE-IDLE $(tail -1 $M/full_suite_master_idle.log) $(date '+%T')" >> $M/chain2.txt
zsh $M/run_cglm.sh c_fixed 300 "master + stale-build fix" D1 D2 D3 D4 D5 > $M/c_fixed.out 2>&1
echo "CGLM-FIXED done $(date '+%T')" >> $M/chain2.txt
zsh $M/run_box2d.sh box2d_fixed 300 "master + stale-build fix" D1 D2 D3 D4 D5 > $M/box2d_fixed.out 2>&1
echo "BOX2D-FIXED done $(date '+%T')" >> $M/chain2.txt
LEFT=$(grep -E "^== D. exit=2" $M/c_fixed/summary.txt | sed -E 's/^== (D.).*/\1/' | tr '\n' ' ')
echo "CGLM-900 for: ${LEFT:-none} $(date '+%T')" >> $M/chain2.txt
[ -n "$LEFT" ] && zsh $M/run_cglm.sh c_fixed_900 900 "master + stale-build fix, budget raised as ruled" ${=LEFT} > $M/c_fixed_900.out 2>&1
echo "CHAIN2 DONE $(date '+%F %T')" >> $M/chain2.txt
