#!/usr/bin/env python
"""Count the SINGLE-EDIT candidate space the body would enumerate.

Replicates the candidate enumeration in src/fluidfix/loop.py:repair()
EXACTLY -- same observer, same lanes.EMIT/ADVANCE walk over the kind mask,
same acts.candidates() call, same NOPROGRESS skip, same SpanEdit bounds and
anchor-safety checks, same `tried` dedup key -- but never writes a file and
never runs a suite. The number it returns is therefore the number of
candidates an EXHAUSTED single-edit search on that file would try, i.e. the
n that pair.py's cost paragraph is about.

Run: /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python count_candidates.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix.acts import KINDS, Observation, SpanEdit, act_for, candidates  # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402
from fluidfix.localize import Packet  # noqa: E402
from fluidfix.observers import MechanicalObserver  # noqa: E402


def enumerate_candidates(src_lines, anchor_lines, defect_file, root):
    """Return (n_total, n_compile_rejected, per_kind, n_obs, n_sets).

    n_total            distinct candidates the loop would put in `tried`
    n_compile_rejected of those, the ones loop.py rejects for free because
                       they do not compile (.py only)
    per_kind           {kind_name: count}
    """
    pk = Packet(defect_file=defect_file, failure="", lines=list(anchor_lines),
                src_lines=src_lines, mode="measured")
    observations = MechanicalObserver().observe([pk])[0]

    tried = set()
    per_kind = {}
    n_compile = 0
    n_sets = 0
    raw = src_lines
    for obs in observations:
        i = obs.lineno - 1
        if not (0 <= i < len(raw)):
            continue
        body = raw[i].rstrip("\r")
        mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
        while not HALT(mask):
            kind = kind_of(EMIT(mask))
            mask = ADVANCE(mask)
            act = act_for(kind)
            obs.file, obs.root = defect_file, root
            obs.all_lines = [l.rstrip("\r") for l in raw]
            counted = False
            for cand in candidates(body, act, obs):
                if isinstance(cand, SpanEdit):
                    s_, e_ = cand.start, cand.end
                    if not (1 <= s_ <= e_ <= len(raw)) \
                            or not (s_ <= obs.lineno <= e_):
                        continue
                    old_repr = "\n".join(l.rstrip("\r") for l in raw[s_ - 1:e_])
                    if cand.text == old_repr:            # NOPROGRESS
                        continue
                    key = (s_, e_, cand.text)
                    new = raw[:s_ - 1] + [cand.text] + raw[e_:]
                else:
                    if cand == body:                     # NOPROGRESS
                        continue
                    key = (i, cand)
                    new = raw[:]
                    new[i] = cand
                if key in tried:
                    continue
                tried.add(key)
                if not counted:
                    n_sets += 1
                    counted = True
                name = KINDS[kind][0]
                per_kind[name] = per_kind.get(name, 0) + 1
                if defect_file.endswith(".py"):
                    try:
                        compile("\n".join(new), defect_file, "exec")
                    except (SyntaxError, ValueError):
                        n_compile += 1
    return len(tried), n_compile, per_kind, len(observations), n_sets


def pairs(n):
    return n * (n - 1) // 2


def report(tag, src_lines, anchor_lines, defect_file, root, secs_per_cand=None):
    n, nc, pk, nobs, nsets = enumerate_candidates(
        src_lines, anchor_lines, defect_file, root)
    print(f"--- {tag}")
    print(f"    file                     : {defect_file}  "
          f"({len(src_lines)} lines)")
    print(f"    anchor lines in packet   : {len(anchor_lines)}")
    print(f"    observations (lines with a taught signal): {nobs}")
    print(f"    candidate SETS (line x kind, non-empty)  : {nsets}")
    print(f"    SINGLE-EDIT CANDIDATES n : {n}")
    if defect_file.endswith(".py"):
        print(f"      of which free (do not compile)         : {nc}")
        print(f"      paying a suite run                     : {n - nc}")
    print(f"    naive PAIR combinations C(n,2)           : {pairs(n)}")
    if secs_per_cand:
        s1 = n * secs_per_cand
        s2 = pairs(n) * secs_per_cand
        print(f"    at {secs_per_cand}s/candidate: single {s1:,.0f}s "
              f"({s1/3600:.2f} h)   pairs {s2:,.0f}s ({s2/86400:.2f} days)")
    top = sorted(pk.items(), key=lambda kv: -kv[1])
    print(f"    by fault class           : "
          + ", ".join(f"{k}={v}" for k, v in top))
    return n
