#!/usr/bin/env python3
"""The routing law fused into every guard: each fluidfix owns ONE territory and ONE kind.

The lake shards by file, which fixes a search that opened the wrong file. The router version shards by kind,
which fixes a search too broad for its budget. Fusing them gives each small fluidfix both coordinates: it
looks only at its own file, and only at the lines that can exhibit the one fault class the router dispatched
to it. Everything else is a sibling's work.

No product change: the guard is the product's own packet, observer, ranking and repair loop; the harness
restricts each observation to the routed kind, which is what a dispatch means.

  PYTHONPATH=<fluidfix>/src python3 fused.py <clones-root> rich/lenm1-1 --file rich/table.py \
      --kinds 0,1,2,3,4,5,6,7,8,9,10,11,12 --dictionary <rules.py>
"""
import argparse, json, os, re, shutil, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE.parent / "llm-fusion-2026-09-16" / "cases"
SRC = HERE.parents[1] / "src"

DRIVER = """
import sys
src, rel, dictionary, kind = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, src)
from fluidfix import Oracle
from fluidfix.acts import load_dictionary, KINDS
from fluidfix.localize import build_packet
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
from fluidfix.observers import MechanicalObserver
if dictionary:
    load_dictionary(dictionary)
name = KINDS[kind][0] if kind in KINDS else "?"
o = Oracle(".", python=sys.executable)
red, out = o.failing_output()
if not red:
    print("suite green"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10 ** 9)
if pk is None:
    print("no packet"); raise SystemExit(3)
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
mine = []
for x in obs:
    if kind in x.kinds:
        x.kinds = [kind]          # the router dispatched this kind here; the rest belong to siblings
        mine.append(x)
print(f"kind {kind} {name}: {len(mine)} of {len(obs)} observations in {rel}", flush=True)
if not mine:
    print("refused: no line in this territory can exhibit this class"); raise SystemExit(2)
res = repair(o, rel, mine)
print(res.summary())
raise SystemExit(0 if res.repaired else 2)
"""


def sh(cmd, cwd=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


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
    ap.add_argument("--kinds", default="0,1,2,3,4,5,6,7,8,9,10,11,12"); ap.add_argument("--dictionary")
    ap.add_argument("--timeout", type=int, default=420)
    a = ap.parse_args()
    repo_name, cid = a.case.split("/")
    mut = json.load(open(CASES / repo_name / cid / "mutation.json"))
    kinds = [int(k) for k in a.kinds.split(",")]
    root = Path(a.root).resolve()
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    clones = sorted(root.glob(f"{repo_name}_t*"))[: len(kinds)]
    if len(clones) < len(kinds):
        raise SystemExit(f"need {len(kinds)} prepared clones under {root}, found {len(clones)}")

    procs = {}
    t0 = time.time()
    for K, clone in zip(kinds, clones):
        apply_mutation(clone, mut)
        py = str(clone / ".venv" / "bin" / "python")
        procs[K] = (clone, time.time(), subprocess.Popen(
            [py, "-c", DRIVER, str(SRC), a.file, a.dictionary or "", str(K)],
            cwd=clone, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    print(f"[{a.case}] {len(procs)} fused guards on {a.file}: one territory, one kind each", flush=True)

    pending = dict(procs); first_green = None; cancelled = []
    deadline = time.time() + a.timeout
    while pending and time.time() < deadline:
        for K, (clone, ts, pr) in list(pending.items()):
            if pr.poll() is None:
                continue
            del pending[K]
            if pr.returncode == 0 and first_green is None:
                first_green = (K, round(time.time() - t0, 1))
                print(f"  first green: kind {K} at {first_green[1]}s — judge stops the rest", flush=True)
                deadline = time.time()
        if first_green:
            break
        time.sleep(0.3)
    for K, (clone, ts, pr) in pending.items():
        if pr.poll() is None:
            pr.kill(); cancelled.append(K)

    guards = {}
    for K, (clone, ts, pr) in procs.items():
        try:
            out, _ = pr.communicate(timeout=60); code = pr.returncode
        except subprocess.TimeoutExpired:
            pr.kill(); out, code = "TIMEOUT", 124
        if K in cancelled:
            code = 125
        line = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", out or "")
        o = re.search(r"kind \d+ ([\w-]+): (\d+) of (\d+) observations", out or "")
        guards[K] = {"kind_name": o.group(1) if o else "?", "observations": int(o.group(2)) if o else None,
                     "of_total": int(o.group(3)) if o else None, "exit": code,
                     "seconds": round(time.time() - ts, 1), "suite_runs": int(m.group(2)) if m else None,
                     "byte_exact": code == 0 and line == mut["orig"]}
        flag = {0: "GREEN", 2: "refused", 3: "suite green", 124: "timeout", 125: "cancelled"}.get(code, f"exit{code}")
        g = guards[K]
        print(f"  kind {K:2d} {g['kind_name']:28} {flag:9} {g['seconds']:6.1f}s "
              f"obs={g['observations']}/{g['of_total']} runs={g['suite_runs']} "
              f"{'byte-exact' if g['byte_exact'] else ''}", flush=True)
    wall = round(time.time() - t0, 1)
    winner = next((K for K, g in guards.items() if g["exit"] == 0), None)
    verdict = "EXACT" if winner is not None and guards[winner]["byte_exact"] else ("WRONG-GREEN" if winner is not None else "REFUSED")
    res = {"case": a.case, "file": a.file, "guards": len(kinds), "first_green": first_green, "cancelled": cancelled,
           "wall_s": wall, "cpu_sum_s": round(sum(g["seconds"] for g in guards.values()), 1),
           "winner_kind": winner, "verdict": verdict, "per_guard": guards}
    (HERE / f"fused_{repo_name}_{cid}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] JUDGE: {verdict} | winner kind {winner} | wall {wall}s ({len(cancelled)} cancelled) "
          f"cpu-sum {res['cpu_sum_s']}s", flush=True)


if __name__ == "__main__":
    main()
