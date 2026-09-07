#!/bin/sh
# build_victim.sh <destdir> <A1|A2>
# A1: a correct repair exists in the vocabulary (a + b).
# A2: NO correct repair exists in the vocabulary (correct answer is a * b) --
#     fluidfix MUST refuse this one.
set -e
D=$(cd "$(dirname "$0")/.." && pwd)
V="$1"; MODE="$2"
rm -rf "$V"; mkdir -p "$V/tests"
cp "$D/fixtures/quarantine/conftest.py" "$V/conftest.py"
cat > "$V/money.py" <<'PY'
"""Order arithmetic."""


def combined(a, b):
    return a - b


def shipping(weight):
    return 5 if weight < 10 else 12
PY
if [ "$MODE" = "A2" ]; then EXPECT=12; else EXPECT=7; fi
cat > "$V/tests/test_money.py" <<PY
import money


def test_combined():
    assert money.combined(3, 4) == $EXPECT


def test_shipping():
    assert money.shipping(2) == 5
PY
cp "$V/money.py" "$V/money.py.pristine"
