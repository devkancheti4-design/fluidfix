#!/usr/bin/env python3
"""The held-out REAL instances, against their actual parent-commit files.

Taught from click dce3b868 alone. Everything else here was never consulted. For each: fetch the file as it
was before the fix, find the buggy line, and ask — is the maintainer's line among this class's candidates,
and at what rank? The remine corpus ships no tests for these, so this is the knowledge question (reached +
rank), with the harness cap (8) and the product cap (32) marked."""
import json, re, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "src")); sys.path.insert(0, str(R / "research/life-fluidfix-2026-09-18"))
from life_fluidfix import shape_candidates, load_dictionary
load_dictionary(str(R / "examples/taught-2026-09-22/sibling_attribute.py"))
REPOS = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/edcc1538-5d49-421a-b582-de9456e4707c/scratchpad/repos")
rows = json.load(open(R / "research/real-history-2026-09-19/remine.json"))["rows"]
CASES = [("dce3b868", "TAUGHT"), ("f872d7a5", "held out"), ("877cd149", "held out"), ("16cd686b", "held out"),
         ("e1c105b8", "held out"), ("87528364", "held out"), ("f70eb3ca", "control: wrong RECEIVER, not attribute")]
norm = lambda s: re.sub(r"\s+", " ", s.strip())
print(f"{'':9} {'repo':6} {'':8} {'buggy line':44} {'reached':>7} {'rank':>9}  role")
print("-" * 112)
reached_held = total_held = 0
for pre, role in CASES:
    r = next(x for x in rows if x["sha"].startswith(pre))
    try:
        src = subprocess.run(["git", "-C", str(REPOS / r["repo"]), "show", f"{r['sha']}^:{r['file']}"],
                             capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        print(f"{pre:9} {r['repo']:6} {'':8} {'(parent file unavailable)':44}"); continue
    lines = src.split("\n"); want = norm(r["plus"][0]); m = norm(r["minus"][0])
    hits = [i for i, l in enumerate(lines) if norm(l) == m]
    best = None
    for i in hits:
        cands = [c for k, _n, c in shape_candidates(lines[i], i + 1, lines) if k == 4]
        for j, c in enumerate(cands):
            if norm(c) == want:
                best = (j + 1, len(cands)); break
        if best: break
    n_c = len([c for k, _n, c in shape_candidates(lines[hits[0]], hits[0] + 1, lines) if k == 4]) if hits else 0
    ok = best is not None
    if role == "held out": total_held += 1; reached_held += ok
    rank = f"{best[0]}/{best[1]}" + (" (>8)" if best and best[0] > 8 else "") if best else f"—/{n_c}"
    print(f"{pre:9} {r['repo']:6} {'':8} {m[:44]:44} {'YES' if ok else 'no':>7} {rank:>9}  {role}")
print("-" * 112)
print(f"held-out real instances reached: {reached_held}/{total_held}")
