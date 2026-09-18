#!/usr/bin/env python3
"""The lake: one guard per TERRITORY of a repository, all at once, one judge over their reports.

Debugging mode has two sharding keys. `shards/judge.py` (2026-09-16) shards by KIND — the router law's own
domain — which fixes a search that is too broad for its budget. This shards by FILE, which fixes a search
that opened the wrong file: every file the failing test executed gets its own guard, so the ranking only has
to COVER the fault, never rank it first.

Each guard is `fluidfix repair --file <territory>` in its own clone: the same six laws, the same suite, the
same byte-exact rollback, no product change. The judge runs no suite of its own — it reads what the guards
wrote and rules: exactly one program → SHIP; two different programs → AMB, refuse; none → refuse with every
guard's reason.

  PYTHONPATH=<fluidfix>/src python3 lake.py <clones-root> rich/lenm1-1 \
      --template <a clone of rich> --dictionary <rules.py> [--max 16] [--timeout 420]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE.parent / "llm-fusion-2026-09-16" / "cases"
SRC = HERE.parents[1] / "src"


def sh(cmd, cwd=None, env=None, timeout=1800, check=False):
    try:
        return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        class T: returncode, stdout, stderr = 124, "TIMEOUT", ""
        return T()


def apply_mutation(clone: Path, mut: dict, commit: bool = True):
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=clone)
    sh(["git", "clean", "-fdq", "-e", ".venv"], cwd=clone)
    p = clone / mut["file"]
    lines = p.read_text(encoding="utf-8", newline="").split("\n")
    assert lines[mut["lineno"] - 1] == mut["orig"], f"{clone.name}: base line drifted"
    lines[mut["lineno"] - 1] = mut["mutated"]
    p.write_text("\n".join(lines), encoding="utf-8", newline="")
    if commit:
        sh(["git", "-c", "user.name=lake", "-c", "user.email=lake@fluidfix", "commit", "-qam", "lake: inject"], cwd=clone)
    shutil.rmtree(clone / ".fluidfix", ignore_errors=True)


def territories(template: Path, mut: dict, env) -> list[tuple[str, int]]:
    """The files the FAILING TEST executed, most-executed first. This is coverage, not ranking:
    the lake does not need to know which file is guilty, only which files were in the room."""
    apply_mutation(template, mut, commit=False)
    py = str(template / ".venv" / "bin" / "python")
    code = f'''
import json, os, sys
sys.path.insert(0, {str(SRC)!r})
from fluidfix import Oracle
from fluidfix.guard import _is_test_path
o = Oracle(".", python=sys.executable)
red, out = o.failing_output()
cov = os.path.join(".", "_lake_cov.json")
o.run(["--lf", "--tb=no", "--cov=.", f"--cov-report=json:{{cov}}"], cache=True)
files = {{}}
if os.path.exists(cov):
    d = json.load(open(cov)); os.remove(cov)
    for f, data in d.get("files", {{}}).items():
        rel = f.replace("\\\\", "/")
        n = len(data.get("executed_lines", []))
        if n and rel.endswith(".py") and not _is_test_path(rel) and "/.venv/" not in rel and "site-packages" not in rel:
            files[rel] = n
print(json.dumps({{"red": red, "files": files}}))
'''
    r = sh([py, "-c", code], cwd=template, env=env, timeout=900)
    data = json.loads(r.stdout.strip().splitlines()[-1])
    assert data["red"], "the mutation is not live in the template clone"
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=template)
    return sorted(data["files"].items(), key=lambda kv: -kv[1])


# One guard = the product's own packet, observer and repair loop over ONE file, at FULL SIGHT.
# `fluidfix repair --file` builds a packet capped at 110 lines, and the capped view is why the first
# lake run missed a fault on line 638 of a 294-executed-line file. A guard that owns a single
# territory can afford to read all of it — that is the whole point of sharding by file. Same laws,
# same suite, same byte-exact rollback: the harness only widens the view.
GUARD_DRIVER = """
import sys
src, rel, dictionary = sys.argv[1], sys.argv[2], sys.argv[3]
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
print(f"full sight: {len(pk.lines)} executed lines, {len(obs)} observations", flush=True)
res = repair(o, rel, obs)
print(res.summary())
raise SystemExit(0 if res.repaired else 2)
"""


def make_clone(template: Path, dest: Path):
    if dest.exists():
        return
    shutil.copytree(template, dest, symlinks=True)
    (dest / ".git" / "index.lock").unlink(missing_ok=True)
    for pth in list((dest / ".venv").rglob("*.pth")) + [dest / ".venv" / "pyvenv.cfg"]:
        if pth.name == "a1_coverage.pth" or not pth.exists():
            continue
        try:
            t = pth.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if str(template) in t:
            pth.write_text(t.replace(str(template), str(dest)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("case")
    ap.add_argument("--template", required=True); ap.add_argument("--dictionary")
    ap.add_argument("--max", type=int, default=16, help="territories to guard (most-executed first)")
    ap.add_argument("--timeout", type=int, default=420, help="wall cap per guard, seconds")
    ap.add_argument("--confirm", type=int, default=0,
                    help="seconds to keep listening after the first green, to catch a second, different program")
    a = ap.parse_args()
    repo_name, cid = a.case.split("/")
    mut = json.load(open(CASES / repo_name / cid / "mutation.json"))
    template = Path(a.template).resolve(); root = Path(a.root).resolve(); root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)

    t_scan = time.time()
    terr = territories(template, mut, env)[: a.max]
    scan_s = round(time.time() - t_scan, 1)
    guilty = mut["file"]
    covered = any(f == guilty for f, _ in terr)
    print(f"[{a.case}] {len(terr)} territories from one coverage pass ({scan_s}s); "
          f"the faulty file {guilty} is {'IN' if covered else 'NOT IN'} the set", flush=True)

    procs = {}
    t0 = time.time()
    for i, (rel, n) in enumerate(terr):
        clone = root / f"{repo_name}_t{i:02d}"
        make_clone(template, clone)
        apply_mutation(clone, mut)
        py = str(clone / ".venv" / "bin" / "python")
        cmd = [py, "-c", GUARD_DRIVER, str(SRC), rel, a.dictionary or ""]
        procs[rel] = (clone, n, time.time(), subprocess.Popen(cmd, cwd=clone, env=env, stdout=subprocess.PIPE,
                                                              stderr=subprocess.STDOUT, text=True))
    print(f"[{a.case}] {len(procs)} guards launched in parallel, one per territory, {a.timeout}s cap each", flush=True)

    # THE CONNECTION IS THE SPEED-UP: the judge watches every guard, and the first green ends the
    # search — the others are cancelled where they stand. Wall clock is then time-to-first-green,
    # not the slowest guard's give-up time. `--confirm` buys an ambiguity check: seconds to keep
    # listening after the first green, in case a second guard reports a DIFFERENT passing program.
    pending = dict(procs); first_green = None; cancelled = []
    deadline = time.time() + a.timeout
    while pending and time.time() < deadline:
        for rel, (clone, n, ts, pr) in list(pending.items()):
            if pr.poll() is None:
                continue
            del pending[rel]
            if pr.returncode == 0 and first_green is None:
                first_green = (rel, round(time.time() - t0, 1))
                print(f"  first green: {rel} at {first_green[1]}s — judge stops the rest", flush=True)
                if a.confirm:
                    deadline = min(deadline, time.time() + a.confirm)
                else:
                    deadline = time.time()
        if first_green and not a.confirm:
            break
        time.sleep(0.4)
    for rel, (clone, n, ts, pr) in pending.items():
        if pr.poll() is None:
            pr.kill(); cancelled.append(rel)

    guards = {}
    for rel, (clone, n, ts, pr) in procs.items():
        try:
            out, _ = pr.communicate(timeout=60)
            code = pr.returncode
        except subprocess.TimeoutExpired:
            pr.kill(); out, code = "TIMEOUT", 124
        if rel in cancelled:
            code = 125
        dt = round(time.time() - ts, 1)
        line = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", out or "")
        # a guard's PROGRAM is the file it rewrote plus that file's bytes
        program = None
        if code == 0:
            program = (rel, (clone / rel).read_bytes())
        head = next((l for l in (out or "").splitlines() if l.strip() and not l.startswith("dictionary ")), "")
        guards[rel] = {"executed_lines": n, "exit": code, "seconds": dt, "suite_runs": int(m.group(2)) if m else None,
                       "head": head[:200],
                       "repaired_line": int(m.group(1)) if m else None, "faulty_line_restored": line == mut["orig"],
                       "reason": (re.search(r"refused: (.*)", out or "") or [None, ""])[1][:160], "_program": program}
        flag = {0: "GREEN", 2: "refused", 3: "suite green", 124: "timeout", 125: "cancelled"}.get(code, f"exit{code}")
        print(f"  guard {rel:38} {flag:8} {dt:6.1f}s runs={guards[rel]['suite_runs']} "
              f"{'byte-exact' if guards[rel]['faulty_line_restored'] and code == 0 else ''}"
              f"{'  ' + head[:80] if code not in (0, 2) else ''}", flush=True)
    wall = round(time.time() - t0, 1)

    greens = {rel: g for rel, g in guards.items() if g["exit"] == 0}
    programs = {g["_program"] for g in greens.values()}
    if len(programs) == 1:
        rel, g = next(iter(greens.items()))
        ruling = "SHIP"; verdict = "EXACT" if g["faulty_line_restored"] else "WRONG-GREEN"
    elif len(programs) > 1:
        ruling, verdict = "AMB -> REFUSE (two guards, two different programs)", "REFUSED"
    else:
        ruling, verdict = "REFUSE (every guard's reason attached)", "REFUSED"
    res = {"case": a.case, "faulty_file": guilty, "faulty_file_covered": covered, "territories": len(terr),
           "first_green": first_green, "cancelled": cancelled, "confirm_s": a.confirm,
           "scan_s": scan_s, "wall_s": wall, "cpu_sum_s": round(sum(g["seconds"] for g in guards.values()), 1),
           "greens": sorted(greens), "distinct_programs": len(programs), "ruling": ruling, "verdict": verdict,
           "guards": {k: {kk: vv for kk, vv in v.items() if kk != "_program"} for k, v in guards.items()}}
    (HERE / f"lake_{repo_name}_{cid}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] JUDGE: {ruling} -> {verdict} | greens {sorted(greens)} | wall {wall}s "
          f"(first green {first_green[1] if first_green else '-'}s, {len(cancelled)} guards cancelled) "
          f"cpu-sum {res['cpu_sum_s']}s", flush=True)


if __name__ == "__main__":
    main()
