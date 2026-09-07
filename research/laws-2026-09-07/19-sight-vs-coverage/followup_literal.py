#!/usr/bin/env python3
"""19-sight-vs-coverage FOLLOW-UP: the LITERAL bit's observation.

sight_vs_coverage.py measured that on cglm the only DISCRIMINATING asserted
literal is `07`, and that `07` is harvested from the ABSOLUTE PATH cglm's
ASSERT macro prints via __FILE__ (this checkout lives under
".../laws-2026-09-07/19-sight-vs-coverage/..."). It names include/cglm/vec2.h
and include/cglm/ivec2.h -- via the comment `REF: http://allenchou.net/2013/07/
cross-product-of-2d-vectors/` -- in all 13 runs, whatever the defect.

This script re-runs a SUBSET of the defects and records, per file:
  * the full eight-bit SIGHT observation and priority
  * SIGHT       ordering with literals harvested from the whole assert line
                (the faithful port of guard.py's rule)
  * SIGHT_FIX   ordering with literals harvested only from the ASSERT(<expr>)
                text -- __FILE__ and __LINE__ excluded
Report-only: one single-token edit at a time, restored in `finally`.

  nice -n 15 ./to.sh 900 ../../../.venv/bin/python followup_literal.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

from fluidfix.acts import KINDS
from fluidfix.coracle import (COracle, _ANSI, _FRAME, _c_sources, _fail_names,
                              find_candidate_files_c)
from fluidfix.guard import _is_test_path
from fluidfix.sight import observe_bits, sight

import sight_vs_coverage as SVC

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "cglm")
SUBSET = ["vec3_add", "vec4_sub_neon", "util_lerp", "mat4_scale_p"]


def harvest(clean: str, strip_path: bool) -> set[str]:
    """Literals from the failing output's assert lines. strip_path=True keeps
    only the ASSERT(<expr>) tail, dropping the __FILE__/__LINE__ prefix."""
    lits: set[str] = set()
    for m in re.finditer(r"^.*(?:assert|ASSERT).*$", clean, re.M):
        line = m.group(0)
        if strip_path:
            i = line.find("ASSERT")
            line = line[i:] if i >= 0 else ""
        lits.update(re.findall(r"\d{2,}", line))
    return lits


def all_bits(oracle, out, universe, fail_cov, spec, strip_path):
    clean = _ANSI.sub("", out)
    srcs = _c_sources(oracle.root, oracle.build_dir)
    framed = {os.path.basename(m.group("f1") or m.group("f2") or "")
              for m in _FRAME.finditer(clean)}
    named = SVC.named_set(oracle, clean, srcs)
    try:
        recent = {l.strip() for l in subprocess.run(
            ["git", "-C", oracle.root, "log", "-40", "--name-only",
             "--format="], capture_output=True, text=True,
            timeout=30).stdout.splitlines() if l.strip()}
    except Exception:                                       # noqa: BLE001
        recent = set()
    bodies = {}
    for rel in universe:
        try:
            bodies[rel] = open(os.path.join(oracle.root, rel),
                               encoding="utf-8", errors="replace").read()
        except OSError:
            pass
    lits = harvest(clean, strip_path)
    lit_named, lit_hits = set(), {}
    for lit in lits:
        pat = re.compile(rf"(?<![\w.]){re.escape(lit)}(?![\w.])")
        hits = [rel for rel, b in bodies.items() if pat.search(b)]
        if 0 < len(hits) <= 2:
            lit_named.update(hits)
            lit_hits[lit] = hits
    scarce_named = set()
    for _k, entry in KINDS.items():
        sig = entry[2]
        if sig is None:
            continue
        hits = [rel for rel, b in bodies.items() if sig.search(b)]
        if 0 < len(hits) <= 2:
            scarce_named.update(hits)
    bits = {}
    for rel in universe:
        s = spec.get(rel, 0.0)
        nf = len(fail_cov.get(rel, ()))
        b = dict(framed=os.path.basename(rel) in framed,
                 scarce=rel in scarce_named, literal=rel in lit_named,
                 failonly=s >= 0.9, named=rel in named, touched=rel in recent,
                 small=0 < nf < 80, ubiquitous=s < 0.25)
        bits[rel] = dict(priority=sight(observe_bits(**b)), **b)
    return bits, dict(lits=sorted(lits), lit_named=sorted(lit_named),
                      lit_hits=lit_hits, framed=sorted(framed))


def order(bits, spec, fail_cov):
    return sorted(bits, key=lambda r: (bits[r]["priority"],
                                       -(1.0 if bits[r]["named"] else 0.0),
                                       -spec.get(r, 0.0),
                                       -len(fail_cov.get(r, ())), r))


def main() -> int:
    defects = {d["id"]: d for d in json.load(open(
        os.path.join(HERE, "defects.json")))}
    out_rows = []
    for did in SUBSET:
        d = defects[did]
        rel, path = d["file"], os.path.join(ROOT, d["file"])
        src = open(path, encoding="utf-8", newline="").read()
        assert src.count(d["old"]) == 1, did
        open(path, "w", encoding="utf-8", newline="").write(
            src.replace(d["old"], d["new"], 1))
        try:
            oracle = COracle(ROOT, build_dir="build")
            fails, out = oracle.failing_output()
            if not fails:
                print(f"[{did}] SKIP green")
                continue
            body = SVC.body_ordering(oracle, out)
            fail_cov, spec = body["fail_cov"], body["spec"]
            universe = [r for r in fail_cov
                        if not _is_test_path(r) and len(fail_cov[r]) > 0]
            b1, m1 = all_bits(oracle, out, universe, fail_cov, spec, False)
            b2, m2 = all_bits(oracle, out, universe, fail_cov, spec, True)
            o1, o2 = order(b1, spec, fail_cov), order(b2, spec, fail_cov)
            row = dict(
                id=did, file=rel,
                rank_body=SVC.rank_of(body["order"], rel),
                rank_sight=SVC.rank_of(o1, rel),
                rank_sight_fix=SVC.rank_of(o2, rel), n=len(universe),
                prio_hist_sight={p: sum(1 for r in universe
                                        if b1[r]["priority"] == p)
                                 for p in range(8) if any(
                                     b1[r]["priority"] == p for r in universe)},
                prio_hist_fix={p: sum(1 for r in universe
                                      if b2[r]["priority"] == p)
                               for p in range(8) if any(
                                   b2[r]["priority"] == p for r in universe)},
                lit_hits_sight=m1["lit_hits"], lit_hits_fix=m2["lit_hits"],
                lits_sight=m1["lits"], lits_fix=m2["lits"],
                n_named=sum(1 for r in universe if b2[r]["named"]),
                top5_sight=o1[:5], top5_fix=o2[:5],
                bits_true=b2.get(rel))
            out_rows.append(row)
            print(f"[{did}] {rel} n={row['n']} rank body={row['rank_body']} "
                  f"sight={row['rank_sight']} sight_FIX={row['rank_sight_fix']} "
                  f"| lits_path={len(m1['lits'])} lits_expr={len(m2['lits'])} "
                  f"| lit_hits_fix={m2['lit_hits']} "
                  f"| prio sight={row['prio_hist_sight']} "
                  f"fix={row['prio_hist_fix']} named={row['n_named']}")
        finally:
            open(path, "w", encoding="utf-8", newline="").write(src)
        json.dump(out_rows, open(os.path.join(HERE, "followup_literal.json"),
                                 "w"), indent=1, default=str)
    rc, _ = SVC.sh(["cmake", "--build", "build", "-j8"])
    rc2, o2t = SVC.sh(["./build/tests"])
    print("restored: build rc", rc, "tests rc", rc2)
    json.dump(out_rows, open(os.path.join(HERE, "followup_literal.json"), "w"),
              indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
