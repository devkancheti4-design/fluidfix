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
    return sum(q - 1 for _, q in lines)
