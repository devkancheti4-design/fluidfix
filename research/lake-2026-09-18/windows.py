#!/usr/bin/env python3
"""The lake at finer grain: one guard per LINE RANGE of one file, not one per file.

Measured first: a single guard owning rich/table.py at full sight restores the fault in 277 s over 117 suite
runs, because it walks its own file's observations until it reaches line 638. Splitting that territory into W
line ranges gives each guard a fraction of the walk, and the judge — connected to all of them — ends the run
on the first green. This is the user's claim tested directly: fluidfix is small, so use more of them.

  PYTHONPATH=<fluidfix>/src python3 windows.py <clones-root> rich/lenm1-1 --file rich/table.py \
      --windows 4 --dictionary <rules.py> [--timeout 420]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE.parent / "llm-fusion-2026-09-16" / "cases"
SRC = HERE.parents[1] / "src"

# Same product code as a whole-file guard; the only difference is that this one is told which slice of its
# file it owns. Observations outside the window belong to a sibling guard.
DRIVER = """
import sys
src, rel, dictionary, lo, hi = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
if dictionary:
    load_dictionary(dictionary)
o = Oracle(".", python=sys.executable)
red, out = o.failing_output()
if not red:
    print("suite green"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10 ** 9)
if pk is None:
    print("no packet"); raise SystemExit(3)
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
mine = [x for x in obs if lo <= x.lineno <= hi]
print(f"window {lo}-{hi}: {len(mine)} of {len(obs)} observations", flush=True)
if not mine:
    print("refused: no observation in this window"); raise SystemExit(2)
res = repair(o, rel, mine)
print(res.summary())
raise SystemExit(0 if res.repaired else 2)
"""


def sh(cmd, cwd=None, env=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True)


def apply_mutation(clone: Path, mut: dict):
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=clone)
    sh(["git", "clean", "-fdq", "-e", ".venv"], cwd=clone)
    p = clone / mut["file"]
    lines = p.read_text(encoding="utf-8", newline="").split("\n")
    assert lines[mut["lineno"] - 1] == mut["orig"], f"{clone.name}: base line drifted"
    lines[mut["lineno"] - 1] = mut["mutated"]
    p.write_text("\n".join(lines), encoding="utf-8", newline="")
    sh(["git", "-c", "user.name=lake", "-c", "user.email=lake@fluidfix", "commit", "-qam", "lake: inject"], cwd=clone)
    shutil.rmtree(clone / ".fluidfix", ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("case"); ap.add_argument("--file", required=True)
    ap.add_argument("--windows", type=int, default=4); ap.add_argument("--dictionary")
    ap.add_argument("--timeout", type=int, default=420)
    a = ap.parse_args()
    repo_name, cid = a.case.split("/")
    mut = json.load(open(CASES / repo_name / cid / "mutation.json"))
    root = Path(a.root).resolve()
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)

    clones = sorted(root.glob(f"{repo_name}_t*"))[: a.windows]
    if len(clones) < a.windows:
        raise SystemExit(f"need {a.windows} prepared clones under {root}, found {len(clones)}")
    nlines = len((clones[0] / a.file).read_text(encoding="utf-8", newline="").split("\n"))
    step = -(-nlines // a.windows)
    ranges = [(i * step + 1, min(nlines, (i + 1) * step)) for i in range(a.windows)]
    owner = next(i for i, (lo, hi) in enumerate(ranges) if lo <= mut["lineno"] <= hi)
    print(f"[{a.case}] {a.file}: {nlines} lines split into {a.windows} windows {ranges}; "
          f"the fault at line {mut['lineno']} sits in window {owner}", flush=True)

    procs = {}
    t0 = time.time()
    for i, (clone, (lo, hi)) in enumerate(zip(clones, ranges)):
        apply_mutation(clone, mut)
        py = str(clone / ".venv" / "bin" / "python")
        procs[i] = (clone, (lo, hi), time.time(), subprocess.Popen(
            [py, "-c", DRIVER, str(SRC), a.file, a.dictionary or "", str(lo), str(hi)],
            cwd=clone, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    print(f"[{a.case}] {len(procs)} window guards launched in parallel", flush=True)

    pending = dict(procs); first_green = None; cancelled = []
    deadline = time.time() + a.timeout
    while pending and time.time() < deadline:
        for i, (clone, rng, ts, pr) in list(pending.items()):
            if pr.poll() is None:
                continue
            del pending[i]
            if pr.returncode == 0 and first_green is None:
                first_green = (i, rng, round(time.time() - t0, 1))
                print(f"  first green: window {i} {rng} at {first_green[2]}s — judge stops the rest", flush=True)
                deadline = time.time()
        if first_green:
            break
        time.sleep(0.3)
    for i, (clone, rng, ts, pr) in pending.items():
        if pr.poll() is None:
            pr.kill(); cancelled.append(i)

    guards = {}
    for i, (clone, rng, ts, pr) in procs.items():
        try:
            out, _ = pr.communicate(timeout=60); code = pr.returncode
        except subprocess.TimeoutExpired:
            pr.kill(); out, code = "TIMEOUT", 124
        if i in cancelled:
            code = 125
        line = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", out or "")
        nobs = (re.search(r"window \d+-\d+: (\d+) of (\d+) observations", out or "") or [None, "-", "-"])
        guards[i] = {"range": rng, "exit": code, "seconds": round(time.time() - ts, 1),
                     "observations": nobs[1], "of_total": nobs[2], "suite_runs": int(m.group(2)) if m else None,
                     "byte_exact": code == 0 and line == mut["orig"]}
        flag = {0: "GREEN", 2: "refused", 3: "suite green", 124: "timeout", 125: "cancelled"}.get(code, f"exit{code}")
        print(f"  window {i} {str(rng):16} {flag:9} {guards[i]['seconds']:6.1f}s obs={nobs[1]}/{nobs[2]} "
              f"runs={guards[i]['suite_runs']} {'byte-exact' if guards[i]['byte_exact'] else ''}", flush=True)
    wall = round(time.time() - t0, 1)
    winner = next((i for i, g in guards.items() if g["exit"] == 0), None)
    verdict = "EXACT" if winner is not None and guards[winner]["byte_exact"] else ("WRONG-GREEN" if winner is not None else "REFUSED")
    res = {"case": a.case, "file": a.file, "windows": a.windows, "ranges": ranges, "fault_window": owner,
           "first_green": first_green, "cancelled": cancelled, "wall_s": wall,
           "cpu_sum_s": round(sum(g["seconds"] for g in guards.values()), 1), "verdict": verdict, "guards": guards}
    (HERE / f"windows_{repo_name}_{cid}_{a.windows}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] JUDGE: {verdict} | winner window {winner} | wall {wall}s "
          f"({len(cancelled)} cancelled) cpu-sum {res['cpu_sum_s']}s", flush=True)


if __name__ == "__main__":
    main()
