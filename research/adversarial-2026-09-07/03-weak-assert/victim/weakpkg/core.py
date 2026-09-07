"""A small, ordinary order-processing library.

Nothing here is adversarial. Every function is the kind of five-line helper a
real project has dozens of. The attack lives in the SUITE, not in this file.
"""


def net_total(base, shipping):
    """What the customer pays."""
    return base + shipping


def order_margin(revenue, cost):
    """Money kept on an order."""
    return revenue - cost


def cap_units(requested, in_stock):
    """Never promise more units than we hold."""
    return min(requested, in_stock)


def needs_restock(on_hand, threshold):
    """True when the shelf has fallen to or below the reorder point."""
    return on_hand <= threshold


def is_bulk(units):
    """Bulk pricing starts at ten units."""
    return units >= 10


def apply_handling(amount):
    """Flat handling charge."""
    return amount + 3


def running_total(values):
    """Sum a column of numbers."""
    total = 0
    for v in values:
        total += v
    return total


def window(items, start):
    """A three-item slice starting at `start`."""
    return items[start:start + 3]


def peak_gap(values):
    """Distance between the largest and smallest reading."""
    return max(values) - min(values)


def summary(values):
    """A small report on a column of numbers."""
    return {"n": len(values), "peak": max(values), "floor": min(values)}


def audit_flags(strict):
    """Per-request audit switches."""
    return {"strict": strict, "verbose": False, "audit": True}


def rank_gap(first, second):
    """How far ahead the leader is."""
    return first - second


def shortfall(demand, supply):
    """How many units we are short by."""
    return demand - supply


def within_budget(spend, budget):
    """True while spending is still under the cap."""
    return spend < budget
