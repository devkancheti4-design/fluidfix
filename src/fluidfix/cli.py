# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""fluidfix — suite-adjudicated repair of mechanical defects: a branchless
kernel picks the act, the target's own test suite judges every candidate."""
from __future__ import annotations

import argparse
import json
import os
import sys


def _version() -> str:
    """The version of the CODE that is running.

    Prefers the package attribute over installed metadata: an editable
    install keeps the metadata recorded at `pip install -e` time, so after a
    version bump `importlib.metadata` reports the OLD number while the code
    on disk is new — the same silent-staleness trap as `pip install` not
    upgrading."""
    try:
        from . import __version__
        return __version__
    except Exception:                                       # noqa: BLE001
        pass
    try:
        import importlib.metadata as _md
        return _md.version("fluidfix")
    except Exception:                                       # noqa: BLE001
        return "unknown"


def _python_arg(value: str) -> str:
    # resolve a relative --python against the INVOKING cwd at parse time —
    # the oracle runs subprocesses with cwd=root, which silently re-anchored
    # relative paths there. Bare names keep their PATH lookup.
    return os.path.abspath(value) if os.sep in value else value


def _python_works(python: str) -> bool:
    import subprocess
    try:
        return subprocess.run([python, "-c", "pass"], capture_output=True,
                              timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _oracle(args):
    from .oracle import Oracle
    return Oracle(args.root, python=args.python,
                  timeout=args.suite_timeout,
                  per_test_timeout=args.test_timeout)


def cmd_repair(args) -> int:
    from .localize import build_packet
    from .loop import repair
    _load_dictionary(args)
    oracle = _oracle(args)
    packet = build_packet(oracle, args.file, coverage_target=args.cov)
    if packet is None:
        print("suite is green — nothing to repair (refusing to search)")
        return 3
    if args.observer == "claude":
        from .observers import ClaudeObserver
        obs = ClaudeObserver(model=args.model)
        observations = obs.observe([packet])[0]
        if obs.last_usage is not None:
            u = obs.last_usage
            print(f"observer usage: in={u.input_tokens} out={u.output_tokens}",
                  file=sys.stderr)
    else:
        from .observers import MechanicalObserver
        observations = MechanicalObserver().observe([packet])[0]
    result = repair(oracle, args.file, observations,
                    candidate_timeout=args.candidate_timeout)
    if args.json:
        print(json.dumps(result.__dict__, default=str, indent=1))
    else:
        print(result.summary())
    return 0 if result.repaired else 2


def _load_dictionary(args):
    if getattr(args, "dictionary", None):
        from .acts import load_dictionary
        n = load_dictionary(args.dictionary)
        print(f"dictionary {args.dictionary}: {n} fault class(es) registered")


def _observer(args):
    if args.observer == "claude":
        from .observers import ClaudeObserver
        return ClaudeObserver(model=args.model)
    from .observers import MechanicalObserver
    return MechanicalObserver()


def cmd_guard(args) -> int:
    import os as _os
    import time as _time
    if getattr(args, "max_candidates", None):
        _os.environ["FLUIDFIX_CANDIDATE_CAP"] = str(args.max_candidates)
    from .guard import commit_repair, guard_once, propose_repair, write_refusal
    _load_dictionary(args)
    oracle = _oracle(args)
    observer = _observer(args)
    while True:
        report = guard_once(oracle, observer, coverage_target=args.cov,
                            candidate_timeout=args.candidate_timeout,
                            escalate_budget=args.escalate_budget,
                            budget=args.budget)
        print(f"[{_time.strftime('%H:%M:%S')}] {report.summary()}")
        if report.status == "repaired" and args.dry_run:
            # propose-only channel: patch written, tree restored byte-exactly.
            # Returns even under --interval — re-looping would grind out the
            # same proposal every pass until someone applies it.
            _, diff = propose_repair(oracle.root, report)
            print(diff, end="" if diff.endswith("\n") else "\n")
            print("PROPOSED (dry-run): apply with git apply .fluidfix/proposed.patch")
            return 0
        if report.status == "repaired" and args.commit:
            outcome = commit_repair(oracle.root, report)
            print({"committed": "  committed",
                   "clean": "  tree already matches last commit — nothing to commit",
                   "failed": "  commit failed — repair left in working tree"}[outcome])
        if report.status == "refused":
            print(f"  refusal report: {write_refusal(oracle.root, report)}")
        if args.interval is None:
            return 0 if report.status in ("green", "repaired") else 2
        _time.sleep(args.interval)


def cmd_packet(args) -> int:
    from .localize import build_packet
    packet = build_packet(_oracle(args), args.file, coverage_target=args.cov)
    if packet is None:
        print("suite is green — no packet")
        return 3
    print(packet.render())
    return 0


def cmd_init(args) -> int:
    """Zero-tests on-ramp: generate a starter guard suite for a repo.

    Finds every importable module, probes each in a subprocess, and writes
    test_fluidfix_smoke.py covering the ones that import cleanly today —
    guarding the repo against import-breaking regressions with no testing
    knowledge required. Value-level guarding still needs real asserts; the
    generated file says exactly how (the paste trick)."""
    import subprocess
    root = os.path.abspath(args.root)
    python = args.python or sys.executable
    out_path = os.path.join(root, "test_fluidfix_smoke.py")
    if os.path.exists(out_path) and not args.force:
        print("test_fluidfix_smoke.py already exists — re-run with --force to regenerate")
        return 1

    skip_dirs = {".git", "__pycache__", "tests", "test", "venv", ".venv",
                 "env", ".tox", "build", "dist", "node_modules", ".fluidfix"}
    mods = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in skip_dirs and not d.startswith(".")
                       and not d.endswith(".egg-info")]
        rel = os.path.relpath(dirpath, root)
        parts = [] if rel == "." else rel.split(os.sep)
        if parts and not all((os.path.exists(os.path.join(root, *parts[:i + 1],
                                                          "__init__.py")))
                             for i in range(len(parts))):
            continue                      # only walk real packages
        for f in filenames:
            if (not f.endswith(".py") or f.startswith("test_")
                    or f.endswith("_test.py")
                    or f in ("setup.py", "conftest.py", "test_fluidfix_smoke.py")):
                continue
            name = ".".join(parts + [f[:-3]]) if f != "__init__.py" else ".".join(parts)
            if name:
                mods.append(name)
    good, skipped = [], []
    for m in sorted(set(mods)):
        try:
            ok = subprocess.run(
                [python, "-c", f"import {m}"], cwd=root, capture_output=True,
                timeout=15).returncode == 0
        except subprocess.TimeoutExpired:
            ok = False
        (good if ok else skipped).append(m)
    if not good:
        print("no importable modules found — nothing to guard yet "
              "(are you in the project root?)")
        return 1
    mod_lines = "\n".join(f'    "{m}",' for m in good)
    open(out_path, "w", encoding="utf-8").write(f'''\
# test_fluidfix_smoke.py — generated by `fluidfix init`
# Guards every module below against import-breaking regressions: syntax
# errors, bad renames, crashes in module-level code. Safe to commit.
#
# LEVEL UP (2 minutes): import smoke can't see a wrong *value*. For each
# function you care about, add one real assert using the paste trick —
# run it once, freeze today's answer:
#
#   def test_my_function():
#       assert my_function(example_input) == <paste what it printed today>
#
# Full guide: https://github.com/devkancheti4-design/fluidfix/blob/master/docs/QUICKSTART.md
import importlib

import pytest

MODULES = [
{mod_lines}
]


@pytest.mark.parametrize("mod", MODULES)
def test_module_imports(mod):
    importlib.import_module(mod)
''')
    print(f"wrote test_fluidfix_smoke.py guarding {len(good)} module(s)")
    for m in skipped:
        print(f"  skipped (does not import cleanly today): {m}")
    print("next: fluidfix guard . --commit")
    return 0


def cmd_jguard(args) -> int:
    import time as _time
    from .guard import commit_repair, write_refusal
    from .javaoracle import JavaOracle, jguard_once
    from .observers import MechanicalObserver
    _load_dictionary(args)
    oracle = JavaOracle(args.root, mvn=args.mvn, timeout=args.suite_timeout)
    report = jguard_once(oracle, MechanicalObserver(), budget=args.budget)
    print(f"[{_time.strftime('%H:%M:%S')}] {report.summary()}")
    if report.status == "repaired" and args.commit:
        print({"committed": "  committed", "clean": "  nothing to commit",
               "failed": "  commit failed"}[commit_repair(oracle.root, report)])
    if report.status == "refused":
        print(f"  refusal report: {write_refusal(oracle.root, report)}")
    return 0 if report.status in ("green", "repaired") else 2


def cmd_cguard(args) -> int:
    """Guard a C/C++ project: the compiler is a cheap first oracle, the test
    binary is the acceptance gate, same five kernels."""
    import time as _time
    from .coracle import COracle, CBuildError, cguard_once
    from .guard import commit_repair, write_refusal
    from .observers import MechanicalObserver
    _load_dictionary(args)
    oracle = COracle(args.root, build_cmd=args.build_cmd,
                     test_cmd=args.test_cmd, build_dir=args.build_dir,
                     timeout=args.suite_timeout)
    print(f"  build: {oracle.build_cmd}\n  test:  {oracle.test_cmd}")
    while True:
        try:
            report = cguard_once(oracle, MechanicalObserver(),
                                 budget=args.budget)
        except CBuildError as e:
            print(f"fluidfix: {e}")
            return 1
        if report.status != "green" or args.interval is None:
            print(f"[{_time.strftime('%H:%M:%S')}] {report.summary()}")
        if report.status == "repaired" and args.commit:
            print({"committed": "  committed",
                   "clean": "  nothing to commit",
                   "failed": "  commit failed"}[commit_repair(oracle.root,
                                                              report)])
        if report.status == "refused":
            print(f"  refusal report: {write_refusal(oracle.root, report)}")
        if args.interval is None:
            return 0 if report.status in ("green", "repaired") else 2
        _time.sleep(args.interval)


def cmd_hotspots(args) -> int:
    """Answer "what should we test FIRST?" — the question that decides how
    much of a repo fluidfix can maintain. Reads git history; uses coverage
    when the project can produce it."""
    from .hotspots import bugfix_churn, coverage_to_reach, rank_hotspots

    churn, scanned, fixes = bugfix_churn(args.root, commits=args.commits)
    if not churn:
        print("no bug-fix history found here — is this a git repository with "
              "commit messages that say what they fix?")
        return 1
    print(f"scanned {scanned} commits · {fixes} look like bug fixes · "
          f"touching {len(churn)} source files\n")

    covered = None
    if args.coverage:
        from .coracle import COracle
        oracle = COracle(args.root, build_cmd=args.build_cmd,
                         test_cmd=args.test_cmd, build_dir=args.build_dir)
        cov = oracle.coverage()
        if cov.available():
            print("measuring current coverage (instrumented build)...")
            covered = cov.lines(timeout=args.suite_timeout) or None
        if covered is None:
            print("  coverage unavailable — ranking on defect density alone\n")

    rows = rank_hotspots(args.root, churn, covered, limit=args.top)
    head = f"{'#':>3}  {'defects':>7}  {'covered':>7}  file"
    print("WHAT TO TEST FIRST — ranked by defect density x coverage gap")
    print(head)
    for i, r in enumerate(rows, 1):
        cov_s = "     ?" if r["covered"] is None else f"{r['covered']*100:5.0f}%"
        print(f"{i:3d}  {r['defects']:7d}  {cov_s:>7}  {r['file']}")

    print("\nWHAT IT BUYS — share of this repo's OWN historical defects")
    for share, n in coverage_to_reach(churn):
        pct = n / max(len(churn), 1) * 100
        print(f"  guard {share*100:3.0f}% of past defects  ->  test {n:4d} files"
              f"  ({pct:.0f}% of the files that have ever broken)")
    print("\n  Defects cluster, so coverage aimed at the cluster is worth "
          "roughly twice\n  coverage spread evenly. fluidfix maintains "
          "exactly what your tests cover —\n  this is the cheapest order to "
          "widen that.")
    return 0


def cmd_estimate(args) -> int:
    """Answer "how fast will fluidfix be on MY repo?" before anyone commits.

    Measured across three orders of magnitude (independent third-party
    testing, Sept 2026, plus this project's own benchmarks): repair time is
    SUITE RUNS x YOUR SUITE'S OWN RUNTIME. Test count barely matters — 105
    tests that run in 0.07s are cheaper to guard than 20 tests that take 5s.

        2 tests   @ 0.01s ->  2 runs -> ~1.1s
        105 tests @ 0.07s ->  3 runs ->  1.7s
        1,990     @ 4.5s  ->  8 runs ->   36s

    An estimate is only worth as much as the run behind it: this command
    REFUSES to print a number when the suite did not actually execute.
    """
    import time as _time
    from .oracle import HarnessError

    oracle = _oracle(args)
    print(f"timing your suite (one run, {oracle.python})...")
    t0 = _time.time()
    try:
        rc, out = oracle.run(["--tb=no"])
    except Exception as e:                                  # noqa: BLE001
        print(f"could not run the suite: {e}")
        return 1
    secs = _time.time() - t0

    # A number nobody measured is worse than no number. Everything below
    # this line refuses rather than guesses.
    if out.strip() == "TIMEOUT":
        print(f"  your suite did not finish within --suite-timeout "
              f"({args.suite_timeout}s).\n")
        print("EXPECTED REPAIR TIME on this repo")
        print(f"  unmeasurable here, and that IS the answer: at >"
              f"{args.suite_timeout}s per run even a\n  2-run repair costs "
              f"over {2 * args.suite_timeout // 60} minutes. Guard a fast "
              f"subset instead --\n  pass test paths after the root, or "
              f"raise --suite-timeout if the suite\n  really is that long "
              f"and you accept the cost.")
        return 1
    try:
        from .oracle import _check_harness
        _check_harness(rc, oracle.extra_args, out, oracle.root, oracle.python)
    except HarnessError as e:
        print(f"  the suite did not run, so there is nothing to time.\n")
        print(f"{e}")
        return 1

    summary = ""
    for line in reversed(out.strip().splitlines()):
        if " passed" in line or " failed" in line or " error" in line:
            summary = line.strip()[:70]
            break
    if not summary:
        # pytest exited 0 with no summary line: nothing was collected in a
        # way _check_harness recognises. Still refuse — an estimate built on
        # zero tests is a fabrication.
        print("  pytest ran but reported no test results, so this repo has "
              "nothing\n  for fluidfix to be judged by yet. Run `fluidfix "
              "init` to generate a\n  starter smoke suite, then estimate "
              "again.")
        return 1

    startup = 0.5                     # pytest process startup, measured
    per_run = secs + startup
    print(f"  {summary}")
    print(f"  suite runtime: {secs:.2f}s  (+~{startup}s pytest startup "
          f"per run)\n")
    print("EXPECTED REPAIR TIME on this repo")
    print(f"  typical in-vocabulary defect (2-10 suite runs):"
          f"  {2 * per_run:.1f}s - {10 * per_run:.0f}s")
    print(f"  harder localisation (up to 80 runs):           "
          f"  ~{80 * per_run:.0f}s")
    if secs > 60:
        print("\n  Your suite is slow enough that repair cost is dominated by "
              "it.\n  Consider guarding a fast subset "
              "(pass paths after the root) or\n  running on --interval so "
              "each pass handles one fresh regression.")
    elif secs < 5:
        print("\n  Fast suite: repairs will land in seconds. Ideal for the "
              "GitHub Action\n  on every push.")
    print("\n  The arithmetic: time ~= runs x (suite time + startup). "
          "Nothing else\n  in fluidfix costs measurable wall clock — the "
          "kernels decide in\n  nanoseconds; your tests are the entire bill.")
    if rc != 0:
        print("\n  NOTE: your suite is currently RED, so this timing includes "
              "failing\n  tests. fluidfix only acts on a red suite, so this is "
              "the realistic\n  number.")
    return 0


def cmd_selfcheck(args) -> int:
    """Re-derive the shipped laws from scratch. No network, no dependencies.

    Prints the running version first. `pip install fluidfix` is a NO-OP when
    any version is already present — it does not upgrade — so a stale install
    is silent and users report missing subcommands as bugs. Measured three
    times on one machine in a single day. Showing the version costs a line
    and turns that into something a user can see.
    """
    print(f"fluidfix {_version()}")
    from .lanes import ADVANCE, EMIT, HALT
    from .router import route

    bad = 0
    for F1 in range(16):
        for A1 in range(16):
            for Fq in range(16):
                want = (Fq + A1 - F1) % 16
                bad += route(F1, A1, Fq) != want
    print(f"router vs reference, all 4096 (F1,A1,Fq): {4096 - bad}/4096")

    ident = sum(route(F1, A1, F1) != A1 for F1 in range(16) for A1 in range(16))
    print(f"identity route(F1,A1,F1)==A1:               {256 - ident}/256")

    comp = sum(route(0, o2, route(0, o1, q)) != (q + o1 + o2) % 16
               for o1 in range(16) for o2 in range(16) for q in range(16))
    print(f"composition route(o2, route(o1, q)):        {4096 - comp}/4096")

    lane_bad = 0
    for m in range(256):
        if m and EMIT(m) != (m & -m):
            lane_bad += 1
        if m and ADVANCE(m) >= m:
            lane_bad += 1
        if HALT(m) != (1 if m == 0 else 0):
            lane_bad += 1
    print(f"lanes: EMIT/ADVANCE/HALT on 256 states:     {'0 wrong' if not lane_bad else f'{lane_bad} WRONG'}")

    steps = 0
    for m in range(256):
        w = m
        while not HALT(w):
            w = ADVANCE(w)
            steps += 1
            assert steps < 4096, "ADVANCE failed to reduce"
    print(f"termination: every mask drains ({steps} total steps)")
    # ---- law 3: the engine law (dev repo), vendored verbatim ------------
    import hashlib

    from .engine import LAW, decide, situation
    fp = hashlib.sha256(LAW.encode()).hexdigest()
    law_bad = 0 if (len(LAW) == 1555 and fp.startswith("48bf50bff36a2cc9")) else 1
    print(f"engine law fingerprint (sha256 {fp[:16]}, {len(LAW)} chars): "
          f"{'verbatim' if not law_bad else 'DRIFTED'}")
    rulings = {"BUILT": "SHIP", "AMB": "ADD_STATE", "UNREAD": "ADD_MATERIAL",
               "CAPPED": "RAISE_BUDGET", "REFUTED": "HARVEST_COUNTEREXAMPLE"}
    rule_bad = sum(decide(situation(**{k: True})) != v for k, v in rulings.items())
    print(f"engine law rulings the guard depends on:      "
          f"{len(rulings) - rule_bad}/{len(rulings)}")

    # ---- law 4: the ranking law, verified as its author verifies it ------
    from .rank import rank as _rank

    def _spec(x):
        if (x >> 7) & 1:
            return 7
        ev = x & 0x7F
        if not ev:
            return 7
        i = 0
        while not ((ev >> i) & 1):
            i += 1
        return i

    rank_bad = sum(_rank(x) != _spec(x) for x in range(256))
    veto_bad = sum(_rank(x | 128) != 7 for x in range(256))
    mono_bad = sum(1 for x in range(128) for b in range(7)
                   if not ((x >> b) & 1) and _rank(x | (1 << b)) > _rank(x))
    print(f"ranking law vs specification, all 256:       {256 - rank_bad}/256")
    print(f"ranking law veto dominance / monotonicity:   "
          f"{'both hold' if not (veto_bad or mono_bad) else 'VIOLATED'}")

    # ---- law 5: the SIGHT law, verified as its author verifies it ---------
    from .sight import sight as _sight

    def _sspec(x):
        if x & 7:                      # any POINTING bit
            return 0
        for i, base in ((3, 2), (4, 3), (5, 4), (6, 5)):
            if (x >> i) & 1:
                return base + ((x >> 7) & 1)
        return 6 + ((x >> 7) & 1)

    sight_bad = sum(_sight(x) != _sspec(x) for x in range(256))
    # R1: pointing outranks every non-pointing file, at any evidence count
    r1_bad = sum(1 for a in range(256) if a & 7
                 for b in range(256) if not b & 7 and not _sight(a) < _sight(b))
    # R2: the ubiquity penalty cannot reach a pointed-at file
    r2_bad = sum(1 for x in range(256)
                 if x & 7 and _sight(x) != _sight(x & 0x7F))
    # R3: more evidence is never worse
    r3_bad = sum(1 for x in range(256) for b in range(7)
                 if not ((x >> b) & 1) and _sight(x | (1 << b)) > _sight(x))
    print(f"sight law vs specification, all 256:         {256 - sight_bad}/256")
    print(f"sight law tiers (R1 pointing > circumstantial,\n"
          f"  R2 no penalty on pointing, R3 monotone):    "
          f"{'all hold' if not (r1_bad or r2_bad or r3_bad) else 'VIOLATED'}")

    total = (bad or 0) + ident + comp + lane_bad + law_bad + rule_bad \
        + rank_bad + veto_bad + mono_bad \
        + sight_bad + r1_bad + r2_bad + r3_bad
    print("SELFCHECK PASS — 5 laws re-derived" if not total else "SELFCHECK FAIL")
    return 0 if not total else 1


def cmd_kinds(args) -> int:
    """List the fault-class vocabulary: every registered kind plus the slots
    a user dictionary may claim. The kernel routes mod 16, so 16 slots total."""
    import textwrap
    from .acts import KINDS, SHIPPED_KINDS, USER_KINDS
    _load_dictionary(args)
    for kind in range(16):
        if kind in KINDS:
            name, desc, _ = KINDS[kind]
            origin = "shipped" if kind in SHIPPED_KINDS else "taught"
            print(f"{kind:3d}  {name}  ({origin})")
            print(textwrap.fill(desc, width=78, initial_indent="     ",
                                subsequent_indent="     "))
        elif kind in USER_KINDS:
            print(f"{kind:3d}  (free for users — teach it with register() "
                  "in a --dictionary file)")
    return 0


_EXAMPLES = """\
examples:
  fluidfix init [ROOT]                         generate a starter smoke suite
  fluidfix guard ROOT --interval 900 --commit  watch, restore, refuse the novel
  fluidfix guard ROOT --observer claude        LLM eyes, kernel decisions
  fluidfix guard ROOT --dry-run                propose only: patch written, tree untouched
  fluidfix repair ROOT --file pkg/mod.py       localise + repair one defect
  fluidfix packet ROOT --file pkg/mod.py       print the observation packet
  fluidfix jguard ROOT                         guard a Java/Maven project (alpha)
  fluidfix kinds                               list the fault-class vocabulary
  fluidfix selfcheck                           re-verify the shipped laws
"""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="fluidfix", description=__doc__, epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version",
                   version=f"fluidfix {_version()}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, need_file=True):
        sp.add_argument("root", help="target project root (where pytest runs)")
        if need_file:
            sp.add_argument("--file", required=True,
                            help="defect file, relative to root")
        sp.add_argument("--python", default=None, type=_python_arg,
                        help="target project's python (default: this one)")
        sp.add_argument("--cov", default=None,
                        help="coverage target package (default: inferred)")
        sp.add_argument("--dictionary", default=None,
                        help="repo fault-class dictionary: a Python file of "
                             "register() calls, loaded before observing")
        sp.add_argument("--suite-timeout", type=int, default=300,
                        help="full-suite budget in seconds (default 300)")
        sp.add_argument("--test-timeout", type=int, default=60,
                        help="per-test pytest-timeout in seconds (default 60)")

    sp = sub.add_parser("guard", help="commit-and-forget maintenance: watch "
                        "the suite, restore what breaks, refuse what is novel",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog="exit codes (one pass, no --interval): "
                               "0 green or repaired, 2 refused")
    common(sp, need_file=False)
    sp.add_argument("--observer", choices=["mechanical", "claude"],
                    default="mechanical")
    sp.add_argument("--model", default="claude-opus-5")
    sp.add_argument("--candidate-timeout", type=int, default=None,
                    help="per-candidate suite budget (default: --suite-timeout)")
    sp.add_argument("--escalate-budget", type=int, default=600,
                    help="wall-clock cap for law-driven escalation rounds (s)")
    sp.add_argument("--max-candidates", type=int, default=None,
                    help="candidates one act may propose per line (default "
                         "32). Each costs a suite run; raise it for "
                         "name-shaped classes with cheap suites")
    sp.add_argument("--budget", type=int, default=None,
                    help="wall-clock cap for the WHOLE guard pass (s): the "
                         "first pass gets at most a third; the full-sight "
                         "escalation stage gets all the rest (overriding "
                         "--escalate-budget). Default: unbounded first pass")
    sp.add_argument("--interval", type=int, default=None,
                    help="seconds between checks; omit for one pass (CI mode)")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--commit", action="store_true",
                   help="git-commit each restoration (only the repaired file)")
    g.add_argument("--dry-run", action="store_true",
                   help="propose, don't write: print the repair's unified "
                        "diff, restore the tree byte-exactly, save the diff "
                        "to .fluidfix/proposed.patch, exit 0")
    sp.set_defaults(fn=cmd_guard)

    sp = sub.add_parser("repair", help="localise, observe, and repair one defect",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog="exit codes: 0 repaired, 2 refused, "
                               "3 suite green — nothing to repair")
    common(sp)
    sp.add_argument("--observer", choices=["mechanical", "claude"],
                    default="mechanical")
    sp.add_argument("--model", default="claude-opus-5")
    sp.add_argument("--candidate-timeout", type=int, default=None,
                    help="per-candidate suite budget (default: --suite-timeout)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_repair)

    sp = sub.add_parser("packet", help="print the lean observation packet")
    common(sp)
    sp.set_defaults(fn=cmd_packet)

    sp = sub.add_parser("init", help="zero-tests on-ramp: generate a starter "
                        "smoke suite so any repo can be guarded today")
    sp.add_argument("root", nargs="?", default=".")
    sp.add_argument("--python", default=None, type=_python_arg)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("jguard", help="guard a Java/Maven project: JUnit is "
                        "the judge, same kernels, same contracts (alpha)",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog="exit codes: 0 green or repaired, 2 refused")
    sp.add_argument("root", nargs="?", default=".")
    sp.add_argument("--mvn", default="mvn")
    sp.add_argument("--suite-timeout", type=int, default=600)
    sp.add_argument("--budget", type=int, default=None)
    sp.add_argument("--dictionary", default=None)
    sp.add_argument("--commit", action="store_true")
    sp.set_defaults(fn=cmd_jguard)

    sp = sub.add_parser("cguard", help="guard a C/C++ project: the compiler "
                        "is a cheap first oracle, your test binary is the "
                        "judge, same kernels (alpha)",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        epilog="exit codes: 0 green or repaired, 2 refused, "
                               "1 the project does not build")
    sp.add_argument("root", nargs="?", default=".")
    sp.add_argument("--build-cmd", default=None,
                    help="how to build (default: cmake --build <build-dir> -j8)")
    sp.add_argument("--test-cmd", default=None,
                    help="how to run tests (default: a test binary found in "
                         "<build-dir>, else ctest)")
    sp.add_argument("--build-dir", default="build")
    sp.add_argument("--suite-timeout", type=int, default=600)
    sp.add_argument("--budget", type=int, default=None)
    sp.add_argument("--dictionary", default=None)
    sp.add_argument("--commit", action="store_true")
    sp.add_argument("--interval", type=int, default=None,
                    help="seconds between checks; omit for one pass (CI mode). "
                         "With --commit this is commit-and-forget maintenance: "
                         "the guard watches, restores what breaks, and refuses "
                         "what is novel, unattended")
    sp.set_defaults(fn=cmd_cguard)

    sp = sub.add_parser("hotspots", help="what should we test FIRST? ranks "
                        "files by defect density x coverage gap")
    sp.add_argument("root", nargs="?", default=".")
    sp.add_argument("--top", type=int, default=25)
    sp.add_argument("--commits", type=int, default=4000,
                    help="how much history to read (default 4000)")
    sp.add_argument("--coverage", action="store_true",
                    help="also measure current coverage (C/C++ projects; "
                         "builds an instrumented tree)")
    sp.add_argument("--build-cmd", default=None)
    sp.add_argument("--test-cmd", default=None)
    sp.add_argument("--build-dir", default="build")
    sp.add_argument("--suite-timeout", type=int, default=900)
    sp.set_defaults(fn=cmd_hotspots)

    sp = sub.add_parser("kinds", help="list the fault-class vocabulary: every "
                        "registered kind and the free user slots")
    sp.add_argument("--dictionary", default=None,
                    help="load this fault-class dictionary before listing")
    sp.set_defaults(fn=cmd_kinds)

    sp = sub.add_parser("estimate", help="how fast will fluidfix be on THIS "
                        "repo? times your suite and projects repair time")
    common(sp, need_file=False)
    sp.set_defaults(fn=cmd_estimate)

    sp = sub.add_parser("selfcheck", help="re-verify the shipped laws exhaustively")
    sp.set_defaults(fn=cmd_selfcheck)

    args = p.parse_args(argv)
    python = getattr(args, "python", None)
    if python is not None and not _python_works(python):
        # fail fast, one line — a bad interpreter otherwise surfaces as a
        # confusing suite failure (or a traceback) deep inside the oracle
        print(f"fluidfix: --python {python}: not a working interpreter "
              f"(`{python} -c pass` failed)", file=sys.stderr)
        return 2
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
