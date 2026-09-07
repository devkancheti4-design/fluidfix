#!/usr/bin/env python
"""Adversarial AMB fixtures for the engine law's AMB bit (target 04).

Six fixtures. Each is one Python module + one weak test file. For each we run
    (a) repair() directly, with the observation(s) the mechanical observer
        would produce for the named lines (our line order), while a wrapper
        around fluidfix.loop.decide logs every situation byte the body sends
        to the law;
    (b) guard_once() end-to-end with the MechanicalObserver (localise ->
        observe -> rank -> repair), i.e. the real body path;
and then, if anything shipped, a PINNING test that is NOT in the suite is
run against the shipped module to say whether the shipped program is the
intended one.

Nothing in src/ is edited. Run from anywhere:
    nice -n 15 timeout 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python amb_fixtures.py
Results are printed and written to results.json next to this script.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")

from fluidfix import MechanicalObserver, Oracle, guard_once, repair  # noqa: E402
from fluidfix.acts import KINDS, Observation  # noqa: E402
import fluidfix.loop as L  # noqa: E402
from fluidfix.engine import BITS, decide  # noqa: E402

# ---------------------------------------------------------------- fixtures --
# Each: name, mod.py source, test_mod.py source, lines to observe (in the
# order repair() receives them), the spec's expected ruling (from CHANGELOG
# v0.13/0.14 wording: AMB = two DIFFERENT PROGRAMS the suite cannot separate;
# two SPELLINGS of one program at one site are NOT AMB), and a pinning check
# run against whatever ships.
FIXTURES = [
    dict(
        name="F1-spelled-twice-one-site",
        why=("units > 10 (defect) vs correct units >= 10. Kind 0 gives "
             "`units >= 10`, kind 1 gives `units > 9`: ONE program spelled "
             "twice at one site, from two acts. Spec: NOT AMB -> SHIP."),
        mod=textwrap.dedent("""\
            def price(units):
                if units > 10:
                    return "bulk"
                return "unit"
            """),
        test=textwrap.dedent("""\
            from mod import price

            def test_price():
                assert price(10) == "bulk"
                assert price(9) == "unit"
                assert price(11) == "bulk"
            """),
        lines=[2],
        spec="SHIP",
        pin="from mod import price; assert price(10)=='bulk' and price(9)=='unit' and price(100)=='bulk'",
    ),
    dict(
        name="F2-two-programs-one-set",
        why=("a - b - c (defect) vs correct a + b - c; test net(1,2,2)==1 "
             "also admits a - b + c. Kind 3's ONE candidate set holds both "
             "greens: two DIFFERENT programs at one site. Spec: AMB -> "
             "ADD_STATE."),
        mod=textwrap.dedent("""\
            def net(a, b, c):
                return a - b - c
            """),
        test=textwrap.dedent("""\
            from mod import net

            def test_net():
                assert net(1, 2, 2) == 1
            """),
        lines=[2],
        spec="ADD_STATE",
        pin="from mod import net; assert net(5, 1, 2) == 4",
    ),
    dict(
        name="F3-two-programs-two-sites",
        why=("g: x + 2 (defect, correct x + 1); f: g(x) + 1 (correct). Test "
             "f(1)==3 is greened by fixing g (line 2) OR by breaking f to "
             "`g(x)` so the faults cancel (line 4). Two DIFFERENT programs "
             "at two sites. Spec: AMB -> ADD_STATE."),
        mod=textwrap.dedent("""\
            def g(x):
                return x + 2
            def f(x):
                return g(x) + 1
            """),
        test=textwrap.dedent("""\
            from mod import f

            def test_f():
                assert f(1) == 3
            """),
        lines=[2, 4],
        spec="ADD_STATE",
        pin="from mod import f, g; assert g(1) == 2 and f(1) == 3",
    ),
    dict(
        name="F4-two-programs-one-site-two-acts",
        why=("base - delta (defect) vs correct base + delta; test "
             "apply_delta(0,5)==5 also admits delta - base. Kind 2 "
             "(swap operands) -> `delta - base` GREEN (wrong program); "
             "kind 3 (flip additive) -> `base + delta` GREEN (right program). "
             "Two DIFFERENT programs at ONE site from TWO acts. Spec: AMB -> "
             "ADD_STATE. Measurement: set_amb=False, sites=1."),
        mod=textwrap.dedent("""\
            def apply_delta(base, delta):
                return base - delta

            def ident(x):
                return x
            """),
        test=textwrap.dedent("""\
            from mod import apply_delta, ident

            def test_apply_delta():
                assert apply_delta(0, 5) == 5

            def test_ident():
                assert ident(3) == 3
            """),
        lines=[2],
        spec="ADD_STATE",
        pin="from mod import apply_delta; assert apply_delta(10, 5) == 15",
    ),
    dict(
        name="F4b-two-programs-one-site-two-acts-swapped-roles",
        why=("Same line and same weak test as F4, but now the INTENDED "
             "program is delta - base (kind 2's candidate). Shows which of "
             "the two greens ships is decided by kind NUMBER (EMIT = lowest "
             "bit), not by evidence."),
        mod=textwrap.dedent("""\
            def apply_delta(base, delta):
                return base - delta

            def ident(x):
                return x
            """),
        test=textwrap.dedent("""\
            from mod import apply_delta, ident

            def test_apply_delta():
                assert apply_delta(0, 5) == 5

            def test_ident():
                assert ident(3) == 3
            """),
        lines=[2],
        spec="ADD_STATE",
        pin="from mod import apply_delta; assert apply_delta(10, 5) == -5",
    ),
    dict(
        name="F4c-F4-plus-one-pinning-test",
        why=("F4 with the ONE pinning test ADD_STATE would ask for "
             "(apply_delta(10, 5) == 15) added to the suite. Measures what "
             "the law's ruling, had AMB been measured, would have bought."),
        mod=textwrap.dedent("""\
            def apply_delta(base, delta):
                return base - delta

            def ident(x):
                return x
            """),
        test=textwrap.dedent("""\
            from mod import apply_delta, ident

            def test_apply_delta():
                assert apply_delta(0, 5) == 5

            def test_apply_delta_pin():
                assert apply_delta(10, 5) == 15

            def test_ident():
                assert ident(3) == 3
            """),
        lines=[2],
        spec="SHIP",
        pin="from mod import apply_delta; assert apply_delta(10, 5) == 15 and apply_delta(-3, 7) == 4",
    ),
    dict(
        name="F5-one-program-twice-in-one-set",
        why=("(n + 1) * (n + 1) // 2 (defect) vs correct n * (n + 1) // 2. "
             "Kind 1's ONE candidate set yields `(n) * (n + 1) // 2` and "
             "`(n + 1) * (n) // 2`: ONE program (commutative product) "
             "spelled twice, inside one set. Spec: NOT AMB -> SHIP. "
             "Measurement: set_amb=True."),
        mod=textwrap.dedent("""\
            def tri(n):
                return (n + 1) * (n + 1) // 2
            """),
        test=textwrap.dedent("""\
            from mod import tri

            def test_tri():
                assert tri(1) == 1
                assert tri(3) == 6
                assert tri(4) == 10
            """),
        lines=[2],
        spec="SHIP",
        pin="from mod import tri; assert tri(10) == 55 and tri(0) == 0",
    ),
    dict(
        name="F6-one-program-two-sites",
        why=("LIMIT = 10 (line 1); return units > LIMIT (line 3, defect; "
             "correct >=). Kind 0 at line 3 -> `>=` GREEN; kind 1 at line 1 "
             "-> `LIMIT = 9` GREEN. Extensionally ONE program (LIMIT has one "
             "use), but at TWO sites. Spec (CHANGELOG): greens at two lines "
             "= two claims about WHERE = AMB -> ADD_STATE."),
        mod=textwrap.dedent("""\
            LIMIT = 10
            def bulk(units):
                return units > LIMIT
            """),
        test=textwrap.dedent("""\
            from mod import bulk

            def test_bulk():
                assert bulk(10) is True
                assert bulk(9) is False
                assert bulk(11) is True
            """),
        lines=[3, 1],
        spec="ADD_STATE",
        pin="from mod import bulk, LIMIT; assert LIMIT == 10 and bulk(10) is True",
    ),
]


def kinds_for(line: str) -> list[int]:
    """Exactly MechanicalObserver's per-line rule."""
    return [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(line)]


def bits_of(sit: int) -> str:
    return "+".join(b for i, b in enumerate(BITS) if sit >> i & 1) or "-"


def fresh_dir(fx: dict, tag: str) -> str:
    d = os.path.join(HERE, "runs", f"{fx['name']}-{tag}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    with open(os.path.join(d, "mod.py"), "w") as fh:
        fh.write(fx["mod"])
    with open(os.path.join(d, "test_mod.py"), "w") as fh:
        fh.write(fx["test"])
    return d


def pin_check(d: str, pin: str) -> str:
    p = subprocess.run([sys.executable, "-c", pin], cwd=d,
                       capture_output=True, text=True, timeout=60)
    return "PASS" if p.returncode == 0 else "FAIL"


def run_direct(fx: dict) -> dict:
    d = fresh_dir(fx, "direct")
    log: list[int] = []
    orig = L.decide

    def spy(sit):
        log.append(sit)
        return orig(sit)

    L.decide = spy
    try:
        oracle = Oracle(d, python=sys.executable)
        src_lines = fx["mod"].split("\n")
        obs = [Observation(lineno=l, kinds=kinds_for(src_lines[l - 1]))
               for l in fx["lines"]]
        res = repair(oracle, "mod.py", obs)
    finally:
        L.decide = orig
    out = dict(
        mode="direct",
        observations=[(o.lineno, o.kinds) for o in obs],
        repaired=res.repaired, ambiguous=res.ambiguous,
        lineno=res.lineno,
        shipped=(res.new_line or "").strip() or None,
        greens=[g.strip() for g in res.greens],
        suite_runs=res.suite_runs, acts_tried=res.acts_tried,
        reason=res.reason,
        situations=[f"0x{s:03x}={bits_of(s)}->{orig(s)}" for s in log],
        final_mod=open(os.path.join(d, "mod.py")).read(),
    )
    out["pin"] = pin_check(d, fx["pin"]) if res.repaired else "n/a (refused)"
    return out


def run_guard(fx: dict) -> dict:
    d = fresh_dir(fx, "guard")
    log: list[int] = []
    orig = L.decide

    def spy(sit):
        log.append(sit)
        return orig(sit)

    L.decide = spy
    try:
        oracle = Oracle(d, python=sys.executable)
        rep = guard_once(oracle, MechanicalObserver(), escalate=False)
    finally:
        L.decide = orig
    res = rep.result
    out = dict(
        mode="guard",
        status=rep.status, file=rep.file,
        repaired=bool(res and res.repaired),
        ambiguous=bool(res and res.ambiguous),
        lineno=res.lineno if res else None,
        shipped=((res.new_line or "").strip() or None) if res else None,
        greens=[g.strip() for g in res.greens] if res else [],
        suite_runs=res.suite_runs if res else None,
        reason=(res.reason if res else rep.hint),
        hint=rep.hint,
        situations=[f"0x{s:03x}={bits_of(s)}->{orig(s)}" for s in log],
        final_mod=open(os.path.join(d, "mod.py")).read(),
    )
    out["pin"] = pin_check(d, fx["pin"]) if out["repaired"] else "n/a (refused)"
    return out


def main() -> None:
    only = set(sys.argv[1:])
    results = []
    for fx in FIXTURES:
        if only and fx["name"] not in only and fx["name"].split("-")[0] not in only:
            continue
        print("=" * 78)
        print(fx["name"])
        print(textwrap.fill(fx["why"], 78, initial_indent="  ", subsequent_indent="  "))
        print(f"  spec ruling: {fx['spec']}")
        row = dict(name=fx["name"], spec=fx["spec"], why=fx["why"])
        for runner in (run_direct, run_guard):
            r = runner(fx)
            row[r["mode"]] = r
            got = "SHIP" if r["repaired"] else ("ADD_STATE" if r["ambiguous"] else "OTHER")
            r["measured_ruling"] = got
            r["matches_spec"] = (got == fx["spec"])
            print(f"  [{r['mode']}] ruling={got} matches_spec={r['matches_spec']} "
                  f"pin={r['pin']} suite_runs={r['suite_runs']}")
            if r["mode"] == "direct":
                print(f"    observations: {r['observations']}")
            else:
                print(f"    guard status: {r['status']} file={r['file']}")
            print(f"    greens ({len(r['greens'])}): {r['greens']}")
            print(f"    shipped: {r['shipped']!r} at line {r['lineno']}")
            print(f"    law consulted with: {r['situations']}")
            print("    reason: " + textwrap.shorten(r["reason"] or "", 300))
        results.append(row)
    # merge into results.json by fixture name (a filtered rerun must not
    # clobber the rows it did not touch); keep FIXTURES order
    path = os.path.join(HERE, "results.json")
    prior = {}
    if os.path.exists(path):
        with open(path) as fh:
            prior = {r["name"]: r for r in json.load(fh)}
    prior.update({r["name"]: r for r in results})
    results = [prior[f["name"]] for f in FIXTURES if f["name"] in prior]
    with open(path, "w") as fh:
        json.dump(results, fh, indent=1)
    print("=" * 78)
    print(f"{'fixture':48} {'spec':10} {'direct':10} {'guard':10} pin(direct/guard)")
    for row in results:
        print(f"{row['name']:48} {row['spec']:10} "
              f"{row['direct']['measured_ruling']:10} "
              f"{row['guard']['measured_ruling']:10} "
              f"{row['direct']['pin']}/{row['guard']['pin']}")


if __name__ == "__main__":
    main()
