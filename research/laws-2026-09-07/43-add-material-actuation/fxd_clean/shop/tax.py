"""Sales tax."""

RATES = {"CA": 0.0725, "NY": 0.04, "OR": 0.0}


def rate_for(state):
    return RATES.get(state, 0.05)


def with_tax(amount, state):
    return round(amount * (1.0 + rate_for(state)), 2)


def tax_only(amount, state):
    return round(amount * rate_for(state), 2)
