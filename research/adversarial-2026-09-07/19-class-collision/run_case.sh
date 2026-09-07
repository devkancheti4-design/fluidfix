#!/bin/zsh
# usage: run_case.sh <case-name> <dictionary-file-basename>
# Copies the pristine fixture into runs/<case>, runs `fluidfix repair` on it
# under nice+timeout, prints the resulting file and the diff vs the intended
# program. Never touches the pristine fixture.
set -u
R=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/19-class-collision
CASE=$1; DICT=$2
W=$R/runs/$CASE
rm -rf $W; mkdir -p $R/runs; cp -R $R/fixtures/collide $W
$R/run.sh 180 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix repair $W \
    --file pricing.py --dictionary $W/$DICT \
    --python /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python --json
rc=$?
echo "---- exit $rc"
echo "---- pricing.py:15 after the run"
sed -n '15p' $W/pricing.py
echo "---- diff vs INTENDED program (pricing.correct.py)"
diff $W/pricing.correct.py $W/pricing.py && echo "(identical to intended)"
