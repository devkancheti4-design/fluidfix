"""31-cross-rank-sight, probe 1: WHICH LAW IS CONSULTED FIRST.

Wraps (never edits) the body's entry points and logs a single global event
sequence for one guard_once pass:

    SIGHT   one call of sight.sight()  -> file priority
    FILEORD the file list find_candidate_files() returned, and by which route
    RANK    one call of rank.rank()    -> line priority
    KIND    one lanes EMIT inside loop.repair() -> which class is tried next
    RUN     one suite run

Usage:  python order_probe.py <fixture-name> <workdir>
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fixtures  # noqa: E402

EVENTS = []
_SEQ = [0]


def _ev(kind, **kw):
    _SEQ[0] += 1
    EVENTS.append(dict(seq=_SEQ[0], kind=kind, **kw))


def install(root):
    import fluidfix.guard as G
    import fluidfix.lanes as L
    import fluidfix.loop as LP
    import fluidfix.rank as R
    import fluidfix.sight as S
    import fluidfix.oracle as O

    # --- sight.sight (guard.py imports it INSIDE find_candidate_files) ----
    _sight = S.sight

    def sight(obs):
        p = _sight(obs)
        _ev("SIGHT", byte=obs, prio=p,
            bits=[b for i, b in enumerate(S.BITS) if obs >> i & 1])
        return p
    S.sight = sight

    # --- rank.rank (guard.py imports it INSIDE rank_observations) ---------
    _rank = R.rank

    def rank(obs):
        p = _rank(obs)
        _ev("RANK", byte=obs, prio=p,
            bits=[b for i, b in enumerate(R.BITS) if obs >> i & 1])
        return p
    R.rank = rank

    # --- find_candidate_files: record the ROUTE it returned by ------------
    _fcf = G.find_candidate_files

    def fcf(oracle, failing_output, limit=3, evidence=None):
        n_before = sum(e["kind"] == "SIGHT" for e in EVENTS)
        out = _fcf(oracle, failing_output, limit, evidence)
        n_after = sum(e["kind"] == "SIGHT" for e in EVENTS)
        _ev("FILEORD", files=list(out), limit=limit,
            sight_calls=n_after - n_before,
            route=("traceback-early-return" if n_after == n_before
                   else "SIGHT-law"))
        return out
    G.find_candidate_files = fcf

    # --- rank_observations: record the line order it produced -------------
    _ro = G.rank_observations

    def ro(src, observations, failing_output, **kw):
        out = _ro(src, observations, failing_output, **kw)
        _ev("LINEORD", rel=kw.get("rel"),
            lines=[o.lineno for o in out],
            kinds=[list(o.kinds or []) for o in out])
        return out
    G.rank_observations = ro

    # --- lanes EMIT as used by loop.repair() (module-level import) --------
    _emit = LP.EMIT

    def emit(m):
        e = _emit(m)
        _ev("KIND", mask=m, klass=(e.bit_length() - 1) if e else None)
        return e
    LP.EMIT = emit

    # --- suite runs -------------------------------------------------------
    _check = O.Oracle.check

    def check(self, *a, **kw):
        r = _check(self, *a, **kw)
        _ev("RUN", ok=bool(r[0]))
        return r
    O.Oracle.check = check


def main():
    name, work = sys.argv[1], sys.argv[2]
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    defect_file, defect_line = fixtures.ALL[name](work)

    install(work)
    from fluidfix import MechanicalObserver, Oracle, guard_once
    oracle = Oracle(work, python=sys.executable)
    t0 = time.time()
    rep = guard_once(oracle, MechanicalObserver(), budget=180)
    out = {
        "fixture": name, "root": work,
        "defect": f"{defect_file}:{defect_line}",
        "status": rep.status, "file": rep.file,
        "candidates": rep.candidates,
        "evidence": rep.evidence,
        "seconds": round(time.time() - t0, 2),
        "suite_runs": sum(e["kind"] == "RUN" for e in EVENTS),
        "first_law_consulted": next(
            (e["kind"] for e in EVENTS if e["kind"] in ("SIGHT", "RANK")),
            None),
        "events": EVENTS,
    }
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
