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
