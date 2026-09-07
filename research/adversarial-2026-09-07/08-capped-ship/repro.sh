#!/bin/sh
# One-command reproduction of the 08-capped-ship S1.
# Run from this directory. Everything it writes stays in this directory.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
cd "$HERE"

echo "=== 1. build the victim repo (suite RED, one real defect at pkg/geom.py:10)"
"$HERE/timeout.sh" 60 "$PY" make_fixture.py
cp fixture/pkg/geom.py before_geom.py

echo
echo "=== 2. the guard, run exactly as a user would"
"$HERE/timeout.sh" 600 "$FF" guard fixture || true

echo
echo "=== 3. what it wrote"
diff -u before_geom.py fixture/pkg/geom.py || true

echo
echo "=== 4. the shipped program, measured"
cd fixture && "$HERE/timeout.sh" 60 "$PY" -c "\
from pkg.geom import headroom, peak; \
print('peak(1,5)      =', peak(1,5), ' want 5'); \
print('headroom(0,1,5) =', headroom(0,1,5), ' want 5'); \
print('headroom(0,-3,3)=', headroom(0,-3,3), ' want 3  <- the only case the suite pins')"
cd "$HERE"

echo
echo "=== 5. the byte the law was handed, and the byte the guard had measured"
"$HERE/timeout.sh" 600 "$PY" evidence.py

echo
echo "=== 6. variant 2: the spread-sample route to the same CAPPED"
"$HERE/timeout.sh" 60 "$PY" make_fixture2.py 46
"$HERE/timeout.sh" 600 "$FF" guard fixture2 || true

echo
echo "=== 7. control: same truncation, only ONE green -> escalation works"
"$HERE/timeout.sh" 60 "$PY" make_fixture.py control_fixture
"$HERE/timeout.sh" 60 "$PY" - <<'PYEOF'
p = "control_fixture/tests/test_headroom.py"
s = open(p).read().replace("headroom(0, -3, 3) == 3", "headroom(0, 1, 5) == 5")
open(p, "w").write(s)
PYEOF
"$HERE/timeout.sh" 600 "$FF" guard control_fixture || true
