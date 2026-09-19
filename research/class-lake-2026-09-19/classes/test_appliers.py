"""The suite for the appliers — the spec, made executable.

A class is judged the way any repair is judged, but one level up. For each case: apply the class to a
broken line, run the resulting program, and then **check it on a second input the case never used**. That
second check is the whole point. A class that proposes a line the test rejects is merely narrow; a class
that proposes a line the test ACCEPTS and that is wrong is a latent false accept, and only the second input
tells them apart.

Every case here is an incident: either the worked example the class was taught from, or a shape it was
later found to get wrong.
"""
import appliers


def repaired(applier, code, line_no):
    lines = code.split("\n")
    for cand in applier(lines[line_no]):
        trial = lines[:]
        trial[line_no] = cand
        ns = {}
        try:
            exec("\n".join(trial), ns)
        except Exception:
            continue
        fn = next(v for k, v in ns.items() if callable(v) and not k.startswith("_"))
        return fn
    return None


# ---- mutating-call-whose-result-is-dropped
def test_mutating_append_the_taught_example():
    f = repaired(appliers.mutating_call_dropped, "def add(xs, v):\n    xs.append(v)", 1)
    assert f is not None and f([1], 2) == [1, 2] and f([5], 6) == [5, 6]


def test_mutating_pop_whose_call_answers_the_item():
    # the incident: `pop` answers the popped item, so `or` reaches the collection only when it is falsy.
    f = repaired(appliers.mutating_call_dropped, "def drop_last(xs):\n    xs.pop()", 1)
    assert f is not None
    assert f([1, 2, 0]) == [1, 2]          # the input the original test used
    assert f([9, 8, 7]) == [9, 8]          # the second input — this is what catches it


def test_mutating_sort():
    f = repaired(appliers.mutating_call_dropped, "def ordered(xs):\n    xs.sort()", 1)
    assert f is not None and f([3, 1, 2]) == [1, 2, 3] and f([9, 7, 8]) == [7, 8, 9]


# ---- len-as-last-index
def test_len_is_the_whole_right_hand_side():
    f = repaired(appliers.len_as_last_index, "def last(xs):\n    return len(xs)", 1)
    assert f is not None and f([0, 1, 2]) == 2 and f([0] * 7) == 6


def test_len_as_an_operand_of_times():
    # the incident: ` - 1` trailed outside the multiplication is (k*len) - 1, not k*(len-1).
    f = repaired(appliers.len_as_last_index, "def scaled(xs, k):\n    return k * len(xs)", 1)
    assert f is not None
    assert f([0, 1, 2], 2) == 4
    assert f([0] * 5, 3) == 12


# ---- inverted-bare-guard
def test_inverted_guard():
    f = repaired(appliers.inverted_bare_guard,
                 "def head(xs):\n    if xs:\n        return None\n    return xs[0]", 1)
    assert f is not None and f([]) is None and f([7]) == 7


# ---- the criterion the project is actually scored on: the ORIGINAL BYTES come back
#
# Semantic correctness on a second input is not enough. The real-repo study counts a repair only when the
# line it produces equals the pre-mutation original byte for byte, and every lenm1 original in that corpus
# is unparenthesised. A class that brackets unconditionally is semantically right and scores zero here.
BYTE_EXACT = [
    ("elif index == len(timeframes):  # Must have at least 2 items",
     "elif index == len(timeframes) - 1:  # Must have at least 2 items"),
    ("    last_index = len(words)", "    last_index = len(words) - 1"),
    ("    max_pos = len(_maxes)", "    max_pos = len(_maxes) - 1"),
    ("    last_column = column_index == len(self.columns)",
     "    last_column = column_index == len(self.columns) - 1"),
]


def test_len_restores_the_original_bytes():
    for mutated, original in BYTE_EXACT:
        assert original in appliers.len_as_last_index(mutated), (
            f"no candidate restores the original bytes for {mutated!r}")
