"""A tiny module with one mechanical defect."""


def total(units, price):
    return units * price


def discount(units):
    # FIXED BY THE USER, by hand, after fluidfix died. Reviewed. Correct.
    if units >= 10:
        return 0.9
    return 1.0


def bill(units, price):
    return total(units, price) * discount(units)


def tax(amount):
    """USER CODE written after the crash. Not fluidfix's to touch."""
    return amount * 0.08
