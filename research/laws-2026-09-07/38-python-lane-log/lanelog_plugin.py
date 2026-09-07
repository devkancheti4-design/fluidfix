# Read-only instrumentation for agent 38 (38-python-lane-log).
# Loaded with `pytest -p lanelog_plugin`. Patches nothing in src/ on disk:
# it rebinds the law entry points in the already-imported fluidfix modules
# so every law consultation the BODY makes is logged with its call site.
#
# Output: one JSON object per line to $LANELOG (default lanelog.jsonl).
import json
import os
import sys
import traceback

LOG = open(os.environ.get("LANELOG", "lanelog.jsonl"), "a", buffering=1)
_CUR = {"test": "<import-time>"}


def _emit(rec):
    rec["test"] = _CUR["test"]
    LOG.write(json.dumps(rec, default=str) + "\n")


def _site(depth=2):
    """filename:lineno of the BODY frame that consulted the law."""
    st = traceback.extract_stack()
    # st[-1] is _site, st[-2] is the wrapper, st[-3] is the caller
    fr = st[-(depth + 1)]
    return "%s:%d" % (os.path.basename(fr.filename), fr.lineno)


def _bits(byte, names):
    return [n for i, n in enumerate(names) if byte >> i & 1]


def install():
    import fluidfix
    from fluidfix import acts, engine, guard, lanes, localize, loop, rank, router, sight

    # ---- engine law -------------------------------------------------------
    _decide = engine.decide

    def decide(sit):
        out = _decide(sit)
        low = sit & 0xFF
        _emit({"law": "engine", "site": _site(), "sit": sit, "byte": low,
               "bits": _bits(low, engine.BITS), "ruling": out})
        return out
    engine.decide = decide
    loop.decide = decide            # loop.py binds it at module import

    # ---- SIGHT law --------------------------------------------------------
    _sight = sight.sight

    def sight_f(obs):
        out = _sight(obs)
        _emit({"law": "sight", "site": _site(), "byte": obs,
               "bits": _bits(obs, sight.BITS), "ruling": out})
        return out
    sight.sight = sight_f

    # ---- ranking law ------------------------------------------------------
    _rank = rank.rank

    def rank_f(obs):
        out = _rank(obs)
        _emit({"law": "rank", "site": _site(), "byte": obs,
               "bits": _bits(obs, rank.BITS), "ruling": out})
        return out
    rank.rank = rank_f

    # ---- fluid-router -----------------------------------------------------
    _route = router.route

    def route_f(F1, A1, Fq):
        out = _route(F1, A1, Fq)
        _emit({"law": "router", "site": _site(), "byte": [F1, A1, Fq],
               "bits": [], "ruling": out})
        return out
    router.route = route_f
    acts.route = route_f            # acts.py binds it at module import

    # ---- lanes ------------------------------------------------------------
    for nm in ("EMIT", "ADVANCE", "HALT"):
        orig = getattr(lanes, nm)

        def mk(nm=nm, orig=orig):
            def f(m):
                out = orig(m)
                _emit({"law": "lanes." + nm, "site": _site(), "byte": m,
                       "bits": [], "ruling": out})
                return out
            return f
        f = mk()
        setattr(lanes, nm, f)
        setattr(loop, nm, f)        # loop.py binds them at module import

    # ---- guard / repair boundaries (fixture identity + outcome) -----------
    _guard_once = guard.guard_once

    def guard_once(oracle, observer, *a, **kw):
        files = _snapshot(oracle.root)
        _emit({"law": "-", "event": "guard_once:enter", "root": oracle.root,
               "files": files})
        try:
            rep = _guard_once(oracle, observer, *a, **kw)
        except BaseException as e:                              # noqa: BLE001
            _emit({"law": "-", "event": "guard_once:raise",
                   "root": oracle.root, "exc": repr(e)})
            raise
        _emit({"law": "-", "event": "guard_once:exit", "root": oracle.root,
               "status": rep.status, "file": rep.file,
               "candidates": rep.candidates, "seconds": rep.seconds,
               "hint": (rep.hint or "")[:400],
               "reason": (getattr(rep.result, "reason", "") or "")[:400]})
        return rep
    guard.guard_once = guard_once
    fluidfix.guard_once = guard_once

    _repair = loop.repair

    def repair(oracle, rel, observations, *a, **kw):
        _emit({"law": "-", "event": "repair:enter", "root": oracle.root,
               "file": rel, "n_obs": len(observations or [])})
        res = _repair(oracle, rel, observations, *a, **kw)
        _emit({"law": "-", "event": "repair:exit", "root": oracle.root,
               "file": rel, "repaired": bool(res.repaired),
               "ambiguous": bool(getattr(res, "ambiguous", False)),
               "acts_tried": list(getattr(res, "acts_tried", []) or []),
               "reason": (res.reason or "")[:400]})
        return res
    loop.repair = repair
    fluidfix.repair = repair
    guard.repair = repair


def _snapshot(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", ".fluidfix")]
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            try:
                if os.path.getsize(p) < 20000:
                    out[rel] = open(p, "rb").read().decode("utf-8", "replace")
            except OSError:
                pass
        if len(out) > 40:
            break
    return out


# ---------------------------------------------------------------- pytest ---
def pytest_configure(config):
    install()
    _emit({"law": "-", "event": "installed", "python": sys.version.split()[0]})


def pytest_runtest_logstart(nodeid, location):
    _CUR["test"] = nodeid


def pytest_runtest_logreport(report):
    if report.when == "call":
        _emit({"law": "-", "event": "test:outcome", "outcome": report.outcome})
