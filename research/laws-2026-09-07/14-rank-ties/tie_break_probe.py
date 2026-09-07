"""Direct probes of guard.rank_observations: which key resolves a tie.

No suite runs, no git. Run:
  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python tie_break_probe.py
"""
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
import fluidfix.rank as rankmod  # noqa: E402
from fluidfix.acts import Observation  # noqa: E402
from fluidfix.guard import rank_observations  # noqa: E402
from fluidfix.rank import BITS  # noqa: E402

LOG = []
_real = rankmod.rank


def _spy(x):
    p = _real(x)
    LOG.append((x, p))
    return p


rankmod.rank = _spy      # priority() does `from .rank import rank` at call time


def show(title, src, obs, out, **kw):
    LOG.clear()
    ordered = rank_observations(src, obs, out, **kw)
    print(f"\n== {title} ==")
    for o, (x, p) in zip(obs, LOG):
        bits = "+".join(b for i, b in enumerate(BITS) if x >> i & 1) or "(none)"
        print(f"  line {o.lineno:2d} kinds={o.kinds} byte={x:08b} -> priority {p}  [{bits}]")
    print("  order chosen:", [o.lineno for o in ordered])
    return ordered


# ---------------------------------------------------------------- probe A
# Five signaled lines in ONE def; the failing test names that def. Pure
# assertion failure (no traceback frame), so no line is FRAMED. All five
# get the identical byte -> identical priority -> identical token count ->
# the incoming index (ascending line number) decides.
srcA = "\n".join([
    "def count_above(xs, t):",          # 1
    "    n = 0",                        # 2
    "    if t >= 100:",                 # 3  signaled (strictness)
    "        t = 100",                  # 4
    "    if t >= 200:",                 # 5  signaled
    "        t = 200",                  # 6
    "    if t >= 300:",                 # 7  signaled
    "        t = 300",                  # 8
    "    for x in xs:",                 # 9
    "        if x >= t:",               # 10 the defect (should be >)
    "            n += 1",               # 11 signaled (augmented assign)
    "    return n",                     # 12
])
outA = "FAILED test_mod.py::test_count_above - assert 3 == 1"
obsA = [Observation(lineno=l, kinds=[0]) for l in (3, 5, 7, 10)] + \
       [Observation(lineno=11, kinds=[9])]
show("A: identical bytes -> incoming index (line order) breaks the tie",
     srcA, obsA, outA)

# ---------------------------------------------------------------- probe B
# Same, but the observation list is handed over in REVERSE line order:
# the tie-break follows the incoming index, not the line number.
show("B: same bytes, list reversed -> the order flips with the index",
     srcA, list(reversed(obsA)), outA)

# ---------------------------------------------------------------- probe C
# Two defs; the failing test id shares 2 tokens with one def and 1 with
# the other. Both lines NAMED+SIGNALED -> priority 2 both; the token DEGREE
# (a code key under the law) puts the 2-token def first even though it
# sits later in the file.
srcC = "\n".join([
    "class FrenchLocale:",                        # 1
    "    def ordinal_number(self, n):",           # 2
    "        return n >= 1",                      # 3 signaled, tokens {french, ordinal, number}
    "",                                           # 4
    "class OdiaLocale:",                          # 5
    "    def ordinal_number(self, n):",           # 6
    "        return n >= 2",                      # 7 signaled, tokens {odia, ordinal, number}
])
outC = "FAILED tests/test_locales.py::TestOdiaLocale::test_ordinal_number - assert"
obsC = [Observation(lineno=3, kinds=[0]), Observation(lineno=7, kinds=[0])]
show("C: equal priority, token DEGREE breaks the tie (Odia incident shape)",
     srcC, obsC, outC)

# ---------------------------------------------------------------- probe D
# RECENT/CHEAP/DENSE are measured but MASKED: line 10 is CHEAP (one kind,
# < 8 candidates) while line 11 sits in a block of 8 identically-shaped
# lines (DENSE). Both SIGNALED, both NAMED -> both priority 2 -> the
# index decides; the extra evidence never reaches the ruling.
srcD = "\n".join(
    ["def count_above(xs, t):"] +
    [f"    a{i} = xs[{i}] + t" for i in range(8)] +   # 2..9 dense shape
    ["    if xs[0] >= t:",                            # 10 defect, cheap
     "        return 1",                              # 11
     "    return xs[1] + t"]                          # 12 dense shape again
)
outD = "FAILED test_mod.py::test_count_above - assert 1 == 0"
obsD = [Observation(lineno=2, kinds=[3]), Observation(lineno=10, kinds=[0])]
show("D: DENSE line 2 vs CHEAP line 10, both SIGNALED -> same priority, index wins",
     srcD, obsD, outD)

# ---------------------------------------------------------------- probe E
# The RETRIED veto is reachable through the API ... when a caller passes
# `retried`. Neither caller in guard.py does (lines 511, 585).
show("E: retried={10} passed explicitly -> the veto works at the API",
     srcD, obsD, outD, retried={10})
