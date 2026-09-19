# len-as-last-index, re-authored so the PLACEMENT LAW decides where the token goes.
#
# The 2026-09-16 version appended " - 1" immediately after the closing paren, which is correct where
# len(...) is the whole right-hand side (the shape of its one worked example), correct under `+` by
# associativity, correct inside a call — and wrong under any operator binding tighter than `-`. Measured
# 12/12, 12/12, 12/12 and 0/12 across those four forms, and it shipped `* len(text) - 1` into rich where
# the maintainer had written `* (len(text) - 1)`.
#
# The applier no longer decides. It measures the syntactic context into a situation word and asks the law.

from fluidfix.place import insert_token


def _len_minus_one(line, o):
    out = []
    for m in re.finditer(r"\blen\([\w.\[\]]+\)(?!\s*[-+*/%])", line):
        out.append(insert_token(line, m.start(), m.end(), " - 1"))
    return out or [line]


register(7, "len-as-last-index",
         "a len(x) standing where the last valid index len(x) - 1 belongs",
         re.compile(r"\blen\([\w.\[\]]+\)(?!\s*[-+*/%])"),
         _len_minus_one)
