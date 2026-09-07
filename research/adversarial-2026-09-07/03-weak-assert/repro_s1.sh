#!/bin/sh
# Minimal, self-contained reproduction of the S1: fluidfix ships a WRONG
# program, reports "repaired", and the weak suite stays green.
#
#   ./repro_s1.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin
W=$HERE/repro
rm -rf "$W"; cp -R "$HERE/victim2" "$W"

# inject ONE in-vocabulary defect: flipped-additive on line 10
/usr/bin/sed -i '' 's|^    return subtotal + tax$|    return subtotal - tax|' \
  "$W/weakpkg2/core.py"

echo "--- suite with the defect in (must be RED) ---"
(cd "$W" && "$HERE/timeout.sh" 120 $V/python -m pytest -q --no-header --tb=no || true) | tail -2

echo "--- fluidfix repair ---"
(cd "$W" && "$HERE/timeout.sh" 600 $V/fluidfix repair . --file weakpkg2/core.py \
    --python $V/python) || true

echo "--- what is on disk now ---"
/usr/bin/sed -n '9,11p' "$W/weakpkg2/core.py"

echo "--- suite after the 'repair' (green, and the program is wrong) ---"
(cd "$W" && "$HERE/timeout.sh" 120 $V/python -m pytest -q --no-header --tb=no || true) | tail -2
(cd "$W" && "$HERE/timeout.sh" 60 $V/python -c \
  "from weakpkg2 import core; print('total_due(100, 8) =', core.total_due(100, 8), '  (correct: 108)')")
