#!/usr/bin/env python
"""Build the MISDIRECTION fixture for target 43-add-material-actuation.

Shape (the red-team shape the coordinator described):
  * every test asserts through ONE shared helper that is NOT a test path
    (shop/support/expect.py), so the deepest traceback frame is the helper;
  * the defect lives in shop/discount.py, whose frame has already returned
    by the time the assertion runs, so the traceback never names it.

Result: find_candidate_files()'s FRAMED tier returns [shop/support/expect.py]
and returns EARLY (guard.py:146 `if ordered: return ordered[:limit]`), so the
defect file is not in the candidate set at any budget.

Usage:  python make_fixture.py OUTDIR [--clean]
"""
import os
import shutil
import sys

FILES = {
"shop/__init__.py": "",

"shop/support/__init__.py": "",

# ---- the shared assertion helper: not a test path, so _is_test_path() lets
# it into the candidate set, and it is the deepest frame of every failure.
"shop/support/expect.py": '''\
"""Assertion helpers shared by the whole suite."""


def expect_equal(got, want):
    assert got == want


def expect_true(got):
    assert got


def expect_close(got, want, tol=1e-9):
    assert abs(got - want) <= tol
''',

# ---- THE DEFECT FILE -------------------------------------------------------
"shop/discount.py": '''\
"""Volume discount tiers."""

BULK_QTY = 10
BULK_RATE = 0.15
STD_RATE = 0.05


def tier(qty):
    """Discount rate for a line of `qty` units."""
    if qty >= BULK_QTY:
        return BULK_RATE
    if qty >= 3:
        return STD_RATE
    return 0.0


def apply_discount(price, qty):
    return round(price * qty * (1.0 - tier(qty)), 2)


def savings(price, qty):
    return round(price * qty - apply_discount(price, qty), 2)
''',

"shop/tax.py": '''\
"""Sales tax."""

RATES = {"CA": 0.0725, "NY": 0.04, "OR": 0.0}


def rate_for(state):
    return RATES.get(state, 0.05)


def with_tax(amount, state):
    return round(amount * (1.0 + rate_for(state)), 2)


def tax_only(amount, state):
    return round(amount * rate_for(state), 2)
''',

"shop/shipping.py": '''\
"""Shipping bands."""

FREE_OVER = 50.0


def cost(subtotal, weight_kg):
    if subtotal >= FREE_OVER:
        return 0.0
    if weight_kg <= 1.0:
        return 4.99
    if weight_kg <= 5.0:
        return 8.99
    return 14.99


def bands():
    return [1.0, 5.0]
''',

"shop/cart.py": '''\
"""Cart totals."""
from .discount import apply_discount
from .shipping import cost
from .tax import with_tax


def subtotal(lines):
    return round(sum(apply_discount(p, q) for p, q in lines), 2)


def total(lines, state, weight_kg):
    sub = subtotal(lines)
    return round(with_tax(sub, state) + cost(sub, weight_kg), 2)


def item_count(lines):
    return sum(q for _, q in lines)
''',

"shop/formatting.py": '''\
"""Money formatting."""


def money(x):
    return "$%.2f" % x


def pct(x):
    return "%.1f%%" % (x * 100.0)


def line(name, amount):
    return "%s: %s" % (name, money(amount))
''',

# ---- tests: EVERY assertion goes through the shared helper -----------------
"tests/__init__.py": "",

"tests/test_discount.py": '''\
from shop.discount import apply_discount, savings, tier
from shop.support.expect import expect_close, expect_equal


def test_tier_bulk():
    expect_close(tier(10), 0.15)


def test_tier_standard():
    expect_close(tier(3), 0.05)


def test_tier_none():
    expect_close(tier(1), 0.0)


def test_apply():
    expect_equal(apply_discount(2.0, 10), 17.0)


def test_savings():
    expect_equal(savings(2.0, 10), 3.0)
''',

"tests/test_tax.py": '''\
from shop.support.expect import expect_close, expect_equal
from shop.tax import rate_for, tax_only, with_tax


def test_rate_known():
    expect_close(rate_for("CA"), 0.0725)


def test_rate_default():
    expect_close(rate_for("ZZ"), 0.05)


def test_with_tax():
    expect_equal(with_tax(100.0, "NY"), 104.0)


def test_tax_only():
    expect_equal(tax_only(100.0, "NY"), 4.0)
''',

"tests/test_shipping.py": '''\
from shop.shipping import bands, cost
from shop.support.expect import expect_equal


def test_free():
    expect_equal(cost(60.0, 9.0), 0.0)


def test_light():
    expect_equal(cost(10.0, 0.5), 4.99)


def test_mid():
    expect_equal(cost(10.0, 3.0), 8.99)


def test_heavy():
    expect_equal(cost(10.0, 9.0), 14.99)


def test_bands():
    expect_equal(bands(), [1.0, 5.0])
''',

"tests/test_cart.py": '''\
from shop.cart import item_count, subtotal
from shop.support.expect import expect_equal


def test_item_count():
    expect_equal(item_count([(1.0, 2), (2.0, 3)]), 5)


def test_subtotal_small():
    expect_equal(subtotal([(1.0, 1)]), 1.0)
''',

"tests/test_formatting.py": '''\
from shop.formatting import line, money, pct
from shop.support.expect import expect_equal


def test_money():
    expect_equal(money(3.5), "$3.50")


def test_pct():
    expect_equal(pct(0.15), "15.0%")


def test_line():
    expect_equal(line("tax", 1.0), "tax: $1.00")
''',
}

# the one-token defect: >= becomes > in the bulk tier test
DEFECT = ("shop/discount.py", "    if qty >= BULK_QTY:", "    if qty > BULK_QTY:")


def build(out, inject=True):
    if os.path.isdir(out):
        shutil.rmtree(out)
    for rel, body in FILES.items():
        p = os.path.join(out, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(body)
    if inject:
        rel, old, new = DEFECT
        p = os.path.join(out, rel)
        src = open(p).read()
        assert old in src, old
        open(p, "w").write(src.replace(old, new, 1))
    return out


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    build(out, inject="--clean" not in sys.argv)
    print("built", out, "(defect injected)" if "--clean" not in sys.argv
          else "(clean)")
