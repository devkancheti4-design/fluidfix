"""The taught appliers, as a territory a guard can enter.

Each spec below is the class's own description. The suite in test_appliers.py is derived from it.
"""
import re

# spec: a collection is mutated in place on the last line and never returned, so the caller gets None.
# The repaired line must return the collection WHATEVER the mutating call answers.
def mutating_call_dropped(line):
    m = re.match(r"^(\s*)([A-Za-z_]\w*)\.(\w+)\((.*)\)\s*$", line)
    if not m:
        return []
    indent, receiver, _meth, _args = m.groups()
    # The call is still performed first (it is the mutation), but its answer is
    # discarded: the tuple is indexed, not truth-tested, so a truthy return such
    # as the item from .pop() can never stand in for the collection.
    return [f"{indent}return ({line.strip()}, {receiver})[1]"]


# spec: a len(x) standing where the last valid index len(x) - 1 belongs. The repaired line must subtract
# one from the CALL, whatever surrounds it.
def len_as_last_index(line):
    out = []
    # The " - 1" is bracketed onto the call itself, so it binds to len(...) and
    # not to whatever expression the call sits inside. Only a call that already
    # reads len(...) - 1 is left alone.
    for m in re.finditer(r"\blen\([\w.\[\]]+\)(?!\s*-\s*1\b)", line):
        out.append(line[:m.start()] + "(" + m.group(0) + " - 1)" + line[m.end():])
    return out or [line]


# spec: a bare-name guard `if X:` that should read `if not X:`.
def inverted_bare_guard(line):
    m = re.match(r"^(\s*)(if|elif|while) (\w+):\s*$", line)
    if not m:
        return [line]
    ind, kw, name = m.groups()
    return [f"{ind}{kw} not {name}:"]
