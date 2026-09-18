#!/usr/bin/env python3
"""Not waves — a net that grows from the work, deeper and wider, one fluidfix per node.

`staged.py` dispatches two fixed waves: the remembered class, then everything else. That plan is made
before any work is done, so it is the same plan whether the first node learns something or nothing.

A net instead GROWS, and the law already says in which direction. Every refusal a fluidfix returns carries
its ruling:

    REFUTED   every candidate this node generated was rejected by the suite — the fault is not here
              in this class, so the net grows WIDER: the next class in this territory, the next territory
    CAPPED    a candidate passed but the view was cut short, or the clock ran out with the failure still
              pointing here — the fault may well be here, so the net grows DEEPER: split this node's
              line range in two and give each half its own fluidfix

Each node is one small fluidfix over (territory, class, line range), and each node's verdict decides what
the net spawns next. The first green ends everything. Growth is bounded by a node budget, and when the net
stops growing without a green it says so rather than pretending the search was complete.

  PYTHONPATH=<fluidfix>/src python3 net.py <clones-root> rich/notdrop-1 --template <clone> \\
      --dictionary <rules.py> [--max-nodes 48] [--width 8] [--cold]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from life import Life                                                     # noqa: E402
from recursive import SURVEY, CASES, SRC, sh, apply_mutation, make_clone   # noqa: E402

MEMORY = HERE / "net_memory.json"

# one node: one territory, one class, one line range. Full sight inside the range.
NODE = """
import sys
src, rel, dictionary, kind, lo, hi = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
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
    print("RULING=GREEN-ALREADY"); raise SystemExit(3)
pk = build_packet(o, rel, max_lines=10 ** 9)
if pk is None:
    print("RULING=NO-PACKET"); raise SystemExit(3)
obs = rank_observations("\\n".join(pk.src_lines), MechanicalObserver().observe([pk])[0], out, root=".", rel=rel)
mine = []
for x in obs:
    if kind in x.kinds and lo <= x.lineno <= hi:
        x.kinds = [kind]
        mine.append(x)
print(f"observations={len(mine)}")
if not mine:
    print("RULING=EMPTY"); raise SystemExit(2)
res = repair(o, rel, mine)
print(f"suite_runs={res.suite_runs}")
print(f"RULING={'SHIP' if res.repaired else (res.ruling or 'REFUTED')}")
print(f"capped={bool(res.capped)}  greens={len(res.greens or [])}")
print(res.summary())
raise SystemExit(0 if res.repaired else 2)
"""


def grow_direction(out: str) -> str:
    """The law's own ruling, read back: what this node learned decides what the net spawns."""
    if "RULING=SHIP" in out:
        return "done"
    if "RULING=EMPTY" in out:
        return "wider"            # nothing here can even exhibit this class
    if "capped=True" in out or "RAISE_BUDGET" in out or "greens=1" in out:
        return "deeper"           # something passed, or the view was cut short: look closer here
    return "wider"                # REFUTED: every candidate rejected, the fault is not in this node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("case"); ap.add_argument("--template", required=True)
    ap.add_argument("--dictionary"); ap.add_argument("--max-nodes", type=int, default=48)
    ap.add_argument("--width", type=int, default=8, help="nodes launched per round")
    ap.add_argument("--fanout", type=int, default=1,
                    help="on a refutation, how many further territories to open at once. A node is cheap "
                         "(measured: 32 at once stay byte-exact, 5.1x slower each on 12 cores), so the "
                         "limit is the machine, not the design")
    ap.add_argument("--timeout", type=int, default=420); ap.add_argument("--cold", action="store_true")
    a = ap.parse_args()
    repo_name, cid = a.case.split("/")
    mut = json.load(open(CASES / repo_name / cid / "mutation.json"))
    template = Path(a.template).resolve(); root = Path(a.root).resolve(); root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
    if a.cold:
        MEMORY.unlink(missing_ok=True)
    life = Life(str(MEMORY))

    t_s = time.time()
    apply_mutation(template, mut, commit=False)
    r = sh([str(template / ".venv" / "bin" / "python"), "-c", SURVEY, str(SRC), a.dictionary or ""],
           cwd=template, env=env, timeout=900)
    survey = json.loads(r.stdout.strip().splitlines()[-1])
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=template)
    files = sorted(survey["files"].items(), key=lambda kv: -kv[1]["executed"])
    nlines = {rel: len((template / rel).read_text(encoding="utf-8", newline="").split("\n")) for rel, _ in files}
    remembered = [int(v.split(":")[1]) for v, _c in reversed(life.history("shapes")) if v.startswith("kind:")]
    print(f"[{a.case}] survey {round(time.time() - t_s, 1)}s: {len(files)} territories; "
          f"memory knows {remembered or 'nothing'}; every (territory, class) pair here would be "
          f"{sum(len(i['kinds']) for _r, i in files)} nodes", flush=True)

    # ---- the seed: the smallest thing worth trying, not a plan for the whole search
    seeds = []
    for k in (remembered[:1] or [sorted(files[0][1]["kinds"].items(), key=lambda kv: kv[1])[0][0]]):
        for rel, info in files:
            if int(k) in {int(x) for x in info["kinds"]}:
                seeds.append((rel, int(k), 1, nlines[rel]))
                break
    if not seeds:
        rel, info = files[0]
        seeds = [(rel, int(sorted(info["kinds"].items(), key=lambda kv: kv[1])[0][0]), 1, nlines[rel])]

    frontier, done, nodes, rounds = list(seeds), {}, 0, 0
    winner = None
    t0 = time.time()
    while frontier and winner is None and nodes < a.max_nodes:
        rounds += 1
        batch, frontier = frontier[: a.width], frontier[a.width:]
        batch = [b for b in batch if b not in done]
        if not batch:
            continue
        procs = {}
        for i, (rel, k, lo, hi) in enumerate(batch):
            clone = root / f"{repo_name}_n{(nodes + i) % 24:02d}"
            make_clone(template, clone); apply_mutation(clone, mut)
            py = str(clone / ".venv" / "bin" / "python")
            procs[(rel, k, lo, hi)] = (clone, time.time(), subprocess.Popen(
                [py, "-c", NODE, str(SRC), rel, a.dictionary or "", str(k), str(lo), str(hi)],
                cwd=clone, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
        nodes += len(batch)
        print(f"  round {rounds}: {len(batch)} node(s) — " +
              ", ".join(f"{Path(r).name}:{k}[{lo}-{hi}]" for r, k, lo, hi in batch), flush=True)

        grew_deeper = grew_wider = 0
        for key, (clone, ts, pr) in procs.items():
            try:
                out, _ = pr.communicate(timeout=a.timeout); code = pr.returncode
            except subprocess.TimeoutExpired:
                pr.kill(); out, code = "RULING=CAPPED timeout", 124
            rel, k, lo, hi = key
            runs = re.search(r"suite_runs=(\d+)", out or "")
            line = (clone / mut["file"]).read_text(encoding="utf-8", newline="").split("\n")[mut["lineno"] - 1]
            direction = grow_direction(out or "")
            done[key] = {"exit": code, "seconds": round(time.time() - ts, 1),
                         "suite_runs": int(runs.group(1)) if runs else 0, "grew": direction,
                         "byte_exact": code == 0 and line == mut["orig"]}
            if code == 0:
                winner = key
                print(f"    green: {rel} class {k} lines {lo}-{hi} "
                      f"({done[key]['suite_runs']} suite runs) — the net stops growing", flush=True)
                break
            if direction == "deeper" and hi - lo > 40:
                mid = (lo + hi) // 2
                frontier = [(rel, k, lo, mid), (rel, k, mid + 1, hi)] + frontier      # depth first
                grew_deeper += 2
            else:
                # a refutation is evidence about a whole territory-class pair, so spend it widely:
                # every class this territory can still exhibit, and this class in the next few territories
                kinds_here = sorted({int(x) for _r, i in files for x in i["kinds"] if _r == rel})
                nxt = [(rel, kk, 1, nlines[rel]) for kk in kinds_here
                       if (rel, kk, 1, nlines[rel]) not in done and kk != k]
                other = [(r2, k, 1, nlines[r2]) for r2, i2 in files
                         if k in {int(x) for x in i2["kinds"]} and (r2, k, 1, nlines[r2]) not in done]
                # a remembered class is evidence about the CLASS, not about this territory: spend a
                # refusal on the same class elsewhere before opening other classes here. Measured
                # 2026-09-18: with the common `if x:` class remembered, opening other classes first
                # turned a warm search back into a cold one (129 nodes), because 12 territories can
                # exhibit it while arrow's scarcer class lived in exactly one.
                if k in remembered:
                    add = other[: max(a.fanout * 3, 6)] + nxt[:1]
                else:
                    add = nxt[: a.fanout] + other[: a.fanout]
                frontier += [x for x in add if x not in frontier]
                grew_wider += len(add)
        if winner is None:
            print(f"    grew: {grew_deeper} deeper, {grew_wider} wider — frontier now {len(frontier)}",
                  flush=True)

    wall = round(time.time() - t0, 1)
    runs = sum(g["suite_runs"] for g in done.values())
    verdict = ("EXACT" if winner and done[winner]["byte_exact"] else
               "WRONG-GREEN" if winner else ("EXHAUSTED" if not frontier else "BUDGET"))
    if verdict == "EXACT":
        life.learn("shapes", f"kind:{winner[1]}"); life.save()
    res = {"case": a.case, "rounds": rounds, "nodes": nodes, "suite_runs": runs, "wall_s": wall,
           "verdict": verdict, "winner": list(winner) if winner else None,
           "winner_runs": done[winner]["suite_runs"] if winner else None,
           "every_pair_would_be": sum(len(i["kinds"]) for _r, i in files),
           "grew_deeper": sum(1 for g in done.values() if g["grew"] == "deeper"),
           "memory_before": remembered, "nodes_detail": {f"{r}|{k}|{lo}-{hi}": v for (r, k, lo, hi), v in done.items()}}
    (HERE / f"net_{repo_name}_{cid}.json").write_text(json.dumps(res, indent=1))
    print(f"[{a.case}] {verdict} | {nodes} nodes over {rounds} rounds (every pair would be "
          f"{res['every_pair_would_be']}) | {runs} suite runs | {wall}s", flush=True)


if __name__ == "__main__":
    main()
