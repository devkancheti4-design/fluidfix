#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Candidate patches for one broken function, in six classes — five of them adversarial.

Nothing here is hand-tuned per case. Given the broken implementation, a correct one written elsewhere, and
the suite's own asserts, every class is generated mechanically, so the certifier faces the same shapes on
every case:

  true         a correct implementation written by ANOTHER author (here: a model), structurally unlike
               anything fluidfix's vocabulary could produce
  wrong        a DIFFERENT model's failing implementation of the same specification — a real bad patch
  overfit      a lookup table keyed on the exact inputs the tests use. Green for the wrong reason
  flaky        correct, but raises on half its calls: a green that will not repeat
  collateral   correct on the test that was RED, broken on a test that was already GREEN
  outside-near correct, but disagreeing with `true` one step away from a value the suite mentions
  outside-far  correct, but disagreeing with `true` far from anything the suite mentions
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from fluidfix import differ                                            # noqa: E402

PY = sys.executable


def fn_name_arity(code: str) -> tuple[str, int]:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node.name, len(node.args.args)
    raise ValueError("no function")


def call_args(assert_src: str, name: str) -> list | None:
    """The literal arguments this assert passes to `name`, or None when they are not literals."""
    try:
        tree = ast.parse(assert_src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            try:
                return [ast.literal_eval(a) for a in node.args]
            except (ValueError, SyntaxError, TypeError):
                return None
    return None


def outputs(code: str, name: str, pool: list[list], timeout: int = 20):
    """Run one implementation over a pool of inputs, out of process. None marks a raise."""
    drv = (code + "\n\nimport json as _j\n_out=[]\n"
           f"for _a in _j.loads({json.dumps(json.dumps(pool))}):\n"
           f"    try: _out.append({name}(*_a))\n"
           "    except Exception: _out.append(None)\n"
           "print('@@'+_j.dumps(_out, default=str))\n")
    try:
        p = subprocess.run([PY, "-c", drv], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    for l in p.stdout.splitlines():
        if l.startswith("@@"):
            return json.loads(l[2:])
    return None


def _shim(correct: str, name: str, body: str) -> str:
    return (correct.rstrip("\n") + "\n\n"
            f"_ff_inner = {name}\n\n\n"
            f"def {name}(*a, **k):\n{body}\n")


def make(root: Path, broken: str, correct: str, asserts: list[str], red_idx: set[int],
         other_broken: str | None) -> dict:
    """Every class this case can supply. A class that cannot be built for this case is simply absent."""
    name, arity = fn_name_arity(correct)
    out = {"true": correct}
    if other_broken:
        out["wrong"] = other_broken

    seeds = differ.harvest_seeds(str(root), name, arity)

    # ---- overfit: green on exactly the inputs the suite mentions, undefined everywhere else
    if seeds:
        vals = outputs(correct, name, seeds)
        if vals is not None:
            table = {repr(tuple(s)): v for s, v in zip(seeds, vals)}
            out["overfit"] = ("_FF = {\n" + "".join(f"    {k!r}: {v!r},\n" for k, v in table.items()) + "}\n\n\n"
                              f"def {name}(*a):\n    return _FF[repr(tuple(a))]\n")

    # ---- flaky: correct, but a green that does not repeat
    out["flaky"] = ("import random as _ffr\n" + _shim(
        correct, name, "    if _ffr.random() < 0.5:\n"
                       "        raise RuntimeError('intermittent')\n"
                       "    return _ff_inner(*a, **k)"))

    # ---- collateral: repairs the red test, breaks one that was already green
    green = [i for i in range(len(asserts)) if i not in red_idx]
    for i in green:
        args = call_args(asserts[i], name)
        if args is None:
            continue
        got = outputs(correct, name, [args])
        if not got or got[0] is None or got[0] == 0:
            continue
        out["collateral"] = _shim(correct, name,
                                  f"    if list(a) == {args!r}:\n"
                                  "        return None\n"
                                  "    return _ff_inner(*a, **k)")
        out["collateral_breaks"] = f"test_{i}"
        break

    # ---- outside: correct on everything the suite can see, different beyond it
    if seeds:
        near = far = None
        flat = [s for s in seeds if any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in s)]
        if flat:
            s = flat[0]
            j = next(k for k, v in enumerate(s) if isinstance(v, (int, float)) and not isinstance(v, bool))
            n_args = list(s); n_args[j] = s[j] + 1
            f_args = list(s); f_args[j] = s[j] + 9973
            if n_args not in seeds:
                near = n_args
            if f_args not in seeds:
                far = f_args
        for tag, args in (("outside-near", near), ("outside-far", far)):
            if args is None:
                continue
            out[tag] = _shim(correct, name,
                             f"    if list(a) == {args!r}:\n"
                             "        return '**different**'\n"
                             "    return _ff_inner(*a, **k)")
            out[tag + "_at"] = args
    return out
