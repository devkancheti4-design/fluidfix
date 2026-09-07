#!/usr/bin/env python3
"""19-sight-vs-coverage: the SIGHT law's FILE ranking vs the gcov coverage
tier that cguard_once (src/fluidfix/coracle.py) actually uses.

Report-only. For each defect in defects.json, ONE single-token edit is made
in the PRIVATE cglm copy beside this script, the suite is run once for the
failing output, then THREE orderings of candidate files are computed and the
rank of the true defect file under each is recorded. No repair is attempted.
The file is restored after every defect.

  BODY      exactly what cguard_once builds today (coracle.py 686-745,
            replicated line for line): find_candidate_files_c prefix (frames,
            then NAMED stem affinity, else size), then the coverage extras
            sorted by (-specificity, n_fail, name), then the credible-drop.
  PURECOV   the coverage tier alone: every production file the failing
            probes executed, sorted by (-specificity, n_fail, name).
  SIGHT     the SIGHT law, its eight bits measured the way guard.py measures
            them for Python (find_candidate_files, guard.py ~145-302) but on
            the C evidence: FRAMED from coracle's _FRAME, NAMED from
            coracle's own stem-affinity rule, SCARCE/LITERAL over the file
            bodies, FAILONLY/SMALL/UBIQUITOUS from the SAME gcov numbers the
            tier uses, TOUCHED from git log -40. Sort key mirrors guard.py
            line 300: (priority, -named, -specificity, -n_fail, name).
  SIGHT0    the SIGHT law with NO coverage at all (only the bits that do not
            need gcov), universe = every production source, tie-break by
            size like coracle's evidence-free fallback.

Usage (from this directory, one run at a time):
  nice -n 15 ./to.sh 1800 ../../../.venv/bin/python sight_vs_coverage.py defects.json results.json
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
from fluidfix.sight import BITS, observe_bits, sight

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "cglm")


# --------------------------------------------------------------- BODY ----
def body_ordering(oracle: COracle, out: str) -> dict:
    """EXACT replica of the candidate list cguard_once builds (coracle.py
    lines 686-745). Every threshold below (4 probes, <5 credible, >=3 keep)
    is copied from there, not chosen here."""
    timing = {}
    t0 = time.time()
    candidates = find_candidate_files_c(oracle, out)
    timing["find_candidate_files_c_s"] = time.time() - t0
    prefix = list(candidates)

    fail_cov: dict[str, set[int]] = {}
    cov = oracle.coverage()
    probes = (oracle._fail_tests or [None])[:4]
    t0 = time.time()
    for probe in probes:
        for rel, hit in cov.lines(probe).items():
            fail_cov.setdefault(rel, set()).update(hit)
    timing["probe_coverage_s"] = time.time() - t0          # includes covbuild rebuild
    t0 = time.time()
    full_cov = cov.lines() if fail_cov else {}
    timing["full_coverage_s"] = time.time() - t0
    real = [r for r in fail_cov if not _is_test_path(r)]
    if len(real) < 5:
        fail_cov = {r: h for r, h in full_cov.items()}
        credible = False
    else:
        credible = True

    def _spec(rel):
        f = len(fail_cov.get(rel, ()))
        u = max(len(full_cov.get(rel, ())), f, 1)
        return min(f / u, 1.0)

    dropped: list[str] = []
    if fail_cov:
        seen = set(candidates)
        extra = [r for r in fail_cov if r not in seen and not _is_test_path(r)]
        extra.sort(key=lambda r: (-_spec(r), len(fail_cov[r]), r))
        candidates = candidates + extra
        if credible:
            touched = [c for c in candidates if c in fail_cov]
            if len(touched) >= 3:
                dropped = [c for c in candidates if c not in fail_cov]
                candidates = touched
    return dict(order=candidates, prefix=prefix, credible=credible,
                probes=probes, dropped=dropped, timing=timing,
                fail_cov=fail_cov, full_cov=full_cov,
                spec={r: _spec(r) for r in fail_cov})


# ------------------------------------------------------------- PURECOV ----
def purecov_ordering(fail_cov, spec) -> list[str]:
    files = [r for r in fail_cov if not _is_test_path(r)]
    files.sort(key=lambda r: (-spec[r], len(fail_cov[r]), r))
    return files


# --------------------------------------------------------------- SIGHT ----
def named_set(oracle: COracle, clean: str, srcs: dict[str, str]) -> set[str]:
    """coracle's own NAMED rule (find_candidate_files_c, stem affinity),
    without the size fallback: the set of files with affinity score > 0."""
    stems: dict[str, list[str]] = {}
    for b, r in srcs.items():
        stems.setdefault(os.path.splitext(b)[0].lower(), []).append(r)
    named: set[str] = set()
    for name in oracle._fail_tests or _fail_names(clean):
        parts = re.split(r"[^A-Za-z0-9]+",
                         re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name))
        toks = [t for t in (p.lower() for p in parts) if len(t) >= 3]
        for t in toks:
            if t in ("test", "tests"):
                continue
            named.update(stems.get(t, ()))
            for stem, rels in stems.items():
                if stem != t and (t in stem.split("_")
                                  or stem.startswith(t + "_")):
                    named.update(rels)
    return named


def sight_bits(oracle: COracle, out: str, universe: list[str],
               fail_cov, spec, with_coverage: bool) -> tuple[dict, dict]:
    clean = _ANSI.sub("", out)
    srcs = _c_sources(oracle.root, oracle.build_dir)
    t0 = time.time()
    framed = {os.path.basename(m.group("f1") or m.group("f2") or "")
              for m in _FRAME.finditer(clean)}
    named = named_set(oracle, clean, srcs)
    try:
        recent = {l.strip() for l in subprocess.run(
            ["git", "-C", oracle.root, "log", "-40", "--name-only",
             "--format="], capture_output=True, text=True,
            timeout=30).stdout.splitlines() if l.strip()}
    except Exception:                                       # noqa: BLE001
        recent = set()
    # guard.py reads literals from `assert` lines; cglm prints
    # `assert fail in <file> on line <n> : ASSERT(...)` and the values the
    # runner echoes, so the same regex applied to every line mentioning
    # assert is the faithful port.
    assert_lits: set[str] = set()
    for m in re.finditer(r"^.*(?:assert|ASSERT).*$", clean, re.M):
        assert_lits.update(re.findall(r"\d{2,}", m.group(0)))
    bodies: dict[str, str] = {}
    for rel in universe:
        try:
            bodies[rel] = open(os.path.join(oracle.root, rel),
                               encoding="utf-8", errors="replace").read()
        except OSError:
            pass
    lit_named: set[str] = set()
    for lit in assert_lits:
        pat = re.compile(rf"(?<![\w.]){re.escape(lit)}(?![\w.])")
        hits = [rel for rel, b in bodies.items() if pat.search(b)]
        if 0 < len(hits) <= 2:
            lit_named.update(hits)
    scarce_named: set[str] = set()
    scarce_counts: dict[str, int] = {}
    for kind, entry in KINDS.items():
        sig = entry[2]
        if sig is None:
            continue
        hits = [rel for rel, b in bodies.items() if sig.search(b)]
        scarce_counts[str(kind)] = len(hits)
        if 0 < len(hits) <= 2:
            scarce_named.update(hits)
    bits: dict[str, dict] = {}
    for rel in universe:
        s = spec.get(rel, 0.0) if with_coverage else 0.0
        n_fail = len(fail_cov.get(rel, ())) if with_coverage else 0
        b = dict(framed=os.path.basename(rel) in framed,
                 scarce=rel in scarce_named,
                 literal=rel in lit_named,
                 failonly=with_coverage and s >= 0.9,
                 named=rel in named,
                 touched=rel in recent,
                 small=with_coverage and 0 < n_fail < 80,
                 ubiquitous=with_coverage and s < 0.25)
        bits[rel] = dict(priority=sight(observe_bits(**b)), **b)
    meta = dict(measure_s=time.time() - t0, framed=sorted(framed),
                assert_lits=sorted(assert_lits), lit_named=sorted(lit_named),
                scarce_named=sorted(scarce_named), scarce_counts=scarce_counts,
                named_n=len(named), touched_n=len(recent))
    return bits, meta


def sight_ordering(bits, spec, fail_cov, sizes) -> list[str]:
    """guard.py line 300: (priority, -affinity, -specificity, -n_fail, rel)."""
    return sorted(bits, key=lambda r: (bits[r]["priority"],
                                       -(1.0 if bits[r]["named"] else 0.0),
                                       -spec.get(r, 0.0),
                                       -len(fail_cov.get(r, ())), r))


def sight0_ordering(bits, sizes) -> list[str]:
    return sorted(bits, key=lambda r: (bits[r]["priority"],
                                       -(1.0 if bits[r]["named"] else 0.0),
                                       -sizes.get(r, 0), r))


# --------------------------------------------------------------- utils ----
def rank_of(order: list[str], rel: str) -> int | None:
    return order.index(rel) + 1 if rel in order else None


def spearman(a: list[str], b: list[str]) -> float | None:
    common = [x for x in a if x in b]
    n = len(common)
    if n < 2:
        return None
    ra = {x: i for i, x in enumerate(x for x in a if x in b)}
    rb = {x: i for i, x in enumerate(x for x in b if x in a)}
    d2 = sum((ra[x] - rb[x]) ** 2 for x in common)
    return 1 - 6 * d2 / (n * (n * n - 1))


def sh(cmd: list[str], timeout=300) -> tuple[int, str]:
    p = subprocess.run(["nice", "-n", "15", os.path.join(HERE, "to.sh"),
                        str(timeout)] + cmd, cwd=ROOT, capture_output=True,
                       text=True, errors="replace")
    return p.returncode, p.stdout + p.stderr


# ---------------------------------------------------------------- main ----
def main(defects_path: str, out_path: str) -> int:
    defects = json.load(open(defects_path))
    results = []
    for d in defects:
        rel, old, new = d["file"], d["old"], d["new"]
        path = os.path.join(ROOT, rel)
        src = open(path, encoding="utf-8", newline="").read()
        n = src.count(old)
        rec = dict(id=d["id"], file=rel, old=old, new=new)
        if n != 1:
            rec["skipped"] = f"old text occurs {n} times (need exactly 1)"
            print(f"[{d['id']}] SKIP {rel}: {rec['skipped']}")
            results.append(rec)
            continue
        line_no = src[:src.index(old)].count("\n") + 1
        rec["line"] = line_no
        open(path, "w", encoding="utf-8", newline="").write(
            src.replace(old, new, 1))
        try:
            # a FRESH oracle per defect: _Coverage._ensure_build only
            # rebuilds the instrumented tree once per instance, exactly as
            # one cguard invocation would see it
            oracle = COracle(ROOT, build_dir="build")
            t0 = time.time()
            fails, out = oracle.failing_output()
            rec["suite_s"] = time.time() - t0
            if not fails:
                rec["skipped"] = "suite stayed green after the edit"
                print(f"[{d['id']}] SKIP {rel}:{line_no} suite green")
                results.append(rec)
                continue
            clean = _ANSI.sub("", out)
            rec["fail_tests"] = oracle._fail_tests[:8]
            rec["n_fail_tests"] = len(_fail_names(clean))
            rec["frames"] = sorted({m.group("f1") or m.group("f2")
                                    for m in _FRAME.finditer(clean)})[:5]

            body = body_ordering(oracle, out)
            fail_cov, full_cov, spec = body["fail_cov"], body["full_cov"], body["spec"]
            purecov = purecov_ordering(fail_cov, spec)
            universe = [r for r in fail_cov
                        if not _is_test_path(r) and len(fail_cov[r]) > 0]
            srcs = _c_sources(ROOT, "build")
            sizes = {}
            for r in set(universe) | set(srcs.values()):
                try:
                    sizes[r] = os.path.getsize(os.path.join(ROOT, r))
                except OSError:
                    sizes[r] = 0
            bits, meta = sight_bits(oracle, out, universe, fail_cov, spec, True)
            sight_o = sight_ordering(bits, spec, fail_cov, sizes)
            bits0, meta0 = sight_bits(oracle, out, sorted(set(srcs.values())),
                                      fail_cov, spec, False)
            sight0_o = sight0_ordering(bits0, sizes)

            rec.update(
                credible=body["credible"], probes=body["probes"],
                n_fail_cov_files=len(universe),
                n_full_cov_files=len([r for r in full_cov if not _is_test_path(r)]),
                harness_in_candidates=[r for r in body["order"]
                                       if r.startswith("test/")],
                prefix=body["prefix"], dropped_n=len(body["dropped"]),
                body_top5=body["order"][:5], purecov_top5=purecov[:5],
                sight_top5=sight_o[:5], sight0_top5=sight0_o[:5],
                rank_body=rank_of(body["order"], rel),
                rank_purecov=rank_of(purecov, rel),
                rank_sight=rank_of(sight_o, rel),
                rank_sight0=rank_of(sight0_o, rel),
                n_body=len(body["order"]), n_sight=len(sight_o),
                n_sight0=len(sight0_o),
                spec_true=spec.get(rel), n_fail_true=len(fail_cov.get(rel, ())),
                n_full_true=len(full_cov.get(rel, ())),
                bits_true=bits.get(rel), bits0_true=bits0.get(rel),
                sight_meta=meta, sight0_meta=meta0,
                spearman_body_sight=spearman(body["order"], sight_o),
                spearman_purecov_sight=spearman(purecov, sight_o),
                top1_agree=(body["order"][:1] == sight_o[:1]),
                timing=body["timing"],
                spec_hist={k: sum(1 for r in universe if spec[r] >= k)
                           for k in (0.9, 0.5, 0.25)},
                priority_hist={p: sum(1 for r in universe
                                      if bits[r]["priority"] == p)
                               for p in range(8)},
            )
            print(f"[{d['id']}] {rel}:{line_no} fails={rec['n_fail_tests']} "
                  f"credible={rec['credible']} covfiles={len(universe)} "
                  f"rank body={rec['rank_body']} purecov={rec['rank_purecov']} "
                  f"sight={rec['rank_sight']} sight0={rec['rank_sight0']} "
                  f"spec_true={rec['spec_true']} "
                  f"t_cov={body['timing']['probe_coverage_s'] + body['timing']['full_coverage_s']:.1f}s "
                  f"t_sight={meta['measure_s']:.2f}s")
        finally:
            open(path, "w", encoding="utf-8", newline="").write(src)
        results.append(rec)
        json.dump(results, open(out_path, "w"), indent=1, default=str)
    # leave the copy green
    rc, o = sh(["cmake", "--build", "build", "-j8"])
    rc2, o2 = sh(["./build/tests"])
    print("restored: build rc", rc, "tests rc", rc2, o2.strip().splitlines()[-1:] )
    json.dump(results, open(out_path, "w"), indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
