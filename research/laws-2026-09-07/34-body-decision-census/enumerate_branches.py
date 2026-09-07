"""Enumerate every branch point in the five body files, mechanically.

Counts: `if` / `elif` statements, ternary IfExp, comprehension `if` guards,
`and`/`or` short-circuits used as a decision, and `while` conditions.
Prints file:line, node kind, enclosing function, and the source text.
Classification (law-ruled vs code-decided) is done by hand in REPORT.md;
this script only guarantees the census is COMPLETE.
"""
import ast, sys, os

FILES = ["loop.py", "guard.py", "acts.py", "oracle.py", "coracle.py"]
SRC = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix"

def enclosing(tree):
    """line -> innermost def/class name"""
    owner = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for l in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                prev = owner.get(l)
                owner[l] = node.name if prev is None else prev + "." + node.name
    return owner

total = 0
rows = []
for fn in FILES:
    path = os.path.join(SRC, fn)
    src = open(path, encoding="utf-8").read()
    lines = src.split("\n")
    tree = ast.parse(src)
    own = enclosing(tree)
    for node in ast.walk(tree):
        kind = None
        if isinstance(node, ast.If):
            kind = "if/elif"
        elif isinstance(node, ast.IfExp):
            kind = "ternary"
        elif isinstance(node, ast.While):
            kind = "while"
        elif isinstance(node, ast.comprehension):
            for g in node.ifs:
                rows.append((fn, g.lineno, "comp-if", own.get(g.lineno, "-"),
                             lines[g.lineno - 1].strip()[:100]))
                total += 1
            continue
        elif isinstance(node, ast.BoolOp):
            kind = "boolop(%s)" % type(node.op).__name__.lower()
        if kind:
            rows.append((fn, node.lineno, kind, own.get(node.lineno, "-"),
                         lines[node.lineno - 1].strip()[:100]))
            total += 1

rows.sort(key=lambda r: (FILES.index(r[0]), r[1]))
for r in rows:
    print(f"{r[0]}:{r[1]:<4} {r[2]:<14} {r[3]:<28} {r[4]}")
print(f"\nTOTAL branch points: {total}")
from collections import Counter
print(Counter(r[0] for r in rows))
print(Counter(r[2] for r in rows))
