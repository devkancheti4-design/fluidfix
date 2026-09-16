# rules_session_b.py — the fifth class of the 2026-09-16 study (the user slots 4..7 of rules_session.py are full).
# kind 4 — incident: a loop over positions started at 0 instead of 1 (sortedcontainers sortedlist.py:2465)
#   for pos in range(len(self._keys)):        <- shipped
#   for pos in range(1, len(self._keys)):     <- the fix
# The class: a single-argument range() whose first index is not zero. The only live instance of this
# class in the study is the teaching example itself, so it has no held-out test — stated in the write-up.
def _range_from_one(line, o):
    out = []
    for m in re.finditer(r"\brange\((?=(?:[^,()]|\([^()]*\))+\))", line):   # one argument, one nesting level (len(x))
        out.append(line[:m.end()] + "1, " + line[m.end():])
    return out or [line]

register(4, "range-start-dropped",
         "a one-argument range() over positions that should begin at 1",
         re.compile(r"\brange\((?=(?:[^,()]|\([^()]*\))+\))"),
         _range_from_one)
