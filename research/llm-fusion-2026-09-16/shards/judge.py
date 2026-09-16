#!/usr/bin/env python3
"""The judge: fan an incident out to N guards (one per kind, each in its own clone), in parallel, then rule with the
engine law's own outcomes — one passing program ships, two different programs are ambiguous, none is a refusal that
carries every guard's reason. The judge runs no suite of its own.

  PYTHONPATH=<fluidfix>/src python3 judge.py <shards-root> arrow/andor-1 --file arrow/locales.py --budget 900
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; BENCH = HERE.parent
KINDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


def prep(clone: Path, mut: dict):
    def sh(c): return subprocess.run(c, cwd=clone, capture_output=True, text=True)
    sh(["git", "reset", "-q", "--hard", mut["base"]]); sh(["git", "clean", "-fdq", "-e", ".venv"])
    p = clone / mut["file"]; L = p.read_text(encoding="utf-8", newline="").split("\n")
    assert L[mut["lineno"] - 1] == mut["orig"], f"{clone.name}: base line drifted"
    L[mut["lineno"] - 1] = mut["mutated"]; p.write_text("\n".join(L), encoding="utf-8", newline="")
    sh(["git", "-c", "user.name=bench", "-c", "user.email=bench@fluidfix", "commit", "-qam", "bench: inject"])
    shutil.rmtree(clone / ".fluidfix", ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("case"); ap.add_argument("--file", required=True)
    ap.add_argument("--budget", type=int, default=900); ap.add_argument("--kinds", default=",".join(map(str, KINDS)))
    a = ap.parse_args(); repo_name, cid = a.case.split("/")
    mut = json.load(open(BENCH / "cases" / repo_name / cid / "mutation.json"))
    kinds = [int(k) for k in a.kinds.split(",")]
    env = dict(os.environ); env["PYTHONPATH"] = str(BENCH.parents[1] / "src")
    procs = {}
    t0 = time.time()
    for K in kinds:
        clone = Path(a.root) / f"{repo_name}_k{K:02d}"; prep(clone, mut)
        py = str(clone / ".venv" / "bin" / "python")
        # `guard` has no --file (that is `repair`'s flag); the shard guard ranks files itself under the same laws,
        # and the kind-routed dictionary is what makes its search cheap. a.file is kept as the record of the target.
        cmd = [py, "-c", "from fluidfix.cli import main; raise SystemExit(main())", "guard", ".", "--commit", "--budget", str(a.budget),
               "--dictionary", str(HERE / f"kind_{K:02d}.py")]
        procs[K] = (clone, time.time(), subprocess.Popen(cmd, cwd=clone, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    print(f"[{a.case}] {len(procs)} guards launched in parallel, budget {a.budget}s each, target {a.file}", flush=True)
    shards = {}
    for K, (clone, ts, pr) in procs.items():
        out, _ = pr.communicate(timeout=a.budget * 4); dt = round(time.time() - ts, 1)
        cur = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", out)
        ref = clone / ".fluidfix" / "last_refusal.json"; refusal = json.load(open(ref)) if ref.exists() else {}
        content = (clone / mut["file"]).read_bytes() if pr.returncode == 0 else None
        shards[K] = {"exit": pr.returncode, "seconds": dt, "repaired_line": int(m.group(1)) if m else None, "suite_runs": int(m.group(2)) if m else None,
                     "byte_exact": cur == mut["orig"], "hint": (re.search(r"hint: (.*)", out) or [None, ""])[1][:160],
                     "rejected": len(refusal.get("rejected_candidates", [])) + int(refusal.get("rejected_not_listed") or 0), "content": content}
        print(f"  guard k{K:02d}: exit {pr.returncode} in {dt}s runs={shards[K]['suite_runs']} line={shards[K]['repaired_line']} exact={shards[K]['byte_exact']} | {shards[K]['hint'][:70]}", flush=True)
    wall = round(time.time() - t0, 1)
    # ---- the ruling (engine law outcomes, one level up)
    greens = {K: s for K, s in shards.items() if s["exit"] == 0}
    programs = {s["content"] for s in greens.values()}
    held = [K for K, s in shards.items() if "candidate passes" in s["hint"]]
    if len(programs) == 1:
        K = next(iter(greens)); ruling = "SHIP"; verdict = "EXACT" if greens[K]["byte_exact"] else "WRONG-GREEN"
    elif len(programs) > 1: ruling, verdict = "AMB → REFUSE", "REFUSED"
    else: ruling, verdict = "REFUSE (every guard's reason attached)", "REFUSED"
    res = {"case": a.case, "file": a.file, "budget": a.budget, "guards": len(shards), "wall_s": wall, "cpu_sum_s": round(sum(s["seconds"] for s in shards.values()), 1),
           "greens": sorted(greens), "distinct_programs": len(programs), "held": held, "ruling": ruling, "verdict": verdict,
           "shards": {K: {k: v for k, v in s.items() if k != "content"} for K, s in shards.items()}}
    (HERE / f"judge_{repo_name}_{cid}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] JUDGE: {ruling} → {verdict} | greens {sorted(greens)} distinct programs {len(programs)} held {held} | wall {wall}s (serial guard: see cases/) cpu-sum {res['cpu_sum_s']}s", flush=True)


if __name__ == "__main__":
    main()
