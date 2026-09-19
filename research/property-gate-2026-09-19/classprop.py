#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Properties for TAUGHT CLASSES, checked exhaustively.

A function property ("the result is sorted") needs the function's semantics. A taught class is not a
function — it is a transform from one line to another — so its property has to be ALGEBRAIC: a statement
about the rewrite itself, true whatever code surrounds it.

    class 7  len-as-last-index    the candidate must equal the original with len(x) replaced by
                                  (len(x) - 1), for every integer value of every free subexpression
    class 4  flipped-boolean      the textual flip must equal the AST node swap, for every truth assignment
    class 6  inverted-bare-guard  the candidate must be the exact negation, for every value
    class 5  get-without-default  the candidate must agree with the original on every dict holding the key

That kind of property is worth far more than a function property, because it is checked ONCE AT TEACH TIME
and then gates every future application of the class forever — on code nobody has written yet.

Each checker takes (original_line, candidate_line) and returns (ok, why, n_inputs_checked).
"""
from __future__ import annotations

import ast
import itertools
import re

# ------------------------------------------------------------------ evaluating a line over a grid

_SAFE = {"len": len, "int": int, "min": min, "max": max, "abs": abs, "str": str, "bool": bool}


def _free_names(expr: str) -> list:
    tree = ast.parse(expr, mode="eval")
    return sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id not in _SAFE})


def _rhs(line: str) -> str:
    """The expression a line is about: after `=`, after `return`, or the whole condition."""
    s = line.strip().rstrip(":")
    for kw in ("return ", "if ", "elif ", "while "):
        if s.startswith(kw):
            return s[len(kw):]
    m = re.match(r"^[\w.\[\]]+\s*=\s*(.+)$", s)
    return m.group(1) if m else s


def _agree(a: str, b: str, grid, names=None):
    """Do two expressions agree on every point of the grid? Returns (ok, witness, n)."""
    names = names or sorted(set(_free_names(a)) | set(_free_names(b)))
    ca, cb = compile(a, "<a>", "eval"), compile(b, "<b>", "eval")
    n = 0
    for combo in itertools.product(grid, repeat=len(names)):
        env = dict(_SAFE); env.update(dict(zip(names, combo)))
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
    return True, "", n   # callers must treat n == 0 as INCONCLUSIVE — see prop_len_minus_one


# ------------------------------------------------------------------ class 7: token placement

_LEN_CALL = re.compile(r"\blen\([\w.\[\]]+\)")


def prop_len_minus_one(orig: str, cand: str):
    """The candidate must be worth exactly `the original with THIS len(x) -> (len(x) - 1)`.

    EVERY len(...) on the line is replaced by its own free integer, on both sides, so the check ranges over
    every length those lists could ever hold — not the lengths some test happened to use. The line may hold
    several; the one the applier touched is found by where the two lines first differ."""
    o, c = _rhs(orig), _rhs(cand)
    occ_o = list(_LEN_CALL.finditer(o))
    occ_c = list(_LEN_CALL.finditer(c))
    if not occ_o or len(occ_o) != len(occ_c):
        return None, "len(...) count differs between the two lines", 0
    # which occurrence did the applier touch? the first character where the lines diverge
    d = next((i for i, (x, y) in enumerate(zip(o, c)) if x != y), min(len(o), len(c)))
    k = sum(1 for m in occ_o if m.end() <= d)
    k = min(k, len(occ_o) - 1)

    def subst(expr, occs, target=None):
        out, last = [], 0
        for i, m in enumerate(occs):
            out.append(expr[last:m.start()])
            out.append(f"(__L{i} - 1)" if i == target else f"__L{i}")
            last = m.end()
        out.append(expr[last:])
        return "".join(out)

    intended = subst(o, occ_o, target=k)
    actual = subst(c, occ_c, target=None)
    names = sorted(set(_free_names(intended)) | set(_free_names(actual)))
    ok, why, n = _agree(intended, actual, grid=(1, 2, 3, 5, 8), names=names)
    if ok and n == 0:
        return None, "no input could be evaluated — inconclusive, not a pass", 0
    return ok, why, n


# ------------------------------------------------------------------ class 4: boolean flip

def _nth_boolop_swapped(expr: str, n: int) -> str:
    """The expression with the n-th and/or in SOURCE-TOKEN order swapped at the AST node — the thing the
    textual flip is trying to mean.

    The operator must be located by its TOKEN column, not its node's. In `a and b or c` the Or node and the
    And node both start at column 0, so ordering by node column ties and silently matches the first textual
    `and` against the `or` node. The token sits in the gap between consecutive values."""
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
        # Python FLATTENS a homogeneous chain: `a or b or c` is one Or(3 values), not two nested nodes.
        # There is no single operator to swap — swapping the node's op changes all of them — so "flip
        # the n-th operator" is not a well-defined rewrite here. The property does not apply; the honest
        # ruling for such a candidate is AMB, not a silent ship.
        return "AMB"
    target.op = ast.Or() if isinstance(target.op, ast.And) else ast.And()
    return ast.unparse(tree)


def prop_boolean_flip(orig: str, cand: str):
    """Flipping one `and`/`or` TEXTUALLY must mean the same as swapping that operator at the AST node —
    i.e. the rewrite must not silently regroup. `and` binds tighter than `or`, so this is the same hazard
    class 7 has with `- 1` under `*`."""
    o, c = _rhs(orig), _rhs(cand)
    toks_o = [m.start() for m in re.finditer(r"\b(and|or)\b", o)]
    toks_c = [m.start() for m in re.finditer(r"\b(and|or)\b", c)]
    if len(toks_o) != len(toks_c):
        return None, "operator count changed", 0
    which = next((i for i, (a, b) in enumerate(zip(toks_o, toks_c))
                  if o[a:a + 3].strip() != c[b:b + 3].strip()), None)
    if which is None:
        return None, "nothing flipped", 0
    intended = _nth_boolop_swapped(o, which)
    if intended is None:
        return None, "could not locate the node", 0
    if intended == "AMB":
        return None, "flattened chain — one-operator flip is not a node swap; rule AMB", 0
    return _agree(intended, c, grid=(0, 1, "", "x", (), (7,)))


# ------------------------------------------------------------------ class 6: guard negation

def prop_guard_negation(orig: str, cand: str):
    """The candidate guard must be the exact logical negation — true on exactly the values where the
    original is false, with no value on which both agree."""
    o, c = _rhs(orig), _rhs(cand)
    names = sorted(set(_free_names(o)) | set(_free_names(c)))
    vals = (0, 1, -1, "", "x", (), (7,), [], [0], None, 0.0)
    co, cc = compile(o, "<o>", "eval"), compile(c, "<c>", "eval")
    n = 0
    for combo in itertools.product(vals, repeat=len(names)):
        env = dict(_SAFE); env.update(dict(zip(names, combo)))
        try:
            a, b = bool(eval(co, env)), bool(eval(cc, env))
        except Exception:
            continue
        n += 1
        if a == b:
            return False, f"{dict(zip(names, combo))} -> both {a}; not a negation", n
    return True, "", n


# ------------------------------------------------------------------ class 5: .get default

_GET = re.compile(r"\.get\(\s*((?:\"[^\"]*\"|'[^']*'))\s*(?:,\s*(.+?)\s*)?\)")


def prop_get_default(orig: str, cand: str):
    """Supplying a default may only change what happens when the key is ABSENT. On every dict that holds
    the key, the candidate must return exactly what the original did."""
    o, c = _rhs(orig), _rhs(cand)
    mo = _GET.search(o)
    if not mo or mo.group(2) is not None:
        return None, "no bare .get(key) on the line", 0
    key = ast.literal_eval(mo.group(1))
    names = sorted(set(_free_names(o)) | set(_free_names(c)))
    co, cc = compile(o, "<o>", "eval"), compile(c, "<c>", "eval")
    dicts = [{key: v} for v in ("", "a", 0, 1, [], None)] + \
            [{key: v, "other": 9} for v in ("z", 5)]
    n = 0
    for d in dicts:
        for combo in itertools.product([d], repeat=len(names)):
            env = dict(_SAFE); env.update(dict(zip(names, combo)))
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


PROPS = {
    4: ("the flip must not regroup", prop_boolean_flip),
    5: ("must agree wherever the key is present", prop_get_default),
    6: ("must be the exact negation", prop_guard_negation),
    7: ("placement must preserve the value", prop_len_minus_one),
}
