# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""fluidfix CLI.

  fluidfix repair ROOT --file pkg/mod.py [--python VENV_PY] [--observer mechanical|claude]
  fluidfix packet ROOT --file pkg/mod.py [--python VENV_PY]
  fluidfix selfcheck
"""
from __future__ import annotations

import argparse
import json
import sys


def _oracle(args):
    from .oracle import Oracle
    return Oracle(args.root, python=args.python,
                  timeout=args.suite_timeout,
                  per_test_timeout=args.test_timeout)


def cmd_repair(args) -> int:
    from .localize import build_packet
    from .loop import repair
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


def cmd_packet(args) -> int:
    from .localize import build_packet
    packet = build_packet(_oracle(args), args.file, coverage_target=args.cov)
    if packet is None:
        print("suite is green — no packet")
        return 3
    print(packet.render())
    return 0


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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="fluidfix", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("root", help="target project root (where pytest runs)")
        sp.add_argument("--file", required=True,
                        help="defect file, relative to root")
        sp.add_argument("--python", default=None,
                        help="target project's python (default: this one)")
        sp.add_argument("--cov", default=None,
                        help="coverage target package (default: inferred)")
        sp.add_argument("--suite-timeout", type=int, default=300,
                        help="full-suite budget in seconds (default 300)")
        sp.add_argument("--test-timeout", type=int, default=60,
                        help="per-test pytest-timeout in seconds (default 60)")

    sp = sub.add_parser("repair", help="localise, observe, and repair one defect")
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

    sp = sub.add_parser("selfcheck", help="re-verify the shipped laws exhaustively")
    sp.set_defaults(fn=cmd_selfcheck)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
