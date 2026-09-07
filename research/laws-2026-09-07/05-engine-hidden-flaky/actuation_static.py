"""Static check: at the HIDDEN site (src/fluidfix/loop.py:391), is the law's
ruling used for anything other than the text of the message?

`ruling` is assigned from decide() in TWO places in loop.py and one of them
(_rule) is a function nested inside the other (repair), so a naive ast.walk
mixes them. This walks each function's OWN body only (nested defs excluded)
and reports, per assignment, whether the name later reaches a control-flow
test or only an f-string.
Run: .venv/bin/python actuation_static.py
"""
import ast

PATH = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/loop.py"
tree = ast.parse(open(PATH).read(), PATH)
FUNC = (ast.FunctionDef, ast.AsyncFunctionDef)


def own_nodes(fn):
    """Every node in fn's body, NOT descending into nested function defs."""
    stack = [n for n in fn.body if not isinstance(n, FUNC)]
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if not isinstance(c, FUNC):
                stack.append(c)


def calls_decide(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "decide")


for fn in ast.walk(tree):
    if not isinstance(fn, FUNC):
        continue
    body = list(own_nodes(fn))
    assigns = [(t.id, n.lineno) for n in body if isinstance(n, ast.Assign)
               and calls_decide(n.value) for t in n.targets
               if isinstance(t, ast.Name)]
    for name, at in assigns:
        tests, strings = [], []
        for n in body:
            if isinstance(n, (ast.If, ast.While)):
                for u in ast.walk(n.test):
                    if isinstance(u, ast.Name) and u.id == name:
                        tests.append(n.lineno)
            if isinstance(n, ast.JoinedStr):
                for u in ast.walk(n):
                    if isinstance(u, ast.Name) and u.id == name:
                        strings.append(n.lineno)
        print(f"loop.py:{at}  in {fn.name}(): `{name} = decide(...)`")
        print(f"   reaches an if/while test at: {sorted(set(tests)) or 'NOWHERE'}")
        print(f"   reaches an f-string at     : {sorted(set(strings)) or 'NOWHERE'}")
        print("   => " + ("ACTUATED: control flow depends on the ruling"
                          if tests else
                          "NOT ACTUATED: the ruling reaches the WORDING only"))
