#!/usr/bin/env python
"""Third-round mutation sites (agent 17, continuation run).

pick_alt.py only offered sites on executed lines that sat inside an `if (`,
carried a 0.5f literal, or began a float/b2Vec2 declaration.  Nine files were
therefore left with 0 or too-few alternates.  This widens the site grammar --
still strictly ONE token per site, still only on lines the pristine suite
actually executed (full_cov_pristine.json) -- so that files never yet turned
red get a fair chance:

  comparison direction   <  ><  >   <= > <   >= > >
  boolean operator       && > ||
  additive flip          +  <>  -   on any executed statement line

Files chosen by hand on the command line; results go to alt_defects2.json,
which retry2.py reads with its optional second argument.

Run:  .venv/bin/python pick_alt2.py src/foo.c src/bar.c ...
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "box2d")
cov = json.load(open(os.path.join(HERE, "full_cov_pristine.json")))

# skip lines where a single-token flip is overwhelmingly likely to be an
# out-of-bounds crash (no named failing test -> nothing for SIGHT to rank)
# or a no-op (comments, format strings, loop counters).
BAD = re.compile(r"B2_ASSERT|//|/\*|\*/|printf|snprintf|\bfor\s*\(|\+\+|--|\"|^\s*#|sizeof|"
                 r"NULL|malloc|alloc|free\(|memcpy|memset|B2_VALIDATE|return;")
IDXY = re.compile(r"\b\w*(?:[Ii]ndex|Id|Key|Count|count|capacity|Capacity)\w*\s*\]")

FLIPS = [(" <= ", " < "), (" >= ", " > "), (" < ", " > "), (" > ", " < "),
         (" && ", " || "), (" + ", " - "), (" - ", " + ")]


def sites_for(rel, cap=8):
    path = os.path.join(ROOT, rel)
    lines = open(path, encoding="utf-8").read().split("\n")
    execd = sorted(set(cov.get(rel, [])))
    out, seen_lines = [], set()
    # pass 1: comparisons and booleans inside a condition
    for ln in execd:
        if ln > len(lines) or ln in seen_lines:
            continue
        t = lines[ln - 1]
        if BAD.search(t) or IDXY.search(t):
            continue
        if not re.search(r"\b(?:if|while)\s*\(|\?", t):
            continue
        for old, new in FLIPS[:5]:
            if t.count(old) == 1:
                out.append({"file": rel, "line": ln, "old": old, "new": new, "text": t.strip()})
                seen_lines.add(ln)
                break
        if len(out) >= cap:
            return out
    # pass 2: additive flips on plain statement lines
    for ln in execd:
        if ln > len(lines) or ln in seen_lines:
            continue
        t = lines[ln - 1]
        if BAD.search(t) or IDXY.search(t) or "=" not in t:
            continue
        for old, new in FLIPS[5:]:
            if t.count(old) == 1:
                out.append({"file": rel, "line": ln, "old": old, "new": new, "text": t.strip()})
                seen_lines.add(ln)
                break
        if len(out) >= cap:
            return out
    return out


if __name__ == "__main__":
    p = os.path.join(HERE, "alt_defects2.json")
    out = json.load(open(p)) if os.path.exists(p) else {}
    for rel in sys.argv[1:]:
        out[rel] = sites_for(rel)
        print(f"{rel:26s} {len(out[rel])} sites: " +
              "; ".join(f"L{s['line']} {s['old'].strip()}->{s['new'].strip()}" for s in out[rel]))
    json.dump(out, open(p, "w"), indent=1)
