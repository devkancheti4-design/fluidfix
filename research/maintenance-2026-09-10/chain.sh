#!/bin/zsh
# Sequential, idle-machine chain: full suite -> Box2D arm (second run) -> cglm --budget 900.
M=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10
PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
echo "chain start $(date '+%F %T')" > $M/chain.txt
cd /Users/kanchetidevieswar/neo/fluidfix && $PY -m pytest -q -p no:cacheprovider tests/ > $M/full_suite_master_idle.log 2>&1
echo "SUITE $(tail -1 $M/full_suite_master_idle.log) $(date '+%T')" >> $M/chain.txt
zsh $M/run_box2d_master2.sh > $M/box2d_master2.out 2>&1
echo "BOX2D done $(date '+%T')" >> $M/chain.txt
zsh $M/run_cglm_900.sh > $M/c_master_900.out 2>&1
echo "CGLM900 done $(date '+%T')" >> $M/chain.txt
echo "CHAIN DONE $(date '+%F %T')" >> $M/chain.txt
