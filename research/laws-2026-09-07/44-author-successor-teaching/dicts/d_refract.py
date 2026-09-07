# d_refract.py -- ONE taught fault class, from ONE worked example.
#
# Worked example (cglm 48839a3, "fix refract", 2024-07-15):
#     k   = 1.0f + eta * eta - eni * eni;   <- the two additive signs are
#                                              swapped with each other
#     k   = 1.0f - eta * eta + eni * eni;   <- the fix
#
# A pure rule over the line, so ONE string candidate: exchange the first
# binary ' + ' with the first binary ' - '.  Shipped kind 3 flips ONE
# additive operator; this class exchanges a PAIR, which no single kind-3
# edit can reach.
import re as _re

_PLUS, _MINUS = _re.compile(r" \+ "), _re.compile(r" - ")


def _swap_pair(line, o):
    p, m = _PLUS.search(line), _MINUS.search(line)
    if not p or not m:
        return [line]                        # not this class: NOPROGRESS
    a, b = sorted((p.span(), m.span()))
    first = " - " if a == p.span() else " + "
    second = " + " if a == p.span() else " - "
    return [line[:a[0]] + first + line[a[1]:b[0]] + second + line[b[1]:]]


register(
    4,
    "swapped-additive-pair",
    "a line whose binary + and - signs are exchanged with one another",
    _re.compile(r" \+ .* - | - .* \+ "),
    _swap_pair,
)
