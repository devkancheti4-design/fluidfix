"""31-cross-rank-sight, probe 2: DOES THE ORDER CHANGE THE OUTCOME?

Reads the body's own two orderings out of a real localisation pass (no src
edits: the law functions are wrapped and the caller's frame is read for the
values it is ranking), then enumerates the candidate sequence the search
would try under four orderings and reports at which suite run the CORRECT
candidate is reached.

    shipped      file order (SIGHT or traceback) OUTER, line order (RANK) INNER
    rank-first   line order (RANK) OUTER across all files, SIGHT breaks ties
    no-sight     files in alphabetical order, RANK still orders lines
    no-rank      SIGHT file order, lines in source order
    sight-doc    shipped, but with the tie-break sight.py's docstring claims
                 (specificity then executed-line count, no affinity)

Usage: python counterfactual.py <fixture> <workdir>
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

import fixtures  # noqa: E402

# (file, lineno, the exact repaired line text) for each fixture
CORRECT = {
    "F1-single-assert": ("mod.py", 4, "        if x > t:"),
    "F2-single-traceback": ("mod.py", 2, "    return a + b"),
    "F3-multi-assert": ("mod.py", 4, "        if x > t:"),
    "F4-multi-traceback": ("mod.py", 2, "    return a + b"),
    "F5-named-misdirection": ("mod.py", 4, "        if x > t:"),
    "F6-order-sensitive": ("mod.py", 4, "        if x > t:"),
}

FILE_INFO = {}     # rel -> dict(prio, byte, affinity, specificity, n_fail)
LINE_INFO = {}     # (rel, lineno) -> dict(prio, byte)
_CUR_REL = [None]


def install():
    import fluidfix.rank as R
    import fluidfix.sight as S

    _sight, _rank = S.sight, R.rank

    def sight(obs):
        p = _sight(obs)
        f = sys._getframe(1).f_locals          # file_priority2's frame
        rel = f.get("rel")
        if rel is not None:
            FILE_INFO[rel] = dict(prio=p, byte=obs,
                                  specificity=f.get("specificity"),
                                  n_fail=f.get("n_fail"),
                                  bits=[b for i, b in enumerate(S.BITS)
                                        if obs >> i & 1])
        return p
    S.sight = sight

    def rank(obs):
        p = _rank(obs)
        ln = sys._getframe(1).f_locals.get("ln")   # priority()'s frame
        if ln is not None and _CUR_REL[0]:
            LINE_INFO[(_CUR_REL[0], ln)] = dict(
                prio=p, byte=obs,
                bits=[b for i, b in enumerate(R.BITS) if obs >> i & 1])
        return p
    R.rank = rank


def enumerate_runs(oracle, order, packets, correct):
    """Count suite runs the search would pay, in `order`, until the correct
    candidate. Replicates loop.repair()'s free rejections exactly:
    NOPROGRESS (cand == body), duplicates within a file, and .py candidates
    that do not compile are rejected without a suite run."""
    from fluidfix.acts import act_for, candidates
    from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of
    cf, cl, ctext = correct
    runs = 0
    tried_by_file = {}
    trace = []
    for rel, obs in order:
        raw = packets[rel]["raw"]
        tried = tried_by_file.setdefault(rel, set())
        i = obs.lineno - 1
        if not (0 <= i < len(raw)):
            continue
        body = raw[i].rstrip("\r")
        mask = mask_of(k for k in (obs.kinds or []) if 0 <= k <= 15)
        while not HALT(mask):
            kind = kind_of(EMIT(mask))
            mask = ADVANCE(mask)
            obs.file, obs.root = rel, oracle.root
            obs.all_lines = [l.rstrip("\r") for l in raw]
            for cand in candidates(body, act_for(kind), obs):
                if not isinstance(cand, str):
                    continue                      # SpanEdit: not in these fixtures
                if cand == body:
                    continue
                key = (i, cand)
                if key in tried:
                    continue
                tried.add(key)
                new = raw[:]
                new[i] = cand
                if rel.endswith(".py"):
                    try:
                        compile("\n".join(new), rel, "exec")
                    except SyntaxError:
                        continue
                runs += 1
                trace.append((runs, rel, obs.lineno, kind, cand.strip()[:40]))
                if rel == cf and obs.lineno == cl and cand == ctext:
                    return runs, trace
    return None, trace


def main():
    name, work = sys.argv[1], sys.argv[2]
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    fixtures.ALL[name](work)
    install()

    from fluidfix import MechanicalObserver, Oracle
    from fluidfix.guard import find_candidate_files, rank_observations
    from fluidfix.localize import build_packet

    oracle = Oracle(work, python=sys.executable)
    fails, out = oracle.failing_output()
    ev = {}
    shipped_files = find_candidate_files(oracle, out, limit=999, evidence=ev)
    route = "SIGHT-law" if FILE_INFO else "traceback-early-return"

    observer = MechanicalObserver()
    packets, line_order = {}, {}
    for rel in shipped_files:
        p = build_packet(oracle, rel)
        if p is None:
            continue
        raw = open(os.path.join(work, rel), encoding="utf-8",
                   newline="").read().split("\n")
        packets[rel] = {"raw": raw, "packet": p}
        _CUR_REL[0] = rel
        obs = observer.observe([p])[0]
        line_order[rel] = rank_observations("\n".join(p.src_lines), obs, out,
                                            root=work, rel=rel)
        _CUR_REL[0] = None

    files = [f for f in shipped_files if f in packets]

    def lp(rel, o):
        return LINE_INFO.get((rel, o.lineno), {}).get("prio", 7)

    def fp(rel):
        return FILE_INFO.get(rel, {}).get("prio", 0)

    orders = {}
    orders["shipped"] = [(rel, o) for rel in files for o in line_order[rel]]
    # rank-first: the LINE law outer, SIGHT only breaking its ties
    flat = [(rel, o) for rel in files for o in line_order[rel]]
    orders["rank-first"] = sorted(
        flat, key=lambda t: (lp(t[0], t[1]), fp(t[0]), files.index(t[0]),
                             line_order[t[0]].index(t[1])))
    orders["no-sight"] = [(rel, o) for rel in sorted(files)
                          for o in line_order[rel]]
    orders["no-rank"] = [(rel, o) for rel in files
                         for o in sorted(line_order[rel],
                                         key=lambda o: o.lineno)]
    if FILE_INFO:
        doc = sorted(files, key=lambda r: (
            FILE_INFO[r]["prio"], -(FILE_INFO[r]["specificity"] or 0),
            -(FILE_INFO[r]["n_fail"] or 0), r))
        orders["sight-doc-tiebreak"] = [(rel, o) for rel in doc
                                        for o in line_order[rel]]

    result = {"fixture": name, "route": route, "correct": CORRECT[name],
              "shipped_file_order": files, "evidence": ev,
              "file_info": FILE_INFO,
              "line_order": {r: [o.lineno for o in line_order[r]]
                             for r in files},
              "line_info": {f"{k[0]}:{k[1]}": v for k, v in LINE_INFO.items()},
              "runs_to_correct": {}, "traces": {}}
    for k, order in orders.items():
        n, trace = enumerate_runs(oracle, order, packets, CORRECT[name])
        result["runs_to_correct"][k] = n
        result["traces"][k] = trace[:40]
    print(json.dumps(result, indent=1, default=str))


if __name__ == "__main__":
    main()
