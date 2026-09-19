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


# The signal was narrowed on 2026-09-19: `(?!\s*[-+*/%])` suppressed repair whenever ANY operator
# followed, refusing `len(xs) * 2` and `len(xs) + 3` outright. This skips only an already-correct line.
# The PLACEMENT stays the law's: bracketing unconditionally is semantically correct and scores 0 of 4 on
# byte-exact restoration against the real-repo corpus, where every lenm1 original is unparenthesised.
_LEN = re.compile(r"\blen\([\w.\[\]]+\)(?!\s*-\s*1\b)")


def _len_minus_one(line, o):
    return [insert_token(line, m.start(), m.end(), " - 1") for m in _LEN.finditer(line)] or [line]


register(7, "len-as-last-index",
         "a len(x) standing where the last valid index len(x) - 1 belongs",
         _LEN,
         _len_minus_one)


# ---------------------------------------------------------------- class 5, re-authored
#
# The 2026-09-18 version proposed  `return CALL or RECEIVER`, which is correct only when CALL answers
# None. Its signal matches ANY bare method call, so the same defect shape as class 7: the signal
# generalises and the semantics do not. Audited 2026-09-19:
#
#     xs.append(v)   -> return xs.append(v) or xs      correct   (append answers None)
#     xs.pop()       -> return xs.pop() or xs          WRONG     (pop answers the item)
#
# and it is not merely narrow, it is a latent WRONG ACCEPT: `drop_last([1,2,0]) == [1,2]` passes, because
# the popped 0 is falsy, while `drop_last([9,8,7])` then returns 9 instead of [9,8].
#
# Whether a call answers None is not decidable from the line, so the applier must stop needing to know.
# A tuple discards the result positionally and depends on nothing:
#
#     return (CALL, RECEIVER)[-1]
#
# The call still happens, for its effect; its answer is never consulted.

def _return_the_mutated_safely(line, o):
    m = re.match(r"^(\s*)([A-Za-z_]\w*)\.(\w+)\((.*)\)\s*$", line)
    if not m:
        return []
    indent, receiver, _meth, _args = m.groups()
    return [f"{indent}return ({line.strip()}, {receiver})[-1]"]


register(5, "mutating-call-whose-result-is-dropped",
         "a collection is mutated in place on the last line and never returned, so the caller gets None",
         re.compile(r"^\s*[A-Za-z_]\w*\.\w+\(.*\)\s*$"),
         _return_the_mutated_safely)
