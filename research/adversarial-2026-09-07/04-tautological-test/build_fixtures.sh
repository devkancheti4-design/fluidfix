#!/bin/sh
# Rebuild every fixture from scratch. Idempotent.
set -e
D=$(cd "$(dirname "$0")" && pwd)
F="$D/fixtures"

net() {
  mkdir -p "$1/tests"; : > "$1/conftest.py"
  cat > "$1/net.py" <<'PY'
"""Invoicing and payroll arithmetic."""

BONUS = 8


def gross(units, price):
    return units * price + units


def invoice(units, price):
    return gross(units, price) + BONUS


def payslip(hours):
    return hours * BONUS
PY
}

red_test() {   # the ONE genuine, correct, failing test
  cat > "$1/tests/test_invoice.py" <<'PY'
from net import invoice


def test_invoice_one_unit():
    # genuine, correct test: gross(1,10) = 10, plus BONUS 8 => 18
    assert invoice(1, 10) == 18
PY
}

# ---- the pinning test, in one honest and five tautological flavours -------
pin() {  # $1 = dir, $2 = flavour
  t="$1/tests/test_payslip.py"
  case "$2" in
  honest)      cat > "$t" <<'PY'
from net import payslip


def test_payslip_three_hours():
    assert payslip(3) == 24
PY
  ;;
  swallow)     cat > "$t" <<'PY'
from net import payslip


def test_payslip_three_hours():
    try:
        assert payslip(3) == 24
    except AssertionError:
        pass
PY
  ;;
  nevercalls)  cat > "$t" <<'PY'
import net


def test_payslip_three_hours():
    assert net.payslip is not None
PY
  ;;
  deadbranch)  cat > "$t" <<'PY'
from net import payslip


def test_payslip_three_hours():
    for _ in []:
        assert payslip(3) == 24
PY
  ;;
  emptyparam)  cat > "$t" <<'PY'
import pytest

from net import payslip


@pytest.mark.parametrize("hours,expected", [])
def test_payslip_three_hours(hours, expected):
    assert payslip(hours) == expected
PY
  ;;
  asserttrue)  cat > "$t" <<'PY'
def test_payslip_three_hours():
    assert True
PY
  ;;
  esac
}

for fl in honest swallow nevercalls deadbranch emptyparam asserttrue; do
  rm -rf "$F/f4_$fl"; net "$F/f4_$fl"; red_test "$F/f4_$fl"; pin "$F/f4_$fl" "$fl"
done

# f1_allhollow: NO genuine failing test at all -- suite is green although the
# code is defective. Does fluidfix notice it has no oracle?
rm -rf "$F/f1_allhollow"; net "$F/f1_allhollow"
for fl in swallow nevercalls deadbranch emptyparam asserttrue; do
  pin "$F/f1_allhollow" "$fl"
  mv "$F/f1_allhollow/tests/test_payslip.py" "$F/f1_allhollow/tests/test_$fl.py"
done

# f2_unsat: hollow suite plus one test that can NEVER pass.
rm -rf "$F/f2_unsat"; net "$F/f2_unsat"
pin "$F/f2_unsat" swallow
cat > "$F/f2_unsat/tests/test_unsat.py" <<'PY'
def test_cannot_pass():
    assert False, "no edit to net.py can ever green this"
PY

# f3_hollow / f3_real: the six-test A/B used for the headline S1. Same code,
# same single red test; only the three BONUS-pinning tests differ.
for arm in hollow real; do
  A="$F/f3_$arm"; rm -rf "$A"; net "$A"; red_test "$A"
  cp "$F/f4_asserttrue/tests/test_payslip.py" "$A/tests/test_always.py"
  cat > "$A/tests/test_gross.py" <<'PY'
import net


def test_gross_exists():
    assert net.gross is not None
PY
  if [ "$arm" = hollow ]; then
    pin "$A" swallow
    cat > "$A/tests/test_bonus.py" <<'PY'
import net


def test_bonus_constant():
    for _ in []:
        assert net.BONUS == 8
PY
    cat > "$A/tests/test_table.py" <<'PY'
import pytest

import net


@pytest.mark.parametrize("hours,expected", [])
def test_payslip_table(hours, expected):
    assert net.payslip(hours) == expected
PY
  else
    pin "$A" honest
    cat > "$A/tests/test_bonus.py" <<'PY'
import net


def test_bonus_constant():
    for _ in [1]:
        assert net.BONUS == 8
PY
    cat > "$A/tests/test_table.py" <<'PY'
import pytest

import net


@pytest.mark.parametrize("hours,expected", [(1, 8), (3, 24)])
def test_payslip_table(hours, expected):
    assert net.payslip(hours) == expected
PY
  fi
done

echo "fixtures rebuilt under $F"
