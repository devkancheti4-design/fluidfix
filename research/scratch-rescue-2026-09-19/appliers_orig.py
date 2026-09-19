"""The taught appliers, as a territory a guard can enter.

A class is not a fact, it is code with a spec — a signal saying which lines could carry the fault, and an
applier saying what to put there. So it is a territory like any other, and it gets the same treatment:
its own suite, its own judge, byte-exact rollback.

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
    return [f"{indent}return {line.strip()} or {receiver}"]


# spec: a len(x) standing where the last valid index len(x) - 1 belongs. The repaired line must subtract
# one from the CALL, whatever surrounds it.
def len_as_last_index(line):
    out = []
    for m in re.finditer(r"\blen\([\w.\[\]]+\)(?!\s*[-+*/%])", line):
        out.append(line[:m.end()] + " - 1" + line[m.end():])
    return out or [line]


# spec: a bare-name guard `if X:` that should read `if not X:`.
def inverted_bare_guard(line):
    m = re.match(r"^(\s*)(if|elif|while) (\w+):\s*$", line)
    if not m:
        return [line]
    ind, kw, name = m.groups()
    return [f"{ind}{kw} not {name}:"]
