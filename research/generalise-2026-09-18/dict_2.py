# Staged vocabulary for research/generalise-2026-09-18 — the first 2 taught class(es).
# Slot 4 and 5 were written from the edit-budget ladder's own output (../kindof-2026-09-18), from faults
# real models actually wrote. Slots 6 and 7 are the 2026-09-16 session's classes, unchanged.


# ---- slot 4: the mutating call whose result is dropped
#   items.insert(index, value)   ->   return items.insert(index, value) or items
# A collection is mutated in place on the last line and never returned, so the caller gets None. The fault
# IS a missing return, which no line transform can insert — but the mutation line can BECOME the return,
# because a mutating method answers None and `or` then yields the collection.

def _return_the_mutated(line, o):
    m = re.match(r"^(\s*)([A-Za-z_]\w*)\.(\w+)\((.*)\)\s*$", line)
    if not m:
        return []
    indent, receiver, _meth, _args = m.groups()
    return [f"{indent}return {line.strip()} or {receiver}"]


register(4, "mutating-call-whose-result-is-dropped",
         "a collection is mutated in place on the last line and never returned, so the caller gets None",
         re.compile(r"^\s*[A-Za-z_]\w*\.\w+\(.*\)\s*$"),
         _return_the_mutated)


# ---- slot 5: the missing separator before an appended token
#   return ' '.join(parts[:limit]) + '...'   ->   + ' ...'
# A token is appended to a joined string and the separator that joins the rest is forgotten.

def _add_separator(line, o):
    out = []
    for q in ("'", '"'):
        m = re.search(r"\+\s*" + q + r"(?! )([^" + q + r"]*)" + q + r"\s*$", line)
        if m:
            out.append(line[: m.start(1)] + " " + line[m.start(1):])
    return out


register(5, "missing-separator-before-appended-token",
         "a token is concatenated onto a joined string without the separator that joins the rest",
         re.compile(r"\+\s*['\"][^'\"]*['\"]\s*$"),
         _add_separator)
