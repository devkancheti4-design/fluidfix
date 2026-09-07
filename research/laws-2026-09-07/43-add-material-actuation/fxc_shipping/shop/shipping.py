"""Shipping bands."""

FREE_OVER = 50.0


def cost(subtotal, weight_kg):
    if subtotal >= FREE_OVER:
        return 0.0
    if weight_kg < 1.0:
        return 4.99
    if weight_kg <= 5.0:
        return 8.99
    return 14.99


def bands():
    return [1.0, 5.0]
