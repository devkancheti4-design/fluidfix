# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helpers for writing a class property — the reusable part of exhaustive checking.

A taught file defines its own applier; it defines its own property checker the same way. What is general,
and lives here, is the machinery for saying "these two expressions must agree over this whole domain".
"""
from __future__ import annotations

import ast
import itertools
import re

SAFE = {"len": len, "int": int, "min": min, "max": max, "abs": abs,
        "str": str, "bool": bool, "sorted": sorted, "sum": sum}

# values that exercise every truthiness path a Python object can take
TRUTH_GRID = (0, 1, -1, "", "x", (), (7,), [], [0], None, 0.0)


def free_names(expr: str) -> list:
    """Every name in the expression that is not a builtin we supply."""
    tree = ast.parse(expr, mode="eval")
    return sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id not in SAFE})


def rhs(line: str) -> str:
    """The expression a line is about: after `=`, after `return`, or the whole condition."""
    s = line.strip().rstrip(":")
    for kw in ("return ", "if ", "elif ", "while "):
        if s.startswith(kw):
            return s[len(kw):]
    m = re.match(r"^[\w.\[\]]+\s*=\s*(.+)$", s)
    return m.group(1) if m else s


def agree_over(a: str, b: str, grid, names=None):
    """Do two expressions agree on every point of `grid ** names`? -> (ok, witness, n_evaluated).

    A point where the INTENDED side raises is skipped — it is not a case the rewrite is answerable for.
    A point where only the CANDIDATE raises is a violation: the rewrite introduced the failure.

    n_evaluated is returned so the caller can refuse to call a zero-input check a pass."""
    names = names if names is not None else sorted(set(free_names(a)) | set(free_names(b)))
    ca, cb = compile(a, "<intended>", "eval"), compile(b, "<candidate>", "eval")
    n = 0
    for combo in itertools.product(grid, repeat=len(names)):
        env = dict(SAFE)
        env.update(dict(zip(names, combo)))
        try:
            va = eval(ca, env)
        except Exception:
            continue
        try:
            vb = eval(cb, env)
        except Exception as e:
            return False, f"{dict(zip(names, combo))} -> candidate raised {type(e).__name__}", n
        n += 1
        if va != vb:
            return False, f"{dict(zip(names, combo))} -> intended {va!r}, candidate {vb!r}", n
    return True, "", n


def nth_boolop_swapped(expr: str, n: int):
    """The expression with the n-th `and`/`or` in SOURCE-TOKEN order swapped at its AST node — what a
    textual flip of that token is trying to mean. Returns None if there is no such operator, and the
    string "AMB" when the operator belongs to a flattened chain.

    The operator must be found by its TOKEN column, not its node's: in `a and b or c` the Or node and the
    And node both start at column 0, so ordering by node column ties and silently matches the first
    textual `and` against the `or` node."""
    tree = ast.parse(expr, mode="eval")
    ops = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            for i in range(len(node.values) - 1):
                gap_start = node.values[i].end_col_offset
                gap = expr[gap_start:node.values[i + 1].col_offset]
                m = re.search(r"\b(and|or)\b", gap)
                ops.append((gap_start + (m.start() if m else 0), node))
    ops.sort(key=lambda t: t[0])
    if n >= len(ops):
        return None
    target = ops[n][1]
    if len(target.values) > 2:
        # Python flattens a homogeneous chain: `a or b or c` is one Or(3 values), not two nested nodes.
        # Swapping the node's op changes ALL of them, so "flip the n-th operator" has no node-level
        # meaning here. The rewrite is under-determined by the line — the honest ruling is AMB.
        return "AMB"
    target.op = ast.Or() if isinstance(target.op, ast.And) else ast.And()
    return ast.unparse(tree)
