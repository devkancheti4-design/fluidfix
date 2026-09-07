"""A tiny module with one mechanical defect."""


def total(units, price):
    return units * price


def discount(units):
    # DEFECT: should be `units >= 10`
    if units > 10:
        return 0.9
    return 1.0


def bill(units, price):
    return total(units, price) * discount(units)
