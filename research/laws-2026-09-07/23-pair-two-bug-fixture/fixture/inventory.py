"""Stock-level policy.

FAULT B is on line 11: `on_hand > reorder_point` should be
`on_hand < reorder_point` (fluidfix kind 10, flipped-comparison-direction).
One token, in-vocabulary. Independent of billing.py: no import, no shared
state, no shared call path.
"""


def needs_reorder(on_hand, reorder_point):
    return on_hand > reorder_point


def restock_amount(on_hand, target):
    return target - on_hand
