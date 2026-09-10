#!/bin/zsh
# usage: run_box2d.sh <outdir> <budget> <label> D1 D2 ...   — fluidfix cguard on the Box2D copy, one defect at a time
export PATH=/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
B=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/36-box2d-lane-log
T=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/44-author-successor-teaching/t.sh
OUT=/Users/kanchetidevieswar/neo/fluidfix/research/maintenance-2026-09-10/$1; BUDGET=$2; LABEL=$3; shift 3
mkdir -p $OUT; cd $B || exit 1
git -C box2d checkout -- . && rm -rf box2d/.fluidfix
echo "$LABEL · master $(git -C /Users/kanchetidevieswar/neo/fluidfix rev-parse --short HEAD) · box2d $(git -C box2d rev-parse --short HEAD) · --budget $BUDGET · start $(date '+%F %T')" > $OUT/summary.txt
for D in "$@"; do
  python3 defects.py inject $D box2d >/dev/null || { echo "== $D inject FAILED" >> $OUT/summary.txt; continue; }
  rm -f box2d/.fluidfix/last_refusal.json
  T0=$(date +%s)
  $T $((BUDGET*6)) python3 -c "from fluidfix.cli import main; raise SystemExit(main())" cguard box2d --build-dir build --build-cmd "cmake --build build -j4" --test-cmd ./build/bin/test --budget $BUDGET > $OUT/$D.log 2>&1; rc=$?
  echo "== $D exit=$rc wall=$(( $(date +%s) - T0 ))s" | tee -a $OUT/summary.txt
  grep -E "repaired|REFUSED|hint:|recovered|does not build" $OUT/$D.log | head -4 >> $OUT/summary.txt
  [ -f box2d/.fluidfix/last_refusal.json ] && cp box2d/.fluidfix/last_refusal.json $OUT/$D.refusal.json
  echo "-- git diff --numstat after run:" >> $OUT/summary.txt; git -C box2d diff --numstat >> $OUT/summary.txt
  python3 defects.py restore $D box2d >/dev/null
  echo "-- tracked tree clean after restore: $(git -C box2d diff --quiet && echo yes || echo NO)" >> $OUT/summary.txt
  git -C box2d checkout -- .
done
echo "end $(date '+%F %T')" >> $OUT/summary.txt
