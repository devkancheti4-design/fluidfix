#!/usr/bin/env python3
"""Key the memory on the SHAPE, not on the signature — so a new incident of a known class is cheap too.

`recursive.py` keys the judge's Life on the failure signature: repo + failing test. That makes the second
occurrence of the SAME incident cost one fluidfix instead of forty-five, which is an exact-key lookup and
nothing more. It cannot help a fault that has never been seen before, because a new fault has a new key.

The shapes are the part of fluidfix that generalises: a class is a signal plus a transform, so it fires on
lines it has never seen. So put the SHAPE in the memory and dispatch in waves:

    wave 1   the classes that have answered before, across only the territories that can exhibit them
    wave 2   everything else — every remaining (territory, class) pair

Coverage is never lost: a wave-1 miss widens into the full fan-out, which is what the cold run would have
dispatched anyway. What changes is the common case, and it generalises — the key is the class, not the
incident, so a fault in a file never seen before still lands in wave 1 when its class is known.

  PYTHONPATH=<fluidfix>/src python3 staged.py <clones-root> arrow/lenm1-1 --template <clone> \\
      --dictionary <rules.py> [--territories 8] [--classes 2] [--cold]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from life import Life                                                     # noqa: E402
from recursive import DRIVER, SURVEY, CASES, SRC, sh, apply_mutation, make_clone, launch   # noqa: E402

MEMORY = HERE / "shape_memory.json"


def run_wave(plan, template, root, repo_name, mut, dictionary, env, timeout, label, offset=0):
    """Launch one wave, stop it at the first green, and report what each guard did."""
    if not plan:
        return {}, None, 0.0, []
    procs = {}
    t0 = time.time()
    for i, (rel, k) in enumerate(plan):
        clone = root / f"{repo_name}_t{offset + i:02d}"
        make_clone(template, clone)
        apply_mutation(clone, mut)
        procs[(rel, k)] = (clone, time.time(), launch(clone, rel, k, dictionary, env))
    print(f"  {label}: {len(plan)} fluidfix{'' if len(plan) == 1 else 'es'} "
          f"({', '.join(sorted({str(k) for _r, k in plan}))} as the class)", flush=True)

    pending = dict(procs); first_green = None; cancelled = []
    deadline = time.time() + timeout
    while pending and time.time() < deadline:
        for key, (clone, ts, pr) in list(pending.items()):
            if pr.poll() is None:
                continue
            del pending[key]
            if pr.returncode == 0 and first_green is None:
                first_green = (key, round(time.time() - t0, 1))
                print(f"    first green: {key[0]} kind {key[1]} at {first_green[1]}s", flush=True)
                deadline = time.time()
        if first_green:
            break
        time.sleep(0.3)
    for key, (clone, ts, pr) in pending.items():
        if pr.poll() is None:
            pr.kill(); cancelled.append(key)

    guards = {}
    for key, (clone, ts, pr) in procs.items():
        try:
            out, _ = pr.communicate(timeout=60); code = pr.returncode
        except subprocess.TimeoutExpired:
            pr.kill(); out, code = "TIMEOUT", 124
        if key in cancelled:
            code = 125
        line = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
        m = re.search(r"repaired line (\d+) in (\d+) suite runs", out or "")
        rr = re.search(r"suite_runs=(\d+)", out or "")
        guards[f"{key[0]}|{key[1]}"] = {
            "wave": label, "exit": code, "seconds": round(time.time() - ts, 1),
            "suite_runs": int(m.group(2)) if m else (int(rr.group(1)) if rr else 0),
            "byte_exact": code == 0 and line == mut["orig"]}
    wall = round(time.time() - t0, 1)
    winner = next((k for k, g in guards.items() if g["exit"] == 0), None)
    return guards, winner, wall, cancelled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("case"); ap.add_argument("--template", required=True)
    ap.add_argument("--dictionary"); ap.add_argument("--territories", type=int, default=8)
    ap.add_argument("--classes", type=int, default=2, help="how many remembered classes wave 1 may try")
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--cold", action="store_true", help="empty the shape memory first")
    a = ap.parse_args()
    repo_name, cid = a.case.split("/")
    mut = json.load(open(CASES / repo_name / cid / "mutation.json"))
    template = Path(a.template).resolve(); root = Path(a.root).resolve(); root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    if a.cold:
        MEMORY.unlink(missing_ok=True)
    life = Life(str(MEMORY))

    # ---- one survey: what the failing test executed, and which classes each file can exhibit
    t_s = time.time()
    apply_mutation(template, mut, commit=False)
    r = sh([str(template / ".venv" / "bin" / "python"), "-c", SURVEY, str(SRC), a.dictionary or ""],
           cwd=template, env=env, timeout=900)
    survey = json.loads(r.stdout.strip().splitlines()[-1])
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=template)
    survey_s = round(time.time() - t_s, 1)

    # ---- the memory is keyed by SHAPE, so a brand-new incident can still hit it
    prior = [int(v.split(":")[1]) for v, _c in reversed(life.history("shapes")) if v.startswith("kind:")]
    prior = prior[: a.classes]
    files = sorted(survey["files"].items(), key=lambda kv: -kv[1]["executed"])[: a.territories]
    wave1 = [(rel, k) for k in prior for rel, info in files if k in {int(x) for x in info["kinds"]}]
    wave2 = [(rel, int(k)) for rel, info in files for k in info["kinds"] if (rel, int(k)) not in wave1]
    full = len(wave1) + len(wave2)
    print(f"[{a.case}] survey {survey_s}s: {len(survey['files'])} files executed; "
          f"shape memory knows {prior or 'nothing'}; a cold fan-out here would be {full} fluidfixes", flush=True)

    t0 = time.time()
    g1, w1, wall1, c1 = run_wave(wave1, template, root, repo_name, mut, a.dictionary, env, a.timeout,
                                 "wave 1 (remembered shape)")
    guards = dict(g1); winner, waves = w1, 1
    g2 = {}
    if not winner:
        if wave1:
            print("    wave 1 found nothing — widening, no coverage lost", flush=True)
        g2, w2, wall2, c2 = run_wave(wave2, template, root, repo_name, mut, a.dictionary, env, a.timeout,
                                     "wave 2 (everything else)", offset=len(wave1))
        guards.update(g2); winner, waves = w2, 2 if wave1 else 1
    wall = round(time.time() - t0, 1)

    dispatched = len(guards)
    runs = sum(g["suite_runs"] or 0 for g in guards.values())
    verdict = "EXACT" if winner and guards[winner]["byte_exact"] else ("WRONG-GREEN" if winner else "REFUSED")
    if verdict == "EXACT":
        k = int(winner.rsplit("|", 1)[1])
        life.learn("shapes", f"kind:{k}")              # the SHAPE is what is remembered
        life.learn(f"shape:{k}:where", winner.rsplit("|", 1)[0])
        life.save()
    res = {"case": a.case, "survey_s": survey_s, "shape_prior": prior, "wave1": len(wave1), "wave2": len(wave2),
           "full_fan_out_would_be": full, "waves_used": waves, "dispatched": dispatched, "suite_runs": runs,
           "winner": winner, "winner_runs": guards[winner]["suite_runs"] if winner else None,
           "verdict": verdict, "wall_s": wall, "cpu_sum_s": round(sum(g["seconds"] for g in guards.values()), 1),
           "memory_rows": len(life.store), "memory_bytes": len(life.dumps().encode()), "guards": guards}
    (HERE / f"staged_{repo_name}_{cid}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] {verdict} | winner {winner} in {res['winner_runs']} suite runs | "
          f"dispatched {dispatched} of a possible {full} | suite runs {runs} | wall {wall}s", flush=True)
    print(f"[{a.case}] shape memory now: {[v for v, _ in life.history('shapes')]} "
          f"({len(life.store)} rows, {res['memory_bytes']} bytes)", flush=True)


if __name__ == "__main__":
    main()
