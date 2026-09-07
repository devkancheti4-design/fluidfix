#!/usr/bin/env python
"""Alternate single-token sites for files whose first mutation left the suite
green. Priority: `if (... < ...)` direction flips, float literal 0.5f->0.25f,
then + / - flips on float lines. Executed lines only (pristine coverage).
Writes alt_defects.json: {file: [sites...]}."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "box2d")
cov = json.load(open(os.path.join(HERE, "full_cov_pristine.json")))
latest = {}
for line in open(os.path.join(HERE, "results.jsonl")):
    r = json.loads(line); latest[r["file"]] = r
files = [f for f, r in latest.items() if r["status"] == "green"]
BAD = re.compile(r"B2_ASSERT|//|/\*|printf|\bfor\s*\(|\+\+|\"|#|sizeof|NULL|Index|index|Id\b|Key\b|data [-+]|\+ 0;|\+ 1;|\+ 1,|B2_VALIDATE")
out = {}
for rel in files:
    lines = open(os.path.join(ROOT, rel), encoding="utf-8").read().split("\n")
    execd = sorted(set(cov.get(rel, [])))
    sites = []
    def add(ln, old, new):
        t = lines[ln - 1]
        if t.count(old) == 1 and not BAD.search(t) and len(sites) < 6:
            sites.append({"file": rel, "line": ln, "old": old, "new": new, "text": t.strip()})
    for ln in execd:
        t = lines[ln - 1]
        if re.search(r"\bif\s*\(", t):
            if " < " in t: add(ln, " < ", " > ")
            elif " > " in t: add(ln, " > ", " < ")
    for ln in execd:
        if "0.5f" in lines[ln - 1]: add(ln, "0.5f", "0.25f")
    for ln in execd:
        t = lines[ln - 1]
        if re.match(r"^\s*(?:float|b2Vec2)\s", t):
            if " + " in t: add(ln, " + ", " - ")
            elif " - " in t: add(ln, " - ", " + ")
    prev = {(latest[rel]["line"], latest[rel]["old"])}
    out[rel] = [s for s in sites if (s["line"], s["old"]) not in prev]
    print(f"{rel:24s} {len(out[rel])} alternates: " + "; ".join(f"L{s['line']} {s['old'].strip()}->{s['new'].strip()}" for s in out[rel]))
json.dump(out, open(os.path.join(HERE, "alt_defects.json"), "w"), indent=1)
