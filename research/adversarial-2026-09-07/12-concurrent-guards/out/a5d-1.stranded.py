"""A tiny module with one mechanical defect."""


def total(units, price):
    return units * price


def grade(score):
    # DEFECT: should be `score < 60`
    if score > 59:
        return "F"
    return "P"


def bill(units, price):
    return total(units, price)
