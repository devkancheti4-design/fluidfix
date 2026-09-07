#!/usr/bin/env python
"""Instrument the RANKING law's observation byte WITHOUT editing src/.

Wraps fluidfix.rank.observe_bits (every byte the body builds) and
fluidfix.guard.rank_observations (every call, and which kwargs the body
passed) then runs the guard-driving tests in-process with pytest.main so the
wrappers see every byte the body ever hands the law.

Usage (from anywhere):
  nice -n 15 timeout 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
      log_rank_bits.py [tests...]
Writes rank_bits_log.json and rank_bits_summary.txt next to this script.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FF = "/Users/kanchetidevieswar/neo/fluidfix"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import fluidfix.rank as R      # noqa: E402
import fluidfix.guard as G     # noqa: E402

BYTES: list[dict] = []
CALLS: list[dict] = []
_DEPTH = [0]     # >0 while inside guard.rank_observations (the BODY's call)

_orig_obs = R.observe_bits


def _obs_logged(**kw):
    b = {k: bool(v) for k, v in kw.items()}
    b["_in_body"] = _DEPTH[0] > 0
    BYTES.append(b)
    return _orig_obs(**{k: v for k, v in kw.items()})


R.observe_bits = _obs_logged

_orig_ro = G.rank_observations


def _ro_logged(src, observations, failing_output, *, root=None, rel=None,
               retried=None):
    n0 = len(BYTES)
    _DEPTH[0] += 1
    try:
        out = _orig_ro(src, observations, failing_output, root=root, rel=rel,
                       retried=retried)
    finally:
        _DEPTH[0] -= 1
    CALLS.append({
        "n_obs": len(observations),
        "root_passed": root is not None,
        "rel": rel,
        "retried_passed": retried is not None,
        "retried_len": len(retried) if retried else 0,
        "output_has_File_line": bool(re.search(r'File "[^"]+\.py", line \d+',
                                                failing_output)),
        "output_has_path_colon_line": bool(re.search(r"\.py:\d+", failing_output)),
        "output_has_FAILED": bool(re.search(r"^(?:FAILED|ERROR)\s", failing_output,
                                            re.M)),
        "bytes_logged": len(BYTES) - n0,
        "kinds_empty": sum(1 for o in observations if not o.kinds),
    })
    return out


G.rank_observations = _ro_logged


def _flush(rc="running"):
    """Write the log after every call so a capped run still yields data."""
    with open(os.path.join(HERE, "rank_bits_log.json"), "w") as f:
        json.dump({"rc": rc, "calls": CALLS, "bytes": BYTES,
                   "repairs": globals().get("REPAIRS", [])}, f, indent=1)


_ro_inner = _ro_logged


def _ro_flushing(*a, **kw):
    out = _ro_inner(*a, **kw)
    _flush()
    return out


G.rank_observations = _ro_flushing

# Wrap guard.repair too: every candidate trial (rel, at, text) per repair()
# call, so trials repeated across passes on the same file — the situation
# the RETRIED veto exists for — can be counted afterwards.
REPAIRS: list[dict] = []
_orig_repair = G.repair


def _repair_logged(oracle, rel, observations, **kw):
    res = _orig_repair(oracle, rel, observations, **kw)
    REPAIRS.append({
        "root": getattr(oracle, "root", None), "rel": rel,
        "n_obs": len(observations),
        "obs_lines": [o.lineno for o in observations],
        "repaired": bool(getattr(res, "repaired", False)),
        "trials": [(t.get("at"), t.get("tried")) for t in
                   (getattr(res, "tried_log", None) or [])],
    })
    _flush()
    return res


G.repair = _repair_logged

# self-interrupt before the outer 300 s cap so the summary is still written
import signal  # noqa: E402

BUDGET_S = int(os.environ.get("RANK_LOG_BUDGET_S", "270"))


def _alarm(signum, frame):
    raise KeyboardInterrupt(f"rank-log budget {BUDGET_S}s reached")


signal.signal(signal.SIGALRM, _alarm)
signal.alarm(BUDGET_S)

import pytest  # noqa: E402

DEFAULT_TESTS = [
    "tests/test_guard.py", "tests/test_engine_fusion.py",
    "tests/test_span_edits.py", "tests/test_teaching.py",
    "tests/test_context_transforms.py", "tests/test_dictionary.py",
    "tests/test_demo_walkthrough.py", "tests/test_regressions.py",
    "tests/test_refusal_diagnosis.py", "tests/test_dry_run.py",
    "tests/test_rank_law.py",
]
tests = sys.argv[1:] or DEFAULT_TESTS
os.chdir(FF)
rc = pytest.main(["-q", "-p", "no:cacheprovider", "--tb=line",
                  "-o", f"cache_dir={HERE}/.pytest_cache", *tests])

bits = R.BITS


def _kw(b):
    return {k: v for k, v in b.items() if not k.startswith("_")}


lines = [f"pytest rc={rc}  tests={tests}",
         f"rank_observations calls={len(CALLS)}  bytes={len(BYTES)} "
         f"(in-body {sum(b['_in_body'] for b in BYTES)}, "
         f"direct-from-tests {sum(not b['_in_body'] for b in BYTES)})"]
for label, sel in (("BODY-BUILT bytes (inside guard.rank_observations)",
                    [b for b in BYTES if b["_in_body"]]),
                   ("ALL bytes incl. tests calling observe_bits directly",
                    BYTES)):
    per_bit = collections.Counter()
    prio = collections.Counter()
    for b in sel:
        for k, v in _kw(b).items():
            if v:
                per_bit[k.upper()] += 1
        prio[R.rank(_orig_obs(**_kw(b)))] += 1
    combos = collections.Counter(
        "+".join(k.upper() for k, v in _kw(b).items() if v) or "(none)"
        for b in sel)
    lines += ["", f"--- {label}: n={len(sel)}",
              "per-bit set count:"]
    for name in bits:
        lines.append(f"  {name:9s} {per_bit.get(name, 0):5d} / {len(sel)}")
    lines += ["priority histogram (rank() output):"]
    for p in range(8):
        lines.append(f"  p={p} {prio.get(p, 0):5d}")
    lines += ["byte combinations seen:"]
    for c, n in combos.most_common():
        lines.append(f"  {n:5d}  {c}")
lines += ["", "call-site facts:",
          f"  calls with retried= passed by the body: "
          f"{sum(c['retried_passed'] for c in CALLS)} / {len(CALLS)}",
          f"  calls with root= passed:                "
          f"{sum(c['root_passed'] for c in CALLS)} / {len(CALLS)}",
          f"  calls whose failing_output had 'File \"x.py\", line N': "
          f"{sum(c['output_has_File_line'] for c in CALLS)} / {len(CALLS)}",
          f"  calls whose failing_output had 'x.py:N': "
          f"{sum(c['output_has_path_colon_line'] for c in CALLS)} / {len(CALLS)}",
          f"  calls whose failing_output had FAILED/ERROR lines: "
          f"{sum(c['output_has_FAILED'] for c in CALLS)} / {len(CALLS)}",
          f"  observations with empty kinds handed to the law: "
          f"{sum(c['kinds_empty'] for c in CALLS)}"]
# --- re-tried trials: same (root, rel, at, text) in more than one repair()
# call of the same guarded repo = a candidate re-run after rejection, which
# the RETRIED veto exists to demote and the body never asks for.
seen: dict = {}
dups = 0
dup_examples = []
for i, r in enumerate(REPAIRS):
    for at, txt in r["trials"]:
        key = (r["root"], r["rel"], at, txt)
        if key in seen and seen[key] != i:
            dups += 1
            if len(dup_examples) < 5:
                dup_examples.append((r["rel"], at, (txt or "")[:60]))
        seen.setdefault(key, i)
total_trials = sum(len(r["trials"]) for r in REPAIRS)
multi = collections.Counter((r["root"], r["rel"]) for r in REPAIRS)
lines += ["", "repair() calls (guard.repair wrapper):",
          f"  calls={len(REPAIRS)}  files repaired-more-than-once="
          f"{sum(1 for v in multi.values() if v > 1)}",
          f"  candidate trials logged={total_trials} "
          f"(tried_log caps at 64 per repair)",
          f"  trials REPEATED on the same (repo, file, line, candidate) in a "
          f"later repair() call: {dups}"]
for ex in dup_examples:
    lines.append(f"    e.g. {ex}")
summary = "\n".join(lines)
print("\n" + summary)
with open(os.path.join(HERE, "rank_bits_summary.txt"), "w") as f:
    f.write(summary + "\n")
_flush(rc)
