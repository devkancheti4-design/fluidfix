#!/usr/bin/env python3
"""Render RESULT.md from the measurement files in this directory. Re-run as data lands.
Every number in the tables comes from a JSON written by the harness that measured it."""
import json, re, statistics
from glob import glob
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(p):
    p = HERE / p
    return json.load(open(p)) if p.exists() else None


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def scale_section():
    d = load("scale_results.json")
    if not d: return "_not run_"
    rs = d["results"]; walls = sorted(r["wall_s"] for r in rs); locs = sorted(r["localise_s"] for r in rs)
    rows = [(r["file"], r["kind"], r["rank_of_true_file"], r["localise_s"], r["suite_runs"], r["wall_s"], "yes" if r["byte_exact"] else "NO") for r in rs]
    tally = (f"Synthetic package: {d['n_files']} source files, {d['n_tests']} tests, green suite {d['suite_s']} s, seed {d['seed']}. "
             f"True file ranked first in {sum(r['rank_of_true_file']==1 for r in rs)}/{len(rs)} cases; "
             f"byte-exact repair in {sum(r['byte_exact'] and r['status']=='repaired' for r in rs)}/{len(rs)}; "
             f"localisation {locs[0]}–{locs[-1]} s; repair wall-clock median {walls[len(walls)//2]} s (min {walls[0]}, max {walls[-1]}).")
    return tally + "\n\n" + md_table(["file", "injected fault (shipped kind)", "rank of true file", "localise s", "suite runs", "wall s", "byte-exact"], rows)


def bench_section():
    rs = load("bench_real_results.json")
    if not rs: return "_bench_real.py has not written results yet_"
    out = []
    for repo in dict.fromkeys(r["repo"] for r in rs):
        trials = [r for r in rs if r["repo"] == repo and "meta" not in r]
        scans = [r for r in rs if r["repo"] == repo and r.get("meta") == "scan"]
        hung = [r for r in rs if r["repo"] == repo and r.get("meta") == "hung"]
        scan_line = ", ".join(f"{s['cls']} {s['live']} live of {s['attempts']} tried" for s in scans)
        rows = [(r["id"], "in" if r["in_vocab"] else "OOV", f"`{r['file']}:{r['lineno']}`", f"`{r['orig'][:48]}` → `{r['mutated'][:48]}`",
                 r["verdict"], r["seconds"], r["suite_runs"] if r["suite_runs"] is not None else "-") for r in trials]
        out.append(f"### {repo}\n\nScans: {scan_line or 'in progress'}." + (f" Mutants that hung the suite and were skipped: {len(hung)}." if hung else "") + "\n\n"
                   + md_table(["case", "vocab", "site", "mutation", "verdict", "seconds", "suite runs"], rows))
    trials = [r for r in rs if "meta" not in r]; iv = [r for r in trials if r["in_vocab"]]; ov = [r for r in trials if not r["in_vocab"]]
    def cnt(xs, v): return sum(x["verdict"] == v for x in xs)
    summ = md_table(["", "live trials", "byte-exact", "wrong-green", "refused", "no-action"],
                    [("in-vocabulary", len(iv), cnt(iv, "EXACT"), cnt(iv, "WRONG-GREEN"), cnt(iv, "REFUSED"), cnt(iv, "NO-ACTION")),
                     ("out-of-vocabulary", len(ov), cnt(ov, "EXACT"), cnt(ov, "WRONG-GREEN"), cnt(ov, "REFUSED"), cnt(ov, "NO-ACTION"))])
    ex = [r["seconds"] for r in iv if r["verdict"] == "EXACT"]
    if ex: summ += f"\n\nIn-vocabulary byte-exact repairs: median {statistics.median(ex):.0f} s, min {min(ex)}, max {max(ex)} s."
    return summ + "\n\n" + "\n\n".join(out)


def rerun_section():
    rows = []
    for p in sorted(glob(str(HERE / "cases" / "*" / "*" / "rerun_budget*.json"))):
        if "_taught" in Path(p).name: continue          # the taught replays are §6's table
        r = json.load(open(p)); r["extra"] = re.sub(r"--dictionary \S*/", "--dictionary ", r.get("extra", "")); rows.append((r["case"], r.get("code", "source tree"), f'{r["budget"]}{(" " + r["extra"]) if r.get("extra") else ""}', r["verdict"], r["seconds"], r["suite_runs"] or "-", r["rejected"] if r["rejected"] is not None else "-", r["hint"][:90]))
    return md_table(["case", "code", "budget s (+flags)", "verdict", "seconds", "suite runs", "candidates rejected", "guard's hint"], rows) if rows else "_none_"


def ladder_section():
    files = sorted(glob(str(HERE / "ladder_*.json")))
    if not files: return "_no ladder runs yet_"
    out = []
    for f in files:
        rs = json.load(open(f)); label = rs[0]["author"] if rs else Path(f).stem
        if "packetv1" in Path(f).stem: label += " — packet v1 (superseded: the packet never contained the defect line)"
        if label.startswith("fable"): label += " — in-session author who had seen the bench log before authoring: an upper bound, not a blind measurement; tokens are characters/4"
        rows = []
        for r in sorted(rs, key=lambda x: x["case"]):
            tk = r.get("tokens") or {}; tiers = r.get("tiers") or []
            reached = max((t["tier"] for t in tiers), default=0)
            t1 = next((t for t in tiers if t["tier"] == 1), {}); why = t1.get("why", "")
            rows.append((r["case"], r["cls"], reached, r["verdict"], tk.get("input", "-"), tk.get("output", "-"), tk.get("total", "-"), r["wall_s"], why[:60]))
        n = len(rs); ex = sum(r["verdict"] == "EXACT" for r in rs); wg = sum(r["verdict"] == "WRONG-GREEN" for r in rs)
        tot = [ (r.get("tokens") or {}).get("total", 0) for r in rs]
        out.append(f"### author: {label}\n\n{ex}/{n} byte-exact, {wg} wrong-green, {n-ex-wg} refused; tokens per case median {statistics.median(tot) if tot else 0:.0f}, total {sum(tot)}.\n\n"
                   + md_table(["case", "class", "tier reached", "verdict", "tokens in", "tokens out", "tokens total", "wall s", "tier-1 rule check"], rows))
    return "\n\n".join(out)


def taught_section():
    """Teach once by hand (no model), judged zero-token on the same class elsewhere."""
    teach = {"click/andor-1", "click/getdef-1", "click/notdrop-1", "click/lenm1-1", "python-sortedcontainers/rangestart-1"}
    rows = []
    for p in sorted(glob(str(HERE / "cases" / "*" / "*" / "rerun_budget*_taught.json"))):
        r = json.load(open(p)); case = r["case"]; mut = json.load(open(Path(p).parent / "mutation.json")); cls = mut["cls"]
        found = "-"
        if r["verdict"] == "REFUSED":
            rp = Path(p).parent / p.split("rerun_budget")[1].replace(".json", "").join(["refusal_rerun", ".json"])
            if rp.exists():
                rej = json.load(open(rp)).get("rejected_candidates", [])
                at = [c for c in rej if c["at"].endswith(f":{mut['lineno']}") and c["tried"].strip() == mut["orig"].strip()]
                found = ("correct line tried and REJECTED by the suite" if at else
                         "correct line not among the rejected; guard reports a passing candidate held by CAPPED" if "candidate passes" in r["hint"] else "true line not reached")
        rows.append((case, cls, "teaching example" if case in teach else "held-out (another repo)", r["verdict"], r["seconds"], r["suite_runs"] or "-", r["budget"], found, r["hint"][:70]))
    if not rows: return "_not run_"
    held = [r for r in rows if r[2].startswith("held")]; ex = sum(r[3] == "EXACT" for r in held); wg = sum(r[3] == "WRONG-GREEN" for r in held)
    tex = [r for r in rows if not r[2].startswith("held")]
    head = (f"Teaching examples restored: {sum(r[3]=='EXACT' for r in tex)}/{len(tex)}. Held-out cases (same class, another repo, zero tokens): "
            f"{ex}/{len(held)} byte-exact, {wg} wrong-green, {len(held)-ex-wg} refused.")
    return head + "\n\n" + md_table(["case", "class", "role", "verdict", "seconds", "suite runs", "budget s", "on refusal: was the correct line found?", "guard's hint"], rows)


def shards_section():
    files = sorted(glob(str(HERE / "shards" / "judge_*.json")))
    if not files: return "_not run_"
    rows = []
    for f in files:
        r = json.load(open(f)); rep, cid = r["case"].split("/")
        serial = None
        for cand in (HERE / "cases" / rep / cid / "rerun_budget900_taught.json", HERE / "cases" / rep / cid / "refusal_tier0.json"):
            if cand.exists(): serial = json.load(open(cand)); break
        s_txt = f'{serial.get("verdict", "REFUSED")} in {round(serial.get("seconds", 0))} s' if serial else "-"
        rows.append((r["case"], r["file"], r["guards"], r["ruling"], r["verdict"], r["wall_s"], r["cpu_sum_s"], ",".join(map(str, r["greens"])) or "-", r["distinct_programs"], ",".join(map(str, r["held"])) or "-", s_txt))
    return md_table(["case", "file", "guards", "judge's ruling", "verdict", "wall s (slowest guard)", "cpu-sum s", "green guards (kind)", "distinct programs", "held guards", "serial guard, same dictionary"], rows)


def main():
    body = (HERE / "RESULT_prose.md").read_text() if (HERE / "RESULT_prose.md").exists() else "# LLM fusion — measured (2026-09-16)\n\n{scale}\n\n{bench}\n\n{rerun}\n\n{ladder}\n"
    (HERE / "RESULT.md").write_text(body.format(scale=scale_section(), bench=bench_section(), rerun=rerun_section(), ladder=ladder_section(), taught=taught_section(), shards=shards_section()))
    print("wrote RESULT.md")


if __name__ == "__main__":
    main()
