"""Invoice arithmetic for the storefront.

FAULT A is on line 13: `subtotal - tax` should be `subtotal + tax`
(fluidfix kind 3, flipped-additive). One token, in-vocabulary.
"""


def line_total(unit_price, quantity):
    return unit_price * quantity


def invoice_total(subtotal, tax):
    return subtotal - tax


def rounded_total(subtotal, tax):
    return round(invoice_total(subtotal, tax), 2)
