def count_above(xs, t):
    n = 0
    for x in xs:
        if x >= t:
            n += 1
    return n
