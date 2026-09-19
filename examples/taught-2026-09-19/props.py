# Properties for the four taught classes — what every rewrite of each class must be true of, whatever
# code surrounds the line. Taught the same way the classes are: one statement, one checker, versioned
# beside the dictionary. Loaded with load_dictionary(), which supplies `teach_property` and `propcheck`.
#
# Why these and not properties of the repaired FUNCTION: a function property has to be written once per
# function, and only helps where someone wrote one. A class property is written once when the class is
# taught and then holds every future rewrite of that class to account — in repositories nobody has cloned
# yet, at zero suite runs.
#
# Each one is stated in English first, because the English is what a maintainer reviews.

_LEN_CALL = re.compile(r"\blen\([\w.\[\]]+\)")


# ---------------------------------------------------------------- class 7
# "The candidate must be worth exactly the original with THIS len(x) replaced by (len(x) - 1)."
#
# Every len(...) on the line becomes its own free integer on both sides, so the check ranges over every
# length those lists could ever hold rather than the lengths some test happened to use. This is the
# property that `* len(text) - 1` violated in rich while rich's own suite accepted it.
def _prop_len_minus_one(orig, cand):
    o, c = propcheck.rhs(orig), propcheck.rhs(cand)
    occ_o, occ_c = list(_LEN_CALL.finditer(o)), list(_LEN_CALL.finditer(c))
    if not occ_o or len(occ_o) != len(occ_c):
        return None, "len(...) count differs between the two lines", 0
    d = next((i for i, (x, y) in enumerate(zip(o, c)) if x != y), min(len(o), len(c)))
    k = min(sum(1 for m in occ_o if m.end() <= d), len(occ_o) - 1)

    def subst(expr, occs, target):
        out, last = [], 0
        for i, m in enumerate(occs):
            out.append(expr[last:m.start()])
            out.append(f"(__L{i} - 1)" if i == target else f"__L{i}")
            last = m.end()
        out.append(expr[last:])
        return "".join(out)

    intended, actual = subst(o, occ_o, k), subst(c, occ_c, None)
    names = sorted(set(propcheck.free_names(intended)) | set(propcheck.free_names(actual)))
    return propcheck.agree_over(intended, actual, grid=(1, 2, 3, 5, 8), names=names)


teach_property(7, "the placement must preserve the value: the candidate equals the original with "
                  "len(x) replaced by (len(x) - 1), for every length",
               _prop_len_minus_one)


# ---------------------------------------------------------------- class 4
# "Flipping one and/or TEXTUALLY must mean the same as swapping that operator at its node."
#
# `and` binds tighter than `or`, so a textual flip can regroup the expression — the same hazard class 7
# has with `- 1` under `*`. On a flattened chain (`a or b or c` is one Or of three values) the flip has
# no node-level meaning at all, and the property says so rather than guessing.
def _prop_boolean_flip(orig, cand):
    o, c = propcheck.rhs(orig), propcheck.rhs(cand)
    to = [m.start() for m in re.finditer(r"\b(and|or)\b", o)]
    tc = [m.start() for m in re.finditer(r"\b(and|or)\b", c)]
    if len(to) != len(tc):
        return None, "operator count changed", 0
    which = next((i for i, (a, b) in enumerate(zip(to, tc))
                  if o[a:a + 3].strip() != c[b:b + 3].strip()), None)
    if which is None:
        return None, "nothing flipped", 0
    intended = propcheck.nth_boolop_swapped(o, which)
    if intended is None:
        return None, "could not locate the operator", 0
    if intended == "AMB":
        return None, "flattened chain — a one-operator flip is not a node swap; rule AMB", 0
    return propcheck.agree_over(intended, c, grid=(0, 1, "", "x", (), (7,)))


teach_property(4, "the flip must not regroup: flipping the token must mean the same as swapping that "
                  "operator at its node, for every truth assignment",
               _prop_boolean_flip)


# ---------------------------------------------------------------- class 6
# "The candidate guard must be the exact negation — no value on which the two agree."
def _prop_guard_negation(orig, cand):
    o, c = propcheck.rhs(orig), propcheck.rhs(cand)
    names = sorted(set(propcheck.free_names(o)) | set(propcheck.free_names(c)))
    co, cc = compile(o, "<o>", "eval"), compile(c, "<c>", "eval")
    import itertools as _it
    n = 0
    for combo in _it.product(propcheck.TRUTH_GRID, repeat=len(names)):
        env = dict(propcheck.SAFE); env.update(dict(zip(names, combo)))
        try:
            a, b = bool(eval(co, env)), bool(eval(cc, env))
        except Exception:
            continue
        n += 1
        if a == b:
            return False, f"{dict(zip(names, combo))} -> both {a}; not a negation", n
    return True, "", n


teach_property(6, "the candidate must be the exact negation of the original guard, on every value",
               _prop_guard_negation)


# ---------------------------------------------------------------- class 5
# "Supplying a default may only change what happens when the key is ABSENT."
_GET = re.compile(r"\.get\(\s*((?:\"[^\"]*\"|'[^']*'))\s*(?:,\s*(.+?)\s*)?\)")


def _prop_get_default(orig, cand):
    o, c = propcheck.rhs(orig), propcheck.rhs(cand)
    mo = _GET.search(o)
    if not mo or mo.group(2) is not None:
        return None, "no bare .get(key) on the line", 0
    import ast as _ast
    key = _ast.literal_eval(mo.group(1))
    names = sorted(set(propcheck.free_names(o)) | set(propcheck.free_names(c)))
    co, cc = compile(o, "<o>", "eval"), compile(c, "<c>", "eval")
    n = 0
    for v in ("", "a", 0, 1, [], None, "z", 5):
        d = {key: v, "other": 9}
        env = dict(propcheck.SAFE); env.update({nm: d for nm in names})
        try:
            va = eval(co, env)
        except Exception:
            continue
        try:
            vb = eval(cc, env)
        except Exception as e:
            return False, f"{d} -> candidate raised {type(e).__name__}", n
        n += 1
        if va != vb:
            return False, f"key present in {d} -> was {va!r}, now {vb!r}", n
    return True, "", n


teach_property(5, "supplying a default may only change the key-absent case: on every mapping that holds "
                  "the key, the candidate returns what the original did",
               _prop_get_default)
