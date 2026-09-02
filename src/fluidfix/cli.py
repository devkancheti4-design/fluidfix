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


def cmd_selfcheck(args) -> int:
    """Re-derive the shipped laws from scratch. No network, no dependencies."""
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
    print("SELFCHECK PASS" if not (bad or ident or comp or lane_bad) else "SELFCHECK FAIL")
    return 0 if not (bad or ident or comp or lane_bad) else 1


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

    sp = sub.add_parser("kinds", help="list the fault-class vocabulary: every "
                        "registered kind and the free user slots")
    sp.add_argument("--dictionary", default=None,
                    help="load this fault-class dictionary before listing")
    sp.set_defaults(fn=cmd_kinds)

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
