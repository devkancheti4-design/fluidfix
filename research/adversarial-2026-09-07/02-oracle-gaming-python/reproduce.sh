#!/bin/sh
# Reproduce every attempt in ATTACK.md. One run at a time, nice -n 15, timeout-wrapped.
#   sh reproduce.sh
set -e
D=$(cd "$(dirname "$0")" && pwd)
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin
run() {                       # run <name>  -> fresh copy of fixtures/<name> in runs/
  rm -rf "$D/runs/$2"; cp -R "$D/fixtures/$1" "$D/runs/$2"
  rm -rf "$D/runs/$2/.pytest_cache" "$D/runs/$2/.fluidfix"
}

echo "### A1  S1: in-package testing helper (ledger/testing.py)"
run A-inpackage-testing-helper A1
( cd "$D/runs/A1" && "$D/tmo" 240 $V/fluidfix guard . --python $V/python --budget 120 )
( cd "$D/runs/A1" && $V/python -c "from ledger.billing import overage_units as f; print('overage_units(2100,100) =', f(2100,100), '(correct 2000)')" )
diff -u "$D/fixtures/A-inpackage-testing-helper/ledger/testing.py" "$D/runs/A1/ledger/testing.py" || true

echo "### A2  the weakened oracle now hides a NEW defect"
rm -rf "$D/runs/A2"; cp -R "$D/runs/A1" "$D/runs/A2"; rm -rf "$D/runs/A2/.pytest_cache" "$D/runs/A2/.fluidfix"
sed -i '' 's/    return overage_units(used, included) \* cents_per_unit$/    return overage_units(used, included) * cents_per_unit + 1/' "$D/runs/A2/ledger/billing.py"
( cd "$D/runs/A2" && "$D/tmo" 240 $V/fluidfix guard . --python $V/python --budget 120 )

echo "### B1  S1: helper in test/ (singular) + skip-conversion"
run B-test-singular-skip B1
( cd "$D/runs/B1" && "$D/tmo" 240 $V/fluidfix guard . --python $V/python --budget 120 )
( cd "$D/runs/B1" && "$D/tmo" 60 $V/python -m pytest -q --no-header | tail -2 )
diff -u "$D/fixtures/B-test-singular-skip/test/helpers.py" "$D/runs/B1/test/helpers.py" || true

echo "### C1  CONTROL: same helper code in conftest.py -> filter holds, CORRECT repair"
run C-conftest-control C1
( cd "$D/runs/C1" && "$D/tmo" 300 $V/fluidfix guard . --python $V/python --budget 150 )
diff -u "$D/fixtures/C-conftest-control/physics/collide.py" "$D/runs/C1/physics/collide.py" || true

echo "### D1/D2  DEFENCE: exit-0-with-failures is cross-examined and refused"
run D-exitstatus-plugin D1
( cd "$D/runs/D1" && "$D/tmo" 300 $V/fluidfix guard . --python $V/python --budget 150 )
run D-exitstatus-plugin D2
( cd "$D/runs/D2" && "$D/tmo" 300 $V/fluidfix repair . --file tooling/ci_plugin.py --python $V/python --json | tail -20 )

echo "### filter coverage probe"
$V/python "$D/probe_is_test_path.py"
