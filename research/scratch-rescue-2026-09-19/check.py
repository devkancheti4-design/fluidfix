import importlib.util, textwrap
spec = importlib.util.spec_from_file_location("appliers", "appliers_fixed.py")
appliers = importlib.util.module_from_spec(spec); spec.loader.exec_module(appliers)

def repaired(applier, src, lineno):
    lines = src.split("\n")
    cands = applier(lines[lineno])
    assert cands, "no candidate"
    lines[lineno] = cands[0]
    code = "\n".join(lines)
    ns = {}
    exec(code, ns)
    print("  >>", repr(lines[lineno]))
    return ns[code.split("def ",1)[1].split("(",1)[0]]

f = repaired(appliers.mutating_call_dropped, "def drop_last(xs):\n    xs.pop()", 1)
assert f([1,2,0]) == [1,2], f([1,2,0])
assert f([9,8,7]) == [9,8], f([9,8,7])

f = repaired(appliers.mutating_call_dropped, "def add(xs, v):\n    xs.append(v)", 1)
assert f([1,2], 3) == [1,2,3]
assert f([], 0) == [0]

f = repaired(appliers.mutating_call_dropped, "def s(xs):\n    xs.sort()", 1)
assert f([3,1,2]) == [1,2,3]

f = repaired(appliers.len_as_last_index, "def scaled(xs, k):\n    return k * len(xs)", 1)
assert f([0,1,2], 2) == 4, f([0,1,2],2)

f = repaired(appliers.len_as_last_index, "def last(xs):\n    return len(xs)", 1)
assert f([5,6,7]) == 2, f([5,6,7])

f = repaired(appliers.len_as_last_index, "def idx(xs):\n    return xs[len(xs)]", 1)
assert f([5,6,7]) == 7

f = repaired(appliers.inverted_bare_guard, "def g(flag):\n    if flag:\n        return 'a'\n    return 'b'", 1)
assert f(True) == 'b' and f(False) == 'a'

# idempotence / already-correct len
print(appliers.len_as_last_index("    return len(xs) - 1"))
print(appliers.mutating_call_dropped("    return x"))
print("ALL OK")
