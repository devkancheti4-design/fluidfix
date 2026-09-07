"""Money formatting."""


def money(x):
    return "%.3f" % x


def pct(x):
    return "%.1f%%" % (x * 100.0)


def line(name, amount):
    return "%s: $%s" % (name, money(amount))
