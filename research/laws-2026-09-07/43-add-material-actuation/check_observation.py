#!/usr/bin/env python
"""Text-only checks of the UNREAD observation (0 suite runs)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import widen as W

CASES = {
"helper carries the assert (fixture A/B shape)": ("""
    def test_tier_bulk():
>       expect_close(tier(10), 0.15)

tests/test_discount.py:6: 
_ _ _ _ _ _
    def expect_close(got, want, tol=1e-9):
>       assert abs(got - want) <= tol
E       AssertionError

shop/support/expect.py:13: AssertionError
FAILED tests/test_discount.py::test_tier_bulk - AssertionError
""", {"shop/support/expect.py"}),

"test carries the assert (ordinary case)": ("""
    def test_tier_bulk():
>       assert tier(10) == 0.15
E       assert 0.05 == 0.15

tests/test_discount.py:6: AssertionError
FAILED tests/test_discount.py::test_tier_bulk - assert 0.05 == 0.15
""", set()),

"the DEFECT FILE itself raises on an assert (false-positive probe)": ("""
    def test_tier_bulk():
>       tier(10)

tests/test_discount.py:6: 
_ _ _ _ _ _
    def tier(qty):
>       assert qty > BULK_QTY
E       AssertionError

shop/discount.py:10: AssertionError
FAILED tests/test_discount.py::test_tier_bulk - AssertionError
""", {"shop/discount.py"}),

"exception, not an assert, inside a source file": ("""
    def test_x():
>       total([(1.0, 0)], "CA", 1.0)

tests/test_cart.py:9: 
_ _ _ _ _ _
    def total(lines, state, weight_kg):
>       return round(with_tax(sub, state) / cost(sub, weight_kg), 2)
E       ZeroDivisionError: float division by zero

shop/cart.py:14: ZeroDivisionError
FAILED tests/test_cart.py::test_x - ZeroDivisionError
""", set()),
}

for name, (out, want) in CASES.items():
    got = W.assertion_carriers(out)
    print("%-52s carriers=%-30s expected=%-30s %s"
          % (name, sorted(got), sorted(want), "OK" if got == want else "MISMATCH"))
    print("    UNREAD given framed=%s -> %s"
          % (sorted(want) or ["<none>"], W.unread(sorted(got), got)))
