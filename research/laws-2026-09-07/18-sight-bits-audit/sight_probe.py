#!/usr/bin/env python
"""Record every observation byte the BODY hands to the SIGHT law.

Usage:  .venv/bin/python sight_probe.py <fixture_root> [limit]

Nothing in src/ is edited. `fluidfix.sight.sight` is replaced, for the
duration of one find_candidate_files() call, by a recorder that reads the
caller frame (guard.file_priority2) for `rel`, `specificity`, `n_fail`, logs
the byte, then returns the real law's ruling. The ranking the body produces
is therefore exactly what it would have produced unobserved.

Also printed, as DIAGNOSTICS (a re-computation, not the body's own state):
  - the lines of the failing output the FRAMED / LITERAL / NAMED regexes read
  - per taught-signal hit counts over the candidate bodies (SCARCE's input)
"""
import os
import re
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fluidfix.sight as sight_mod                      # noqa: E402
from fluidfix.guard import find_candidate_files          # noqa: E402
from fluidfix.oracle import Oracle                       # noqa: E402
from fluidfix.sight import BITS                          # noqa: E402

REAL = sight_mod.sight
LOG: list = []


def recorder(obs):
    f = sys._getframe(1)
    loc = f.f_locals
    LOG.append((loc.get("rel"), obs, loc.get("specificity"), loc.get("n_fail")))
    return REAL(obs)


def names(obs):
    return "|".join(b for i, b in enumerate(BITS) if obs >> i & 1) or "-"


def main():
    root = os.path.abspath(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    oracle = Oracle(root, python=sys.executable)
    fails, out = oracle.failing_output()
    assert fails, "fixture is green; nothing to localise"
    clean = re.sub(r"\x1b\[[0-9;]*m", "", out)

    print("== failing output lines the ranker's regexes read ==")
    for line in clean.splitlines():
        if (re.search(r"([\w./\\-]+\.py)[\":,]", line)
                or re.match(r"^E?\s*(?:assert|AssertionError)", line)
                or re.match(r"^(?:FAILED|ERROR)\s", line)):
            print("   ", line.rstrip()[:140])

    ev: dict = {}
    sight_mod.sight = recorder
    try:
        order = find_candidate_files(oracle, out, limit=limit, evidence=ev)
    finally:
        sight_mod.sight = REAL

    print(f"\n== sight() calls: {len(LOG)}  (0 means the law was never consulted) ==")
    print(f"{'file':28} {'byte':>4}  {'prio':>4}  {'spec':>5} {'n_fail':>6}  bits")
    for rel, obs, spec, nf in sorted(LOG, key=lambda t: (REAL(t[1]), t[0] or "")):
        print(f"{rel:28} {obs:4d}  {REAL(obs):4d}  {spec:5.2f} {nf:6d}  {names(obs)}")
    print("\n== order returned by find_candidate_files ==")
    for i, rel in enumerate(order, 1):
        print(f"   {i}. {rel}")
    print("\n== evidence dict ==")
    print("   pointed:", ev.get("pointed"))
    for k, v in (ev.get("lanes") or {}).items():
        print(f"   lanes[{k}]: {v}")

    # ---- diagnostics: SCARCE's input, recomputed the way guard.py does it
    from fluidfix.acts import KINDS
    cands = sorted({t[0] for t in LOG if t[0]})
    bodies = {}
    for rel in cands:
        try:
            bodies[rel] = open(os.path.join(root, rel), encoding="utf-8",
                               errors="replace").read()
        except OSError:
            pass
    print("\n== per-signal hits over candidate bodies (SCARCE fires on 1..2) ==")
    for kind, (name, _d, sig) in KINDS.items():
        if sig is None:
            continue
        hits = [rel for rel, b in bodies.items() if sig.search(b)]
        flag = "  <- SCARCE" if 0 < len(hits) <= 2 else ""
        print(f"   kind {kind:2d} {name:28} {sig.pattern!r:45} {len(hits)} {hits}{flag}")


if __name__ == "__main__":
    main()
