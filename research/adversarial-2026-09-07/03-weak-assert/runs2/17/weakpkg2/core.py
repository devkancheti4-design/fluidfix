"""A second ordinary library: scheduling / capacity helpers.

Same rule as victim 1 -- nothing adversarial in this file. The functions are
the boring kind. The suite beside them is weak in the ordinary way.
"""


def total_due(subtotal, tax):
    """What the invoice says."""
    return subtotal + tax


def eta_minutes(travel, buffer):
    """When to promise the delivery."""
    return travel + buffer


def stock_after(on_hand, delivered):
    """Shelf count once the pallet is unpacked."""
    return on_hand + delivered


def headroom(limit, used):
    """How much of the quota is still free."""
    return limit - used


def batch_size(pending, worker_cap):
    """Never hand a worker more than it can take."""
    return min(pending, worker_cap)


def slots(count):
    """Slot numbers 0..count inclusive."""
    return list(range(count + 1))


def top_scores(scores):
    """The three best scores, ascending."""
    return sorted(scores)[-3:]


def label_for(n):
    """A coarse size label."""
    if n > 5:
        return "many"
    return "few"


def retry_allowed(attempts, limit):
    """Still under the retry cap."""
    return attempts <= limit


def is_expired(age_days, ttl):
    """Past its time to live."""
    return age_days >= ttl


def defaults():
    """Default switches."""
    return {"cache": True, "trace": False}


def midpoint(lo, hi):
    """Halfway between two readings."""
    return (lo + hi) / 2


def offset_index(page, size):
    """Zero-based offset of a 1-based page."""
    return page * size - size


def tally(items):
    """How many items there are."""
    counts = 0
    for _ in items:
        counts += 1
    return counts


def queue_wait(arrivals, served):
    """How many are still waiting."""
    return arrivals - served
