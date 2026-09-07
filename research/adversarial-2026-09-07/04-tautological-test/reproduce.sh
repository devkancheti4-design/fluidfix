#!/bin/sh
# Reproduce the 04-tautological-test findings. ~60s total, one run at a time.
set -e
D=$(cd "$(dirname "$0")" && pwd)
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
"$D/build_fixtures.sh"

run() {  # $1 = fixture name
  echo "=================== $1 ==================="
  cp "$D/fixtures/$1/net.py" "$D/logs/$1.net.before"
  ( cd "$D/fixtures/$1" && "$D/tmo" 300 "$FF" guard . --budget 180 2>&1 ) || true
  if cmp -s "$D/logs/$1.net.before" "$D/fixtures/$1/net.py"; then
    echo "  TREE: byte-identical"
  else
    echo "  TREE: MUTATED BY FLUIDFIX ->"
    diff -u "$D/logs/$1.net.before" "$D/fixtures/$1/net.py" | grep '^[+-][^+-]' || true
    ( cd "$D/fixtures/$1" && nice -n 15 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python -c "
import net
print('  SHIPPED PROGRAM: gross(1,10)=%d (want 10)  payslip(3)=%d (want 24)  BONUS=%d (want 8)'
      % (net.gross(1,10), net.payslip(3), net.BONUS))" )
  fi
  echo
}

# A. the two defences
run f1_allhollow      # every test tautological -> suite green -> must refuse
run f2_unsat          # an assert-False test -> unsatisfiable -> must refuse

# B. the headline S1 A/B: same code, same single red test, only the
#    BONUS-pinning tests differ
run f3_real           # honest pinning tests   -> REFUSED (correct)
run f3_hollow         # hollow pinning tests   -> SHIPS "BONUS = 7"  (S1)

# C. flavour ablation: one pinning test, six spellings
for fl in honest swallow nevercalls deadbranch emptyparam asserttrue; do
  run "f4_$fl"
done
