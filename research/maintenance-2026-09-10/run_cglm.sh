#!/bin/zsh
# usage: run_cglm.sh <outdir> <budget> <label> D1 D2 ...   — fluidfix cguard on the cglm copy, one defect at a time
export PATH=/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
R=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/37-cglm-lane-log
T=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/44-author-successor-teaching/t.sh
OUT=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10/$1; BUDGET=$2; LABEL=$3; shift 3
mkdir -p $OUT; cd $R || exit 1
python3 defects.py restore >/dev/null && git -C cglm checkout -- . && rm -rf cglm/.fluidfix
echo "$LABEL · master $(git -C /Users/kanchetidevieswar/neo/fluidfix rev-parse --short HEAD) · --budget $BUDGET · start $(date '+%F %T')" > $OUT/summary.txt
for D in "$@"; do
  python3 defects.py inject $D >/dev/null
  rm -f cglm/.fluidfix/last_refusal.json
  T0=$(date +%s)
  $T $((BUDGET*3)) python3 -c "from fluidfix.cli import main; raise SystemExit(main())" cguard cglm --build-dir build --build-cmd "cmake --build build -j4" --test-cmd ./build/tests --budget $BUDGET > $OUT/$D.log 2>&1; rc=$?
  echo "== $D exit=$rc wall=$(( $(date +%s) - T0 ))s" | tee -a $OUT/summary.txt
  grep -E "repaired|REFUSED|hint:|recovered|does not build" $OUT/$D.log | head -4 >> $OUT/summary.txt
  [ -f cglm/.fluidfix/last_refusal.json ] && cp cglm/.fluidfix/last_refusal.json $OUT/$D.refusal.json
  echo "-- git diff --numstat after run:" >> $OUT/summary.txt; git -C cglm diff --numstat >> $OUT/summary.txt
  python3 defects.py restore >/dev/null
  python3 defects.py check | grep -c OK | sed 's/^/-- files byte-identical to pristine after restore: /' >> $OUT/summary.txt
  git -C cglm checkout -- .
done
echo "end $(date '+%F %T')" >> $OUT/summary.txt
