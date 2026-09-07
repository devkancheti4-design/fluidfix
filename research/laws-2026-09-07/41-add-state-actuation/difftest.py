#!/usr/bin/env python
"""ADD_STATE, actuated: generate a PINNING TEST from two green candidates.

The engine law rules ADD_STATE on BUILT+AMB (byte 0x203): two different
programs both pass the suite, so refuse and ask for ONE pinning test. Today
that ruling is WORDING ONLY -- `ADD_STATE` is interpolated into the refusal
message at loop.py:237 and nothing is produced. This module prototypes the
missing ACTUATION, outside src/, and is a pure function of what the loop
already holds in memory at loop.py:217:

    greens: list[(crepr, content, old_repr, at)]

i.e. for every suite-passing candidate, the FULL FILE CONTENT it produces.

Method (differential testing, seeded from the repo's own suite):

  1. find the function enclosing the disputed line, in each variant
  2. harvest CONCRETE call arguments from the repo's tests (ast literals) --
     the suite is the only source of in-domain inputs fluidfix has
  3. mutate each seed ONE ARGUMENT AT A TIME (+-1, +-2, 0, negate, double;
     for sequences: reverse, swap, drop, extend, elementwise +-1; for floats
     +-0.5) -- one-at-a-time keeps the witness readable
  4. evaluate every candidate variant on the whole pool, in its own
     subprocess, each input twice; an input whose own two runs disagree is
     UNSTABLE and discarded (a flaky witness would pin nothing)
  5. the first input on which two variants disagree is the WITNESS
  6. emit a pytest file the user drops in: the call, and one commented
     assertion per candidate with that candidate's value

No ground truth is used anywhere in steps 1-6. The user picks the line.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import subprocess
import sys

PY = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python"
POOL_CAP = 400
CALL_ALARM = 2          # seconds per call, inside the driver
# Runs per input; an input whose own runs disagree is UNSTABLE and cannot pin
# anything. 2 is not enough: on a random-valued function 11 of 20 generations
# still emitted a witness (l4_sweep.py). 5 emitted 0 of 20.
REPEATS = 5


# ----------------------------------------------------------------- step 1 --
def enclosing_function(src: str, lineno: int):
    """The innermost FunctionDef containing `lineno`, or None."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None) or lineno
            if node.lineno <= lineno <= end:
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


def param_names(fn) -> list[str]:
    a = fn.args
    return [p.arg for p in (list(a.posonlyargs) + list(a.args))]


# ----------------------------------------------------------------- step 2 --
def harvest_seeds(root: str, fname: str, arity: int) -> list[list]:
    """Concrete argument tuples for `fname` found as literals in the repo's
    own test files. The suite is the only in-domain input source we have."""
    seeds, seen = [], set()
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".venv", "__pycache__",
                                    ".fluidfix", ".pytest_cache")]
        for f in files:
            if not f.endswith(".py"):
                continue
            if not (f.startswith("test_") or f.endswith("_test.py")
                    or "test" in dirpath.split(os.sep)):
                continue
            try:
                tree = ast.parse(open(os.path.join(dirpath, f),
                                      encoding="utf-8").read())
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                nm = (fn.id if isinstance(fn, ast.Name)
                      else fn.attr if isinstance(fn, ast.Attribute) else None)
                if nm != fname or node.keywords or len(node.args) != arity:
                    continue
                try:
                    args = [ast.literal_eval(a) for a in node.args]
                except (ValueError, SyntaxError, TypeError):
                    continue
                k = repr(args)
                if k not in seen:
                    seen.add(k)
                    seeds.append(args)
    return seeds


# ----------------------------------------------------------------- step 3 --
def _mutations(v):
    out = []
    if isinstance(v, bool):
        out += [not v]
    elif isinstance(v, int):
        out += [v + 1, v - 1, v + 2, v - 2, 0, -v, v * 2]
    elif isinstance(v, float):
        out += [v + 0.5, v - 0.5, v + 1.0, v - 1.0, 0.0, -v]
    elif isinstance(v, str):
        out += ["", v + "x", v[::-1], v.upper()]
    elif isinstance(v, (list, tuple)):
        L = list(v)
        c = []
        if len(L) >= 2:
            c += [L[::-1], [L[1], L[0]] + L[2:], L[1:], L[:-1]]
        c += [L + [0], []]
        for i in range(min(len(L), 4)):
            if isinstance(L[i], (int, float)) and not isinstance(L[i], bool):
                for d in (1, -1, 2):
                    M = list(L)
                    M[i] = M[i] + d
                    c.append(M)
        out += [tuple(x) for x in c] if isinstance(v, tuple) else c
    elif v is None:
        out += [0, ""]
    return out


DEFAULT_ATOMS = [0, 1, 2, -1, 5, 0.5, "", "a", [], [0], [1, 2], [2, 1],
                 [1, 2, 3], True, False, None]


def build_pool(seeds: list[list], arity: int) -> list[list]:
    pool, seen = [], set()

    def add(a):
        k = repr(a)
        if k not in seen and len(pool) < POOL_CAP:
            seen.add(k)
            pool.append(a)

    for s in seeds:
        add(list(s))
    for s in seeds:                       # ONE argument at a time
        for i in range(arity):
            for m in _mutations(s[i]):
                a = list(s)
                a[i] = m
                add(a)
    # MIDPOINTS between the values the suite itself uses at each position.
    # +-1/+-2 is local; a threshold that moved far (`> 20` vs `> 120`) has a
    # disagreement region no local mutation reaches, but a bisection of the
    # suite's own range does. Measured: recovers case L2 (limits.py).
    for i in range(arity):
        vals = sorted({s[i] for s in seeds
                       if isinstance(s[i], (int, float))
                       and not isinstance(s[i], bool)})
        for lo, hi in zip(vals, vals[1:]):
            for s in seeds:
                a = list(s)
                a[i] = type(lo)((lo + hi) / 2) if isinstance(lo, int) \
                    else (lo + hi) / 2.0
                add(a)
    if not seeds:                         # no suite seeds: type-blind fallback
        import itertools
        for combo in itertools.product(DEFAULT_ATOMS, repeat=min(arity, 3)):
            add(list(combo) + [0] * (arity - len(combo)))
    return pool


# ----------------------------------------------------------------- step 4 --
_DRIVER = r'''
import copy, json, signal, sys, traceback
sys.path.insert(0, ".")
def _to(sig, frm): raise TimeoutError("call exceeded %d s" % {alarm})
try:
    signal.signal(signal.SIGALRM, _to)
except Exception:
    pass
out = []
try:
    import {mod} as M
    f = getattr(M, {fname!r})
except BaseException as e:
    print("@@FLUIDFIX@@" + json.dumps({{"import_error":
                                        type(e).__name__ + ": " + str(e)[:120]}}))
    sys.exit(0)
CALLS = json.loads({calls!r})
for args in CALLS:
    def once():
        return repr(f(*copy.deepcopy(args)))
    try:
        signal.alarm({alarm})
        rs = [once() for _ in range({repeats})]
        signal.alarm(0)
        out.append(rs[0] if len(set(rs)) == 1 else "!UNSTABLE")
    except BaseException as e:
        try:
            signal.alarm(0)
        except Exception:
            pass
        out.append("!" + type(e).__name__ + ": " + str(e)[:60])
print("@@FLUIDFIX@@" + json.dumps({{"values": out}}))
'''


def evaluate(probe_dir: str, relpath: str, variant_src: str, mod: str,
             fname: str, pool: list[list], timeout: int = 120):
    """Run one variant over the whole pool in its own subprocess."""
    with open(os.path.join(probe_dir, relpath), "w", encoding="utf-8",
              newline="") as f:
        f.write(variant_src)
    drv = _DRIVER.format(mod=mod, fname=fname, calls=json.dumps(pool),
                         alarm=CALL_ALARM, repeats=REPEATS)
    dp = os.path.join(probe_dir, "_fluidfix_probe.py")
    with open(dp, "w", encoding="utf-8") as f:
        f.write(drv)
    p = subprocess.run(["nice", "-n", "15", PY, "-B", "_fluidfix_probe.py"],
                       cwd=probe_dir, capture_output=True, text=True,
                       timeout=timeout)
    for line in p.stdout.splitlines():
        if line.startswith("@@FLUIDFIX@@"):
            return json.loads(line[len("@@FLUIDFIX@@"):])
    return {"driver_error": (p.stdout + p.stderr)[-300:]}


# ------------------------------------------------------------- steps 5, 6 --
def most_called(root: str) -> list[tuple[str, int]]:
    """Functions the repo's own tests call, most-called first. The suite's
    entry points -- the right place to pin when the candidates edit
    DIFFERENT functions (the compensating-fault shape, loop.py:208-212)."""
    counts: dict[str, int] = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".venv", "__pycache__",
                                    ".fluidfix", ".pytest_cache")]
        for f in files:
            if not (f.endswith(".py") and (f.startswith("test_")
                                           or f.endswith("_test.py"))):
                continue
            try:
                tree = ast.parse(open(os.path.join(dirpath, f),
                                      encoding="utf-8").read())
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func,
                                                             ast.Name):
                    counts[node.func.id] = counts.get(node.func.id, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def find_function(src: str, name: str):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name == name:
            return node
    return None


def differentiate(root: str, relpath: str, lineno: int,
                  cand_lines: list[str], workdir: str) -> dict:
    """Given >=2 suite-passing candidates, find a call they disagree on and
    emit a pinning test.

    `cand_lines` is either a list of replacement LINES (all at `lineno`) or a
    list of (lineno, line) pairs -- greens at DIFFERENT sites. The loop holds
    exactly this at loop.py:217 as `greens[i][0]` and `greens[i][3]`.

    Returns a dict; `separated` is True iff a stable witness exists."""
    edits = [(lineno, c) if isinstance(c, str) else tuple(c)
             for c in cand_lines]
    rec = {"file": relpath, "lineno": lineno,
           "candidates": [c for _, c in edits],
           "sites": sorted({ln for ln, _ in edits})}
    with open(os.path.join(root, relpath), encoding="utf-8",
              newline="") as f:
        base = f.read()
    raw = base.split("\n")
    variants = []
    for ln, c in edits:
        new = raw[:]
        new[ln - 1] = c + raw[ln - 1][len(raw[ln - 1].rstrip("\r")):]
        variants.append("\n".join(new))

    # WHICH function to pin. Every function some candidate edits, plus the
    # suite's own entry points. First one that separates wins.
    targets: list[str] = []
    for v, (ln, _) in zip(variants, edits):
        fn = enclosing_function(v, ln)
        if fn is not None and fn.name not in targets:
            targets.append(fn.name)
    for nm, _n in most_called(root):
        if nm not in targets and find_function(variants[0], nm) is not None:
            targets.append(nm)
    rec["targets_tried"] = targets
    if not targets:
        rec["separated"] = False
        rec["failed"] = ("no enclosing function at the disputed line and no "
                         "test-called function in this file (non-Python "
                         "source parses to nothing)")
        return rec

    probe = os.path.join(workdir, "_probe")
    shutil.rmtree(probe, ignore_errors=True)
    shutil.copytree(root, probe, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".fluidfix", ".pytest_cache"))
    mod = relpath[:-3].replace(os.sep, ".")
    attempts = []
    try:
        for tname in targets:
            fn = find_function(variants[0], tname)
            if fn is None:
                continue
            params = param_names(fn)
            seeds = harvest_seeds(root, tname, len(params))
            pool = build_pool(seeds, len(params))
            att = {"function": tname, "params": params, "n_seeds": len(seeds),
                   "n_pool": len(pool)}
            if not pool:
                att["failed"] = "empty input pool"
                attempts.append(att)
                continue
            cols = []
            for v in variants:
                r = evaluate(probe, relpath, v, mod, tname, pool)
                if "values" not in r:
                    att["failed"] = f"could not evaluate: {r}"
                    break
                cols.append(r["values"])
            if len(cols) != len(variants):
                attempts.append(att)
                continue
            att["n_unstable"] = sum(1 for i in range(len(pool))
                                    if any(c[i] == "!UNSTABLE" for c in cols))
            att["n_error"] = sum(1 for i in range(len(pool))
                                 if any(c[i].startswith("!") for c in cols))
            witness = None
            for i in range(len(pool)):
                vals = [c[i] for c in cols]
                if any(v.startswith("!") for v in vals):
                    continue   # unstable or raising: not a clean pin
                if len(set(vals)) > 1:
                    witness = i
                    break
            att["n_separating"] = sum(
                1 for i in range(len(pool))
                if not any(c[i].startswith("!") for c in cols)
                and len({c[i] for c in cols}) > 1)
            if witness is None:
                att["failed"] = (f"no stable, exception-free input of "
                                 f"{len(pool)} separates the candidates")
                attempts.append(att)
                continue
            call = f"{tname}({', '.join(repr(a) for a in pool[witness])})"
            att.update(witness_call=call,
                       witness_values=[c[witness] for c in cols])
            attempts.append(att)
            rec.update(attempts=attempts, separated=True, function=tname,
                       n_seeds=att["n_seeds"], n_pool=att["n_pool"],
                       n_unstable=att["n_unstable"],
                       n_separating=att["n_separating"],
                       witness_call=call, witness_values=att["witness_values"],
                       test_text=render_test(relpath, rec["sites"],
                                             [c for _, c in edits], mod,
                                             tname, call,
                                             att["witness_values"]))
            return rec
    finally:
        shutil.rmtree(probe, ignore_errors=True)

    rec["attempts"] = attempts
    rec["separated"] = False
    rec["failed"] = ("no witness on any of " + ", ".join(targets) + ": "
                     + "; ".join(a.get("failed", "?") for a in attempts))
    return rec


def render_test(relpath, sites, cand_lines, mod, fname, call, values) -> str:
    lab = [chr(ord("A") + i) for i in range(len(cand_lines))]
    where = (f"{relpath}:{sites[0]}" if not isinstance(sites, list)
             else f"{relpath}:{','.join(map(str, sites))}")
    head = [
        '"""Pinning test proposed by fluidfix.',
        "",
        f"The engine law ruled BUILT+AMB -> ADD_STATE at {where}:",
        f"{len(cand_lines)} DIFFERENT programs all pass this suite, so the",
        "suite cannot say which one you meant. They disagree here:",
        "",
    ]
    for L, c, v in zip(lab, cand_lines, values):
        head.append(f"    {L}:  {c.strip()}")
        head.append(f"         {call}  ->  {v}")
    head += [
        "",
        "Uncomment the ONE assertion that states what your program should do,",
        "delete the others, and re-run fluidfix. Every candidate but yours",
        "will then be red, and the ambiguity is gone.",
        '"""',
        f"from {mod} import {fname}",
        "",
        "",
        f"def test_fluidfix_pin_{fname}():",
    ]
    body = [f"    # assert {call} == {v}    # candidate {L}"
            for L, v in zip(lab, values)]
    return "\n".join(head + body) + "\n"


def pinned(test_text: str, which: int) -> str:
    """Uncomment assertion `which` -- what the USER does by hand. Used by the
    harness to measure whether the test actually separates."""
    out, seen = [], 0
    for line in test_text.split("\n"):
        s = line.strip()
        if s.startswith("# assert "):
            if seen == which:
                line = line.replace("# assert ", "assert ", 1)
            seen += 1
        out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    root, rel, ln = sys.argv[1], sys.argv[2], int(sys.argv[3])
    print(json.dumps(differentiate(root, rel, ln, sys.argv[4:],
                                   os.path.dirname(os.path.abspath(__file__))),
                     indent=1))
