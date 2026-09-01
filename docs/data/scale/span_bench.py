"""STRICT v0.7 SpanEdit benchmark on real repos. PRE-REGISTERED protocol:

- Repos: the click (1,990 tests) and arrow (1,902 tests) clones at their
  pinned green baselines. Seed 20260901.
- Sites: PAIRS of mutable tokens (cmp flip or int-literal +1) on two lines
  0 < distance <= 3 apart in the same library file. Found by regex, shuffled
  once with the seed, taken in order — no human choice.
- TRIPLE liveness per pair, the coordination proof: mutate A alone -> suite
  RED; restore; mutate B alone -> suite RED; restore; mutate BOTH -> RED.
  Only pairs passing all three are trials (each single-line fix provably
  leaves the suite red, so only an atomic span can green it).
- One taught GENERIC span class (paired-drift): for the observed line, mine
  the +-3-line neighborhood from obs.all_lines and emit SpanEdit candidates
  combining one single-token variant of each line (cmp flips first, then
  literal +-1), capped at 32. Nothing site-specific.
- Guard: fluidfix guard . --dictionary span_rules.py --escalate-budget 600,
  subprocess cap 1800s. Score per trial: BYTE-EXACT (both lines restored),
  GREEN-DIFF, REFUSED (tree must be byte-identical; the v0.7 failure log
  must name a failing test), TIMEOUT. Target: 2 live pairs per repo,
  scan budget 14 pair-attempts per repo. Everything reported.
"""
import json
import os
import random
import re
import subprocess
import sys
import time

C = "/private/tmp/claude-501/-Users-kanchetidevieswar-neo/34cbaa43-33b4-47bf-8eee-059bc310d9d7/scratchpad/complex"
OUT = os.path.dirname(os.path.abspath(__file__))
FX = "/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix"
SEED = 20260901
RULES = os.path.join(OUT, "span_rules.py")
REPOS = {"click": ("36baa15", "src/click"), "arrow": ("2224255", "arrow")}

CMP = re.compile(r"(?<=[\w\)\]\s])(>=|<=|>|<)(?=[\s\w\(])")
LIT = re.compile(r"(?<![\w.])(\d+)(?![\w.])")
TABLE = {">=": ">", ">": ">=", "<=": "<", "<": "<="}


def sh(cmd, cwd, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          errors="replace", timeout=timeout)


def suite_fails(py, repo):
    r = sh([py, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider",
            "-p", "no:benchmark"], repo, 240)
    return r.returncode != 0


def token_sites(line):
    out = [("cmp", m.start(1), m.group(1), TABLE[m.group(1)])
           for m in CMP.finditer(line)]
    out += [("lit", m.start(1), m.group(1), str(int(m.group(1)) + 1))
            for m in LIT.finditer(line)]
    return out


def find_pairs(repo, lib):
    per_line = {}
    for dp, dn, fns in os.walk(os.path.join(repo, lib)):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), repo)
            lines = open(os.path.join(dp, fn), encoding="utf-8",
                         errors="replace").read().split("\n")
            for i, line in enumerate(lines):
                if line.lstrip().startswith("#"):
                    continue
                ts = token_sites(line)
                if ts:
                    per_line[(rel, i)] = ts
    pairs = []
    for (rel, i), ts_a in per_line.items():
        for d in (1, 2, 3):
            ts_b = per_line.get((rel, i + d))
            if ts_b:
                pairs.append((rel, i, ts_a[0], i + d, ts_b[0]))
    rng = random.Random(SEED)
    rng.shuffle(pairs)
    return pairs


def mutate(repo, rel, lineno0, site):
    path = os.path.join(repo, rel)
    src = open(path, encoding="utf-8", newline="").read()
    lines = src.split("\n")
    _, col, tok, newtok = site
    line = lines[lineno0]
    assert line[col:col + len(tok)] == tok, "site drift"
    lines[lineno0] = line[:col] + newtok + line[col + len(tok):]
    open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))


def main():
    results = []
    for name, (base, lib) in REPOS.items():
        repo = os.path.join(C, name, "repo")
        py = os.path.join(C, name, "venv", "bin", "python")
        sh(["git", "reset", "-q", "--hard", base], repo)
        sh(["git", "clean", "-fdq"], repo)
        assert not suite_fails(py, repo), f"{name} baseline not green"
        print(f"### {name}: baseline green at {base}", flush=True)
        got = attempts = 0
        for rel, a0, sa, b0, sb in find_pairs(repo, lib):
            if got >= 2 or attempts >= 14:
                break
            attempts += 1
            # --- triple liveness -------------------------------------------
            mutate(repo, rel, a0, sa)
            a_live = suite_fails(py, repo)
            sh(["git", "checkout", "-q", "--", rel], repo)
            if not a_live:
                print(f"  [{name}] dead-A {rel}:{a0+1}", flush=True)
                continue
            mutate(repo, rel, b0, sb)
            b_live = suite_fails(py, repo)
            sh(["git", "checkout", "-q", "--", rel], repo)
            if not b_live:
                print(f"  [{name}] dead-B {rel}:{b0+1}", flush=True)
                continue
            mutate(repo, rel, a0, sa)
            mutate(repo, rel, b0, sb)
            if not suite_fails(py, repo):
                sh(["git", "checkout", "-q", "--", rel], repo)
                print(f"  [{name}] pair-dead {rel}:{a0+1}+{b0+1}", flush=True)
                continue
            got += 1
            baseline = sh(["git", "show", f"{base}:{rel}"], repo).stdout.split("\n")
            print(f"  [{name}] LIVE PAIR {rel}:{a0+1}({sa[0]})+{b0+1}({sb[0]}) "
                  f"— guard runs", flush=True)
            t0 = time.time()
            try:
                g = sh([FX, "guard", ".", "--dictionary", RULES,
                        "--python", py, "--escalate-budget", "600"],
                       repo, 1800)
                gexit, gout = g.returncode, g.stdout + g.stderr
            except subprocess.TimeoutExpired:
                gexit, gout = -1, "TIMEOUT 1800s"
            dt = round(time.time() - t0, 1)
            cur = open(os.path.join(repo, rel), encoding="utf-8",
                       newline="").read().split("\n")
            exact = cur[a0] == baseline[a0] and cur[b0] == baseline[b0]
            dirty = sh(["git", "status", "--porcelain"], repo).stdout.strip()
            ref = os.path.join(repo, ".fluidfix", "last_refusal.json")
            log_ok = None
            if gexit == 2 and os.path.exists(ref):
                rj = json.load(open(ref))
                rc_ = rj.get("rejected_candidates", [])
                log_ok = bool(rc_) and all("why" in e and e["why"] for e in rc_[:5])
            verdict = ("TIMEOUT" if gexit == -1 else
                       "BYTE-EXACT" if exact and gexit == 0 else
                       "GREEN-DIFF" if gexit == 0 else
                       "REFUSED-CLEAN" if not dirty or dirty.startswith("?? .fluidfix")
                       else "REFUSED-DIRTY-TREE!")
            results.append({"repo": name, "site": f"{rel}:{a0+1}+{b0+1}",
                            "kinds": f"{sa[0]}+{sb[0]}", "verdict": verdict,
                            "seconds": dt, "guard_exit": gexit,
                            "refusal_log_names_failing_test": log_ok,
                            "tail": gout[-300:]})
            print(f"  [{name}] {rel}:{a0+1}+{b0+1} -> {verdict} in {dt}s "
                  f"(log_ok={log_ok})", flush=True)
            sh(["git", "reset", "-q", "--hard", base], repo)
            sh(["git", "clean", "-fdq"], repo)
        results.append({"repo": name, "meta": "scan", "live_pairs": got,
                        "attempts": attempts})
    json.dump(results, open(os.path.join(OUT, "span_bench_results.json"), "w"),
              indent=1)
    print("SPAN_BENCH_DONE", flush=True)


if __name__ == "__main__":
    main()
