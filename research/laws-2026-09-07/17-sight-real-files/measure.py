#!/usr/bin/env python
"""For each injected single-token defect (defects.json, one site per file,
index chosen by PICK), measure WITHOUT running any repair:

  body order  the candidate FILE order the C body (fluidfix.coracle.
              cguard_once) actually produces. Obtained by calling
              cguard_once with a microscopic --budget so the deadline
              expires before the first candidate is opened: the report's
              `candidates` list is the body's ranking, zero repairs run.
  law order   what the SIGHT law (fluidfix.sight.sight) would rule if the
              C body measured its eight bits the way guard.py does for
              Python (file_priority2), on the SAME coverage the body just
              measured. The C body never calls sight() today.

Per defect: fast build+suite (failing_output), covbuild rebuild, the body's
own gcov probes (cached by wrapping _Coverage.lines so nothing is re-run).
Every run goes through the body's own subprocess path; the whole script is
run under nice -n 15 and bin/timeout. The mutated file is restored after
each defect. Results: results.jsonl (one record per defect) + measure.log.

Run:  cd <this dir> && nice -n 15 bin/timeout 300 \
        /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python measure.py [start] [end]
(300 s covers ~5 defects; the driver run_all.sh loops over slices.)"""
import json, os, re, subprocess, sys, time, traceback
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import (COracle, CBuildError, cguard_once, _c_sources,
                              _fail_names, _FRAME, _is_test_path, _ANSI)
from fluidfix.observers import MechanicalObserver
from fluidfix.sight import sight, observe_bits
from fluidfix.acts import KINDS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "box2d")
PICK = json.load(open(os.path.join(HERE, "pick.json"))) if os.path.exists(os.path.join(HERE, "pick.json")) else {}
DEFECTS = json.load(open(os.path.join(HERE, "defects.json")))
LOG = open(os.path.join(HERE, "measure.log"), "a")

def log(msg):
    print(msg, flush=True); LOG.write(msg + "\n"); LOG.flush()

def git_recent(root, n=40):
    try:
        out = subprocess.run(["git", "-C", root, "log", f"-{n}", "--name-only", "--format="],
                             capture_output=True, text=True, timeout=30).stdout
        return {l.strip() for l in out.splitlines() if l.strip()}
    except Exception:
        return set()

def named_files(clean, fail_tests, srcs):
    """The NAMED lane exactly as find_candidate_files_c scores it (stem or
    partial-stem token match with a failing test name)."""
    stems = {}
    for b, r in srcs.items():
        stems.setdefault(os.path.splitext(b)[0].lower(), []).append(r)
    named = set()
    for name in fail_tests or _fail_names(clean):
        parts = re.split(r"[^A-Za-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name))
        toks = [t for t in (p.lower() for p in parts) if len(t) >= 3 and t not in ("test", "tests")]
        for t in toks:
            named.update(stems.get(t, ()))
            for stem, rels in stems.items():
                if stem != t and (t in stem.split("_") or stem.startswith(t + "_")):
                    named.update(rels)
    return named

def law_order(clean, fail_tests, fail_cov, full_cov, srcs, recent):
    """SIGHT bits per file, mirroring guard.find_candidate_files.file_priority2,
    with C measurements: FRAMED from coracle._FRAME, NAMED from the C stem
    logic, coverage from the body's gcov tier. Universe = files the failing
    tests executed (n_fail > 0), as in guard.py."""
    framed = set()
    for m in _FRAME.finditer(clean):
        base = os.path.basename(m.group("f1") or m.group("f2") or "")
        if base in srcs:
            framed.add(srcs[base])
    universe = [r for r, hit in fail_cov.items() if hit and not _is_test_path(r)]
    bodies = {}
    for rel in universe:
        try:
            bodies[rel] = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        except OSError:
            pass
    # LITERAL: an asserted literal (>= 2 digits) occurring in <= 2 files
    lits = set()
    for m in re.finditer(r"^.*(?:condition false|assert|ENSURE).*$", clean, re.M | re.I):
        lits.update(re.findall(r"\d{2,}", m.group(0)))
    lit_named = set()
    for lit in lits:
        pat = re.compile(rf"(?<![\w.]){re.escape(lit)}(?![\w.])")
        hits = [r for r, b in bodies.items() if pat.search(b)]
        if 0 < len(hits) <= 2:
            lit_named.update(hits)
    # SCARCE: a taught class signal matching LINES in <= 2 files. Measured
    # line-wise (the spec's wording). NOTE guard.py matches sig.search(body)
    # on the WHOLE file text, so its two ^-anchored signals (kinds 2 and 11)
    # can only ever match at the first line of a file; both variants are
    # recorded here so the difference is visible in the report.
    scarce, sig_hits, sig_hits_wholebody = set(), {}, {}
    split = {r: b.split("\n") for r, b in bodies.items()}
    for kind, entry in KINDS.items():
        sig = entry[2]
        if sig is None:
            continue
        hits = [r for r, ls in split.items() if any(sig.search(l) for l in ls)]
        sig_hits[entry[0]] = sorted(hits) if len(hits) <= 3 else len(hits)
        sig_hits_wholebody[entry[0]] = len([r for r, b in bodies.items() if sig.search(b)])
        if 0 < len(hits) <= 2:
            scarce.update(hits)
    named = named_files(clean, fail_tests, srcs)
    rows = []
    for rel in universe:
        n_fail = len(fail_cov[rel])
        n_full = max(len(full_cov.get(rel, ())), n_fail, 1)
        spec = n_fail / n_full
        bits = dict(framed=rel in framed, scarce=rel in scarce, literal=rel in lit_named,
                    failonly=spec >= 0.9, named=rel in named, touched=rel in recent,
                    small=0 < n_fail < 80, ubiquitous=spec < 0.25)
        pri = sight(observe_bits(**bits))
        rows.append((pri, -(1.0 if bits["named"] else 0.0), -spec, -n_fail, rel, bits, n_fail, n_full))
    rows.sort(key=lambda t: t[:5])
    return rows, {"framed": sorted(framed), "scarce": sorted(scarce), "literal": sorted(lit_named),
                  "named": sorted(named & set(universe)), "asserted_literals": sorted(lits),
                  "signal_file_hits_linewise": sig_hits,
                  "signal_file_hits_wholebody": sig_hits_wholebody, "universe": len(universe)}

def run_one(idx, d):
    rel, ln, old, new = d["file"], d["line"], d["old"], d["new"]
    path = os.path.join(ROOT, rel)
    pristine = open(path, "rb").read()
    lines = pristine.decode("utf-8").split("\n")
    assert old in lines[ln - 1], (rel, ln, old, lines[ln - 1])
    lines[ln - 1] = lines[ln - 1].replace(old, new, 1)
    rec = {"n": idx, "file": rel, "line": ln, "old": old, "new": new, "text": d["text"]}
    t0 = time.time()
    try:
        open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))
        oracle = COracle(ROOT, test_cmd="./build/bin/test", build_dir="build", timeout=120)
        cov = oracle.coverage()
        cache = {}
        orig = cov.lines
        def lines_cached(test_filter=None, timeout=None):
            r = orig(test_filter, timeout); cache[test_filter] = r; return r
        cov.lines = lines_cached
        report = cguard_once(oracle, MechanicalObserver(), budget=1e-6)
        rec["status"] = report.status
        rec["seconds_body"] = round(time.time() - t0, 1)
        if report.status == "green":
            rec["note"] = "suite still green: defect not observable"; return rec
        assert not report.attempts, "a repair ran; measurement invalid"
        clean = _ANSI.sub("", oracle._last_out) if hasattr(oracle, "_last_out") else ""
        fails, out = oracle.failing_output()          # cheap re-read: 1 fast build+suite
        clean = _ANSI.sub("", out)
        rec["fail_tests"] = list(oracle._fail_tests)
        rec["failure_excerpt"] = [l for l in clean.splitlines() if "fail" in l.lower() or "condition" in l.lower()][:6]
        body = list(report.candidates)
        rec["body_order"] = body
        rec["clean_tail"] = clean.splitlines()[-12:]
        rec["body_len"] = len(body)
        rec["body_rank"] = body.index(rel) + 1 if rel in body else None
        # reconstruct the body's own fail_cov/full_cov from the cached probes
        fail_cov = {}
        for probe in (oracle._fail_tests or [None])[:4]:
            for r, hit in cache.get(probe, {}).items():
                fail_cov.setdefault(r, set()).update(hit)
        full_cov = cache.get(None, {})
        real = [r for r in fail_cov if not _is_test_path(r)]
        rec["probes"] = [p for p in cache if p is not None]
        rec["credible"] = len(real) >= 5
        rec["n_fail_cov_files"] = len(real)
        rec["true_file_in_fail_cov"] = rel in fail_cov
        srcs = _c_sources(ROOT, "build")
        recent = git_recent(ROOT)
        rows, lanes = law_order(clean, oracle._fail_tests, fail_cov, full_cov, srcs, recent)
        order = [r[4] for r in rows]
        rec["law_order"] = [(r[4], r[0]) for r in rows[:12]]
        rec["law_rank"] = order.index(rel) + 1 if rel in order else None
        me = next((r for r in rows if r[4] == rel), None)
        rec["true_bits"] = me[5] if me else None
        rec["true_priority"] = me[0] if me else None
        rec["true_n_fail"] = me[6] if me else None
        rec["true_n_full"] = me[7] if me else None
        rec["lanes"] = lanes
        # every file's measured byte, so the law order can be recomputed offline
        rec["rows"] = [[r[4], r[0], r[6], r[7], r[5]] for r in rows]
        rec["priority_hist"] = {}
        for r in rows:
            rec["priority_hist"][str(r[0])] = rec["priority_hist"].get(str(r[0]), 0) + 1
    except CBuildError as e:
        rec["status"] = "build-error"; rec["note"] = str(e)[:300]
    except Exception as e:
        rec["status"] = "error"; rec["note"] = traceback.format_exc()[-800:]
    finally:
        open(path, "wb").write(pristine)
    rec["seconds"] = round(time.time() - t0, 1)
    return rec

# ---- second round: retry green files with alternates; fill rows on early records
def _latest():
    latest = {}
    p = os.path.join(HERE, "results.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line); latest[r["file"]] = r
    return latest

def retry_file(rel):
    alts = json.load(open(os.path.join(HERE, "alt_defects.json"))).get(rel, [])
    for k, d in enumerate(alts):
        log(f"--- [retry {rel} alt {k}] L{d['line']} {d['old']!r}->{d['new']!r}")
        rec = run_one(100 + k, d); rec["retry"] = True
        with open(os.path.join(HERE, "results.jsonl"), "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        log(f"    status={rec.get('status')} body_rank={rec.get('body_rank')} law_rank={rec.get('law_rank')} fails={rec.get('fail_tests')} {rec.get('seconds')}s")
        if rec.get("status") != "green":
            return

def fill_rows():
    for rel, r in _latest().items():
        if r["status"] == "refused" and "rows" not in r and r.get("fail_tests"):
            d = {"file": rel, "line": r["line"], "old": r["old"], "new": r["new"], "text": r["text"]}
            log(f"--- [fill {rel}] L{d['line']}")
            rec = run_one(r["n"], d); rec["refill"] = True
            with open(os.path.join(HERE, "results.jsonl"), "a") as f:
                f.write(json.dumps(rec, default=str) + "\n")
            log(f"    status={rec.get('status')} body_rank={rec.get('body_rank')} law_rank={rec.get('law_rank')} {rec.get('seconds')}s")

if __name__ == "__main__" and sys.argv[1:2] == ["--retry"]:
    retry_file(sys.argv[2])
elif __name__ == "__main__" and sys.argv[1:2] == ["--fill"]:
    fill_rows()
elif __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(DEFECTS)
    for i in range(start, min(end, len(DEFECTS))):
        picks = DEFECTS[i]
        d = picks[PICK.get(picks[0]["file"], 0)]
        log(f"--- [{i}] {d['file']}:{d['line']} {d['old']!r}->{d['new']!r}")
        rec = run_one(i, d)
        with open(os.path.join(HERE, "results.jsonl"), "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        log(f"    status={rec.get('status')} body_rank={rec.get('body_rank')} law_rank={rec.get('law_rank')} "
            f"bits={rec.get('true_bits')} fails={rec.get('fail_tests')} {rec.get('seconds')}s {rec.get('note','')[:120]}")

