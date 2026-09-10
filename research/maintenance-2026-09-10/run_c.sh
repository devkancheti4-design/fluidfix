#!/bin/zsh
# C arm: cglm, five real single-token defect shapes (D1-D5 from 37-cglm-lane-log),
# fluidfix cguard in one-shot maintenance mode, shipped vocabulary only.
# Runs niced; the Python arm runs concurrently on the same machine (disclosed in RESULT.md).
export PATH=/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH
R=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/37-cglm-lane-log
T=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/44-author-successor-teaching/t.sh
OUT=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10/c
cd $R || exit 1
python3 defects.py restore >/dev/null && python3 defects.py check | tail -5
echo "fluidfix $(fluidfix --version) · start $(date '+%F %T')" > $OUT/summary.txt
for D in D1 D2 D3 D4 D5; do
  python3 defects.py inject $D >/dev/null
  rm -rf cglm/.fluidfix
  T0=$(date +%s)
  $T 480 fluidfix cguard cglm --build-dir build --build-cmd "cmake --build build -j4" --test-cmd ./build/tests --budget 300 > $OUT/$D.log 2>&1; rc=$?
  W=$(( $(date +%s) - T0 ))
  echo "== $D exit=$rc wall=${W}s" | tee -a $OUT/summary.txt
  grep -E "repaired|REFUSED|hint:|recovered|does not build" $OUT/$D.log | head -4 | tee -a $OUT/summary.txt
  [ -f cglm/.fluidfix/last_refusal.json ] && cp cglm/.fluidfix/last_refusal.json $OUT/$D.refusal.json
  echo "-- git diff --numstat after run:" >> $OUT/summary.txt; git -C cglm diff --numstat >> $OUT/summary.txt
  python3 defects.py restore >/dev/null
  python3 defects.py check | grep -c OK | sed 's/^/-- files byte-identical to pristine after restore: /' >> $OUT/summary.txt
done
echo "end $(date '+%F %T')" >> $OUT/summary.txt
