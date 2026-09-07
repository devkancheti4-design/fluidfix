#!/usr/bin/env python
"""Widened scan: EVERY paired (removed, added) line inside fix commits, any
commit size, code files only (hotspots' _CODE/_SKIP). Pairs are formed
inside a hunk when it removes and adds the same number of lines (positional
pairing). Each pair gets the coarse one-token label and the loop replay.
READ-ONLY git. Usage: .venv/bin/python scan_pairs.py"""
import collections, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_history import (REPOS, HERE, KINDS, _FIX, _SKIP, _CODE, coarse_label,
                          observed_kinds, replay, loop_order)

def pairs(root, n=4000):
    out = subprocess.run(["git","-C",root,"log",f"-n{n}","--no-color","-p","-U0",
                          "--format=@@@%H%x1f%s"], capture_output=True, text=True,
                         errors="replace", timeout=300).stdout
    res, sha, subj, is_fix, path, code = [], None, None, False, None, False
    minus, plus = [], []
    def flush():
        if is_fix and code and minus and plus and len(minus)==len(plus):
            for o, nw in zip(minus, plus):
                res.append((sha[:10], subj, path, o, nw))
    for raw in out.split("\n"):
        if raw.startswith("@@@"):
            flush(); minus, plus = [], []
            sha, _, subj = raw[3:].partition("\x1f"); is_fix = bool(_FIX.search(subj))
            path, code = None, False; continue
        if raw.startswith("diff --git"):
            flush(); minus, plus = [], []
            path = raw.split(" b/",1)[-1]; code = path.endswith(_CODE) and not _SKIP.search(path); continue
        if raw.startswith("@@"):
            flush(); minus, plus = [], []; continue
        if raw.startswith("+++") or raw.startswith("---"): continue
        if raw.startswith("-"): minus.append(raw[1:])
        elif raw.startswith("+"): plus.append(raw[1:])
    flush()
    return res

def main():
    LOOP = loop_order(); rows = []
    for name, root in REPOS.items():
        ps = pairs(root)
        coarse = collections.Counter(); reach = []
        for sha, subj, path, old, new in ps:
            if old.strip() == new.strip(): continue          # whitespace-only
            lab, tok = coarse_label(old, new); coarse[lab] += 1
            pos, per, win = replay(old, new, LOOP)
            r = {"repo":name,"sha":sha,"subject":subj,"file":path,"old":old,"new":new,
                 "coarse":lab,"tok":tok,"kinds_on_line":observed_kinds(old),
                 "win_kind":win,"pos_loop":pos,"per":per}
            rows.append(r)
            if win is not None: reach.append(r)
        print(f"=== {name}: {len(ps)} paired -/+ lines in fix commits ===")
        print("coarse labels:", dict(coarse.most_common()))
        print(f"reachable by a shipped class: {len(reach)}")
        print("winning class frequency:", collections.Counter(KINDS[r['win_kind']][0] for r in reach).most_common())
        # distinct commits among reachable
        print("distinct fix commits among reachable:", len({r['sha'] for r in reach}))
    reach = [r for r in rows if r["win_kind"] is not None]
    print("\n=== replay on the defect line, reachable pairs ===")
    print(f"{'repo':6} {'sha':10} {'coarse':13} {'win kind':28} {'kinds':18} {'loop':>5} {'best':>5} {'recurLOO':>8}  old => new")
    tot = collections.Counter()
    for r in reach:
        same = [q for q in reach if q["repo"]==r["repo"] and q is not r]
        freq = collections.Counter(q["win_kind"] for q in same)
        recur = sorted(KINDS, key=lambda k: (-freq[k], k))
        pos_r,_,_ = replay(r["old"], r["new"], recur)
        best = [r["win_kind"]] + [k for k in LOOP if k != r["win_kind"]]
        pos_b,_,_ = replay(r["old"], r["new"], best)
        r["pos_recur_loo"], r["pos_best"], r["recur_order"] = pos_r, pos_b, recur
        for lab,v in (("loop",r["pos_loop"]),("recur",pos_r),("best",pos_b)): tot[(r["repo"],lab)] += v
        print(f"{r['repo']:6} {r['sha']:10} {r['coarse']:13} {KINDS[r['win_kind']][0]:28} {str(r['kinds_on_line']):18} "
              f"{r['pos_loop']:>5} {pos_b:>5} {pos_r:>8}  {r['old'].strip()[:45]} => {r['new'].strip()[:45]}")
    print("\nsuite runs on the defect line, summed over reachable pairs:")
    for repo in REPOS:
        n = sum(1 for r in reach if r["repo"]==repo)
        print(f"  {repo}: n={n} loop-order={tot[(repo,'loop')]} recurrence-order(LOO)={tot[(repo,'recur')]} winner-first(bound)={tot[(repo,'best')]}")
    ahead = collections.Counter()
    for r in reach:
        for k in r["per"]:
            if k != r["win_kind"]: ahead[KINDS[k][0]] += r["per"][k]
    print("candidates spent on NON-winning kinds ahead of the winner (loop order):", dict(ahead))
    outside = [r for r in reach if r["win_kind"] not in r["kinds_on_line"][:2]]
    print(f"reachable pairs whose winning kind is outside kinds[:2] (CHEAP slice): {len(outside)} of {len(reach)}")
    # one-token pairs NOT reachable: which labels?
    miss = collections.Counter(r["coarse"] for r in rows if r["win_kind"] is None and r["coarse"] not in ("multi-token",))
    print("one-token pairs NOT reachable by any shipped class, by label:", dict(miss.most_common()))
    json.dump(rows, open(os.path.join(HERE,"pairs_results.json"),"w"), indent=1, default=str)
    print("wrote pairs_results.json")
main()
