"""Instrumentation shim: record every candidate the search actually tries,
with a timestamp, WITHOUT editing src/. Import and call install() first.

One row per suite run that judges a candidate:
  t      seconds since install()
  phase  "pass0" | "escalation" (flipped when the engine law rules
         RAISE_BUDGET inside guard_once)
  rel    the file repair() is working on
  line   first line number that differs from the pristine file (the
         candidate's site) — 0 when nothing differs
  sha    sha1 of the WHOLE mutated file (identical sha == the identical
         program was re-tested == repeated work)
  dur    seconds the suite run took
  ok     did the suite go green

Also logs every engine-law consultation (patching fluidfix.engine.decide,
which is what guard.py imports per call) and every repair() call.
"""
import hashlib
import json
import time

ROWS = []
LAWLOG = []
REPAIRS = []
STATE = {"t0": None, "phase": "pass0", "last": None, "rel": None,
         "pristine": None}


def _first_diff(pristine, content):
    if pristine is None:
        return -1
    a, b = pristine.split("\n"), content.split("\n")
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i + 1
    return 0 if len(a) == len(b) else min(len(a), len(b)) + 1


def install():
    from fluidfix import loop as L
    from fluidfix import oracle as O
    from fluidfix import engine as E
    from fluidfix import guard as G
    STATE["t0"] = time.time()

    _w = L._write
    def w(path, content):
        STATE["last"] = (path, content)
        return _w(path, content)
    L._write = w

    def _log(a, b, ok):
        p, content = STATE["last"] or ("?", "")
        ROWS.append({"t": round(a - STATE["t0"], 3), "phase": STATE["phase"],
                     "rel": STATE["rel"], "file": p.rsplit("/", 1)[-1],
                     "line": _first_diff(STATE["pristine"], content),
                     "sha": hashlib.sha1(content.encode()).hexdigest()[:12],
                     "dur": round(b - a, 3), "ok": bool(ok)})

    _c = O.Oracle.check
    def c(self, timeout=None):
        a = time.time(); r = _c(self, timeout=timeout); _log(a, time.time(), r[0])
        return r
    O.Oracle.check = c
    try:
        from fluidfix import coracle as C
        _cc = C.COracle.check
        def cc(self, timeout=None):
            a = time.time(); r = _cc(self, timeout=timeout)
            _log(a, time.time(), r[0]); return r
        C.COracle.check = cc
    except Exception:                                        # noqa: BLE001
        pass

    _d = E.decide
    def d(sit):
        r = _d(sit)
        bits = [b for i, b in enumerate(E.BITS) if sit >> i & 1]
        LAWLOG.append({"t": round(time.time() - STATE["t0"], 3),
                       "sit": sit, "bits": bits, "act": r,
                       "phase": STATE["phase"]})
        if r == "RAISE_BUDGET" and "CAPPED" in bits:
            STATE["phase"] = "escalation"
        return r
    E.decide = d
    G.decide = d

    _r = L.repair
    def rp(oracle, rel, observations, **kw):
        import os
        STATE["rel"] = rel
        try:
            STATE["pristine"] = open(os.path.join(oracle.root, rel),
                                     encoding="utf-8", newline="").read()
        except Exception:                                    # noqa: BLE001
            STATE["pristine"] = None
        n0, a = len(ROWS), time.time()
        res = _r(oracle, rel, observations, **kw)
        REPAIRS.append({"phase": STATE["phase"], "rel": rel,
                        "t_start": round(a - STATE["t0"], 3),
                        "t_end": round(time.time() - STATE["t0"], 3),
                        "deadline_in": (round(kw["deadline"] - a, 1)
                                        if kw.get("deadline") else None),
                        "n_obs": len(observations),
                        "obs_lines": [o.lineno for o in observations][:2000],
                        "runs_logged": len(ROWS) - n0,
                        "suite_runs": res.suite_runs,
                        "repaired": res.repaired,
                        "reason": (res.reason or "")[:300],
                        "tried_log": len(res.tried_log),
                        "tried_more": res.tried_more})
        STATE["rel"] = None; STATE["pristine"] = None
        return res
    L.repair = rp
    G.repair = rp


def dump(path):
    json.dump({"rows": ROWS, "law": LAWLOG, "repairs": REPAIRS},
              open(path, "w"), indent=1)
