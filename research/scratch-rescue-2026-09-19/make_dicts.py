"""Write four staged dictionaries by hand: dict_K holds the first K taught classes, slots 4..7.

The earlier attempt sliced these out of the source files by string index and produced files that began
mid-comment. Assembling them explicitly is both correct and easier to check.
"""
from pathlib import Path

HERE = Path("/Users/kanchetidevieswar/neo/fluidfix/research/generalise-2026-09-18")

HEAD = '''# Staged vocabulary for research/generalise-2026-09-18 — the first {k} taught class(es).
# Slot 4 and 5 were written from the edit-budget ladder's own output (../kindof-2026-09-18), from faults
# real models actually wrote. Slots 6 and 7 are the 2026-09-16 session's classes, unchanged.
'''

SLOT4 = '''

# ---- slot 4: the mutating call whose result is dropped
#   items.insert(index, value)   ->   return items.insert(index, value) or items
# A collection is mutated in place on the last line and never returned, so the caller gets None. The fault
# IS a missing return, which no line transform can insert — but the mutation line can BECOME the return,
# because a mutating method answers None and `or` then yields the collection.

def _return_the_mutated(line, o):
    m = re.match(r"^(\\s*)([A-Za-z_]\\w*)\\.(\\w+)\\((.*)\\)\\s*$", line)
    if not m:
        return []
    indent, receiver, _meth, _args = m.groups()
    return [f"{indent}return {line.strip()} or {receiver}"]


register(4, "mutating-call-whose-result-is-dropped",
         "a collection is mutated in place on the last line and never returned, so the caller gets None",
         re.compile(r"^\\s*[A-Za-z_]\\w*\\.\\w+\\(.*\\)\\s*$"),
         _return_the_mutated)
'''

SLOT5 = '''

# ---- slot 5: the missing separator before an appended token
#   return ' '.join(parts[:limit]) + '...'   ->   + ' ...'
# A token is appended to a joined string and the separator that joins the rest is forgotten.

def _add_separator(line, o):
    out = []
    for q in ("'", '"'):
        m = re.search(r"\\+\\s*" + q + r"(?! )([^" + q + r"]*)" + q + r"\\s*$", line)
        if m:
            out.append(line[: m.start(1)] + " " + line[m.start(1):])
    return out


register(5, "missing-separator-before-appended-token",
         "a token is concatenated onto a joined string without the separator that joins the rest",
         re.compile(r"\\+\\s*['\\"][^'\\"]*['\\"]\\s*$"),
         _add_separator)
'''

SLOT6 = '''

# ---- slot 6: the inverted bare guard (taught 2026-09-16, click shell_completion.py)
#   if value:        ->   if not value:

def _negate_guard(line, o):
    m = re.match(r"^(\\s*)(if|elif|while) (\\w+):\\s*$", line)
    if not m:
        return [line]
    ind, kw, name = m.groups()
    return [f"{ind}{kw} not {name}:"]


register(6, "inverted-bare-guard",
         "a bare-name guard `if X:` that should read `if not X:`",
         re.compile(r"^\\s*(?:if|elif|while) \\w+:\\s*$"),
         _negate_guard)
'''

SLOT7 = '''

# ---- slot 7: len(x) standing where len(x) - 1 belongs (taught 2026-09-16, click utils.py:84)

def _len_minus_one(line, o):
    out = []
    for m in re.finditer(r"\\blen\\([\\w.\\[\\]]+\\)(?!\\s*[-+*/%])", line):
        out.append(line[:m.end()] + " - 1" + line[m.end():])
    return out or [line]


register(7, "len-as-last-index",
         "a len(x) standing where the last valid index len(x) - 1 belongs",
         re.compile(r"\\blen\\([\\w.\\[\\]]+\\)(?!\\s*[-+*/%])"),
         _len_minus_one)
'''

SLOTS = [SLOT4, SLOT5, SLOT6, SLOT7]
for k in range(1, 5):
    (HERE / f"dict_{k}.py").write_text(HEAD.format(k=k) + "".join(SLOTS[:k]))
print("wrote dict_1..dict_4")
