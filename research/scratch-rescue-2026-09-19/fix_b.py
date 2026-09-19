from math import ceil


def percentile(values, p):
    """Nearest-rank percentile of a non-empty list: the value at rank ceil(p/100 * n),
    counting from 1 in the sorted order."""
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    rank = ceil(p / 100 * n)
    if rank < 1:
        rank = 1
    if rank > n:
        return values[-1]
    if rank == n:
        return values[-1]
    return values[rank - 1]
