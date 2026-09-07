#!/usr/bin/env python
"""Variant C: same misdirection shape, defect movable to a DIFFERENT file, so
the widening measurement is not a one-file fluke.  Adds the boundary tests the
alternate defect sites need.

Usage: python make_fixture_c.py OUTDIR --defect=shipping|cart|formatting
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_fixture as A

DEFECTS = {
    # file, original token line, defective line
    "shipping":   ("shop/shipping.py", "    if weight_kg <= 1.0:",
                                       "    if weight_kg < 1.0:"),
    "cart":       ("shop/cart.py", "    return sum(q for _, q in lines)",
                                   "    return sum(q - 1 for _, q in lines)"),
    "formatting": ("shop/formatting.py", '    return "%.2f" % x',
                                         '    return "%.3f" % x'),
}


def files_with_boundaries():
    f = dict(A.FILES)
    f["tests/test_shipping.py"] = f["tests/test_shipping.py"] + '''

def test_light_boundary():
    expect_equal(cost(10.0, 1.0), 4.99)
'''
    f["shop/formatting.py"] = '''\
"""Money formatting."""


def money(x):
    return "%.2f" % x


def pct(x):
    return "%.1f%%" % (x * 100.0)


def line(name, amount):
    return "%s: $%s" % (name, money(amount))
'''
    f["tests/test_formatting.py"] = '''\
from shop.formatting import line, money, pct
from shop.support.expect import expect_equal


def test_money():
    expect_equal(money(3.5), "3.50")


def test_pct():
    expect_equal(pct(0.15), "15.0%")


def test_line():
    expect_equal(line("tax", 1.0), "tax: $1.00")
'''
    return f


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    which = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--defect=")]
    A.FILES = files_with_boundaries()
    A.DEFECT = DEFECTS[which[0]] if which else A.DEFECT
    A.build(out, inject=bool(which))
    print("built", out, "defect:", which[0] if which else "(clean)")
