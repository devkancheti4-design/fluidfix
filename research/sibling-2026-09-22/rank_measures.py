#!/usr/bin/env python3
"""Two ranking measures for the sibling-attribute class, scored on real commits.

v1 — as taught: FILE pool (same-receiver ∪ file defs) by string similarity, then FAMILY by similarity.
v2 — pre-registered before any fresh case was looked at: SAME-RECEIVER names by how often the file uses
     them on that receiver, then FILE-DEFINED names by how often the file uses them, then FAMILY;
     similarity breaks ties only.

The first six cases shaped the class (one taught, five held out for its first test). The ten FRESH cases
were found afterwards by scanning all 565 fixes and were not consulted while writing v2."""
import json, re, subprocess, sys, difflib
from pathlib import Path
from collections import Counter
R = Path(__file__).resolve().parents[2]
REPOS = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/edcc1538-5d49-421a-b582-de9456e4707c/scratchpad/repos")
rows = json.load(open(R / "research/real-history-2026-09-19/remine.json"))["rows"]
fresh = json.load(open(R / "research/sibling-2026-09-22/fresh.json"))
ATTR = re.compile(r"(?:\b([A-Za-z_]\w*)|[\)\]])\.([A-Za-z_]\w*)\b(?!\s*=[^=])")
FAM = {t: {n for n in dir(t) if not n.startswith("_") and callable(getattr(t, n))} for t in (dict, str, list, set)}
norm = lambda s: re.sub(r"\s+", " ", s.strip())
is_text = lambda m: m.strip().startswith(":") or (re.match(r"^[A-Z].*\.$", m.strip()) and "(" not in m)

CASES = [("dce3b868", "taught"), ("f872d7a5", "held-out 1"), ("877cd149", "held-out 1"), ("16cd686b", "held-out 1"),
         ("e1c105b8", "held-out 1"), ("87528364", "held-out 1")] + [(f[1], "FRESH") for f in fresh]

def ranks(sha_pre):
    r = next(x for x in rows if x["sha"].startswith(sha_pre))
    src = subprocess.run(["git", "-C", str(REPOS / r["repo"]), "show", f"{r['sha']}^:{r['file']}"],
                         capture_output=True, text=True).stdout
    lines = src.split("\n"); text = src
    # the changed pair: for FRESH cases, exactly the token-aligned pair the scan recorded — never re-derived
    pair = None
    fr = next((f for f in fresh if f[1] == sha_pre), None)
    if fr:
        _repo, _sha, _file, m, p, wrong, right = fr
        recv = next((x.group(1) for x in ATTR.finditer(m) if x.group(2) == wrong), None)
        pair = (m, recv, wrong, right)
    for m in ([] if pair else r["minus"]):
        for p in r["plus"]:
            a, b = list(ATTR.finditer(m)), list(ATTR.finditer(p))
            if len(a) == len(b):
                d = [(x, y) for x, y in zip(a, b) if x.group(2) != y.group(2)]
                if len(d) == 1 and norm(m) != norm(p):
                    pair = (m, d[0][0].group(1), d[0][0].group(2), d[0][1].group(2)); break
        if pair: break
    if not pair: return None
    line, recv, wrong, right = pair
    sim = lambda c: -difflib.SequenceMatcher(None, wrong, c).ratio()
    defs = {d for d in re.findall(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", text, re.M) if not d.startswith("__")}
    on_recv = Counter(a for a in re.findall(r"\b" + re.escape(recv) + r"\.([A-Za-z_]\w*)", text)
                      if not a.startswith("__")) if recv else Counter()
    on_recv.pop(wrong, None)
    file_defs = defs if (wrong in defs or recv in ("self", "cls")) else set()
    file_defs = {d for d in file_defs if d != wrong}
    in_file = Counter(re.findall(r"\.([A-Za-z_]\w*)\b", text))
    family = set().union(*(f for f in FAM.values() if wrong in f)) - {wrong}
    # v1: merged file pool by similarity, then family by similarity
    v1 = sorted(set(on_recv) | file_defs, key=sim) + sorted(family - set(on_recv) - file_defs, key=sim)
    # v2: same-receiver by count, file-defined by count, family by similarity
    tierA = sorted(on_recv, key=lambda c: (-on_recv[c], sim(c)))
    tierB = sorted(file_defs - set(on_recv), key=lambda c: (-in_file[c], sim(c)))
    tierC = sorted(family - set(on_recv) - file_defs, key=sim)
    v2 = tierA + tierB + tierC
    pool = set(v1)
    rk = lambda lst: (lst.index(right) + 1) if right in lst else None
    return dict(repo=r["repo"], line=line.strip(), wrong=wrong, right=right, pool=len(pool),
                v1=rk(v1), v2=rk(v2), text=bool(is_text(line)))

print(f"{'sha':9} {'repo':7} {'wrong -> right':30} {'pool':>4} {'v1':>4} {'v2':>4}  role")
print("-" * 92)
tally = {}
for pre, role in CASES:
    d = ranks(pre)
    if not d: print(f"{pre:9} (no aligned attribute pair)"); continue
    tag = role + (" · docstring" if d["text"] else "")
    f = lambda v: "—" if v is None else str(v)
    print(f"{pre:9} {d['repo'][:7]:7} {(d['wrong']+' -> '+d['right'])[:30]:30} {d['pool']:>4} {f(d['v1']):>4} {f(d['v2']):>4}  {tag}")
    grp = "fresh" if role == "FRESH" else ("taught" if role == "taught" else "held-out 1")
    t = tally.setdefault(grp, Counter()); t["n"] += 1
    for v in ("v1", "v2"):
        for cap in (8, 32):
            if d[v] is not None and d[v] <= cap: t[f"{v}@{cap}"] += 1
    if d["v1"] is not None: t["in pool"] += 1
print("-" * 92)
print(f"{'group':12} {'n':>3} {'in pool':>8} {'v1 ≤8':>6} {'v2 ≤8':>6} {'v1 ≤32':>7} {'v2 ≤32':>7}")
for g in ("taught", "held-out 1", "fresh"):
    t = tally.get(g, Counter())
    print(f"{g:12} {t['n']:>3} {t['in pool']:>8} {t['v1@8']:>6} {t['v2@8']:>6} {t['v1@32']:>7} {t['v2@32']:>7}")
