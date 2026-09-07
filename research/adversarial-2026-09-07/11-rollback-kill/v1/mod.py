def count_above(xs, t):
    n = -1
    for x in xs:
        if x >= t:
            n += 1
    return n
