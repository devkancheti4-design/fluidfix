def count_above(xs, t):
    n = 0
    lo = 0
    if t >= 1000:
        lo = 1
    if t >= 2000:
        lo = 2
    if t >= 3000:
        lo = 3
    if t >= 4000:
        lo = 4
    for x in xs:
        if x > t:
            n += 1
    return n + lo
