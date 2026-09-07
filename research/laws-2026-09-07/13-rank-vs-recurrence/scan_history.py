#!/usr/bin/env python
"""13-rank-vs-recurrence: measured class recurrence in real git histories vs
the order the body tries fault classes in, and what reordering would save.

READ-ONLY. Runs `git log -p` on the shared clones; never checks out, never
builds, never runs a suite. Every "suite run" number below is a COUNT of
candidates the loop would have to try on the defect line before reaching
the maintainer's exact fix — replaying loop.repair's own iteration order
(lanes.EMIT lowest-bit-first over the observation's kinds, acts.candidates
per kind, NOPROGRESS skip, cross-kind dedupe, 32-candidate cap) without
paying for the runs.

Usage: .venv/bin/python scan_history.py [box2d_dir] [cglm_dir]
"""
import collections
import difflib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import KINDS, Observation, act_for, candidates  # noqa: E402
from fluidfix.hotspots import _CODE, _FIX, _SKIP  # noqa: E402
from fluidfix.lanes import ADVANCE, EMIT, HALT, kind_of, mask_of  # noqa: E402

S = ("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
     "a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad")
REPOS = {"box2d": sys.argv[1] if len(sys.argv) > 1 else f"{S}/box2d",
         "cglm": sys.argv[2] if len(sys.argv) > 2 else f"{S}/cglm"}
HERE = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------- git ----
def one_line_fixes(root, n=4000):
    """[(sha, subject, file, old_line, new_line)] for fix commits (the body's
    own _FIX regex on the subject, as hotspots.bugfix_churn) whose entire
    source diff is ONE removed line and ONE added line in ONE code file."""
    out = subprocess.run(
        ["git", "-C", root, "log", f"-n{n}", "--no-color", "-p", "-U0",
         "--format=@@@%H%x1f%s"],
        capture_output=True, text=True, errors="replace", timeout=300).stdout
    fixes, scanned, nfix = [], 0, 0
    cur = None
    for raw in out.split("\n"):
        if raw.startswith("@@@"):
            if cur is not None:
                fixes.append(cur)
            sha, _, subj = raw[3:].partition("\x1f")
            scanned += 1
            is_fix = bool(_FIX.search(subj))
            nfix += is_fix
            cur = {"sha": sha, "subject": subj, "fix": is_fix,
                   "files": collections.OrderedDict(), "skip": False}
            continue
        if cur is None:
            continue
        if raw.startswith("diff --git"):
            path = raw.split(" b/", 1)[-1]
            cur["cur_file"] = path
            code = path.endswith(_CODE) and not _SKIP.search(path)
            cur["files"][path] = {"code": code, "minus": [], "plus": []}
            continue
        f = cur.get("cur_file")
        if f is None:
            continue
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("@@"):
            continue
        if raw.startswith("-"):
            cur["files"][f]["minus"].append(raw[1:])
        elif raw.startswith("+"):
            cur["files"][f]["plus"].append(raw[1:])
    if cur is not None:
        fixes.append(cur)

    keep = []
    for c in fixes:
        if not c["fix"]:
            continue
        code_files = {p: d for p, d in c["files"].items() if d["code"]}
        other = [p for p, d in c["files"].items() if not d["code"]
                 and (d["minus"] or d["plus"])]
        if len(code_files) != 1 or other:
            continue
        (path, d), = code_files.items()
        if len(d["minus"]) == 1 and len(d["plus"]) == 1:
            keep.append((c["sha"][:10], c["subject"], path,
                         d["minus"][0], d["plus"][0]))
    return keep, scanned, nfix


# ------------------------------------------------------- coarse labels ----
_TOK = re.compile(r"[A-Za-z_]\w*|\d+\.\d+[fF]?|\d+[uUlL]*|<=|>=|==|!=|&&|\|\||"
                  r"->|\+\+|--|<<|>>|[^\sA-Za-z0-9_]")
CMP = {"<", ">", "<=", ">=", "==", "!="}
LOGIC = {"&&", "||", "!", "true", "false"}


def coarse_label(old, new):
    """A one-TOKEN diff gets a coordinator-style label; else 'multi-token'."""
    a, b = _TOK.findall(old), _TOK.findall(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
    if len(ops) != 1:
        return "multi-token", None
    tag, i1, i2, j1, j2 = ops[0]
    x, y = a[i1:i2], b[j1:j2]
    if tag == "replace" and len(x) == 1 and len(y) == 1:
        p, q = x[0], y[0]
        if re.fullmatch(r"\d+[uUlL]*", p) and re.fullmatch(r"\d+[uUlL]*", q):
            pi, qi = int(re.sub(r"\D", "", p)), int(re.sub(r"\D", "", q))
            if abs(pi - qi) == 1:
                return "off-by-one", (p, q)
            return "other-literal", (p, q)
        if p in CMP and q in CMP:
            return "compare", (p, q)
        if {p, q} <= {"+", "-"} or {p, q} <= {"+=", "-="}:
            return "sign", (p, q)
        if p in LOGIC and q in LOGIC:
            return "logic", (p, q)
        if p in ("min", "max") and q in ("min", "max"):
            return "minmax", (p, q)
        return "other-token", (p, q)
    if tag in ("insert", "delete") and len(x) + len(y) == 1:
        t = (x or y)[0]
        if t == "-":
            return "sign", (tuple(x), tuple(y))
        if t == "!":
            return "logic", (tuple(x), tuple(y))
        return "other-token", (tuple(x), tuple(y))
    return "multi-token", None


# --------------------------------------------------- the loop, replayed ----
def observed_kinds(line):
    """MechanicalObserver.observe, one line."""
    return [k for k, (_, _, sig) in sorted(KINDS.items()) if sig.search(line)]


def replay(old, new, order):
    """Candidates the loop tries on this line before the exact fix, under a
    given kind ORDER (list of kind ids). Mirrors loop.repair: NOPROGRESS
    skip, cross-kind dedupe, acts.candidates' 32 cap. Returns (position or
    None, per-kind candidate counts as tried)."""
    kinds = [k for k in order if k in observed_kinds(old)]
    tried, pos, per = set(), 0, collections.OrderedDict()
    obs = Observation(lineno=1, kinds=kinds)
    for k in kinds:
        n = 0
        for cand in candidates(old, act_for(k), obs):
            if not isinstance(cand, str) or cand == old or cand in tried:
                continue
            tried.add(cand)
            pos += 1
            n += 1
            if cand.rstrip() == new.rstrip():
                per[k] = n
                return pos, per, k
        per[k] = n
    return None, per, None


def loop_order():
    """The body's actual order: lanes.EMIT lowest live bit first."""
    mask, out = mask_of(k for k in KINDS if 0 <= k <= 15), []
    while not HALT(mask):
        out.append(kind_of(EMIT(mask)))
        mask = ADVANCE(mask)
    return out


def main():
    LOOP = loop_order()
    print("loop kind order (lanes.EMIT over KINDS):",
          [(k, KINDS[k][0]) for k in LOOP])
    all_rows = []
    for name, root in REPOS.items():
        fixes, scanned, nfix = one_line_fixes(root)
        print(f"\n=== {name}: scanned {scanned} commits, {nfix} match _FIX, "
              f"{len(fixes)} are one-line/one-file source fixes ===")
        coarse = collections.Counter()
        for sha, subj, path, old, new in fixes:
            lab, tok = coarse_label(old, new)
            coarse[lab] += 1
            pos, per, win = replay(old, new, LOOP)
            all_rows.append({"repo": name, "sha": sha, "subject": subj,
                             "file": path, "old": old, "new": new,
                             "coarse": lab, "tok": tok,
                             "kinds_on_line": observed_kinds(old),
                             "win_kind": win, "pos_loop": pos, "per": per})
        print("coarse one-token labels:", dict(coarse.most_common()))
        reach = [r for r in all_rows if r["repo"] == name and r["win_kind"] is not None]
        print(f"reachable by a shipped class: {len(reach)} of {len(fixes)}")
        print("winning class frequency:",
              collections.Counter(KINDS[r["win_kind"]][0] for r in reach).most_common())

    # ------------------------------------------------ cost of class order --
    reach = [r for r in all_rows if r["win_kind"] is not None]
    print("\n=== per-fix replay on the defect line (reachable fixes) ===")
    print(f"{'repo':6} {'sha':10} {'coarse':12} {'win kind':28} {'kinds on line':22} "
          f"{'pos(loop)':>9} {'pos(best)':>9} {'pos(recur-LOO)':>14}")
    tot = collections.Counter()
    for r in reach:
        # recurrence order, leave-one-out within the SAME repo, ties by id
        same = [q for q in reach if q["repo"] == r["repo"] and q is not r]
        freq = collections.Counter(q["win_kind"] for q in same)
        recur = sorted(KINDS, key=lambda k: (-freq[k], k))
        pos_r, _, _ = replay(r["old"], r["new"], recur)
        best = [r["win_kind"]] + [k for k in LOOP if k != r["win_kind"]]
        pos_b, _, _ = replay(r["old"], r["new"], best)
        r["pos_recur_loo"], r["pos_best"], r["recur_order"] = pos_r, pos_b, recur
        tot[(r["repo"], "loop")] += r["pos_loop"]
        tot[(r["repo"], "recur")] += pos_r
        tot[(r["repo"], "best")] += pos_b
        print(f"{r['repo']:6} {r['sha']:10} {r['coarse']:12} "
              f"{KINDS[r['win_kind']][0]:28} {str(r['kinds_on_line']):22} "
              f"{r['pos_loop']:>9} {pos_b:>9} {pos_r:>14}")
    print("\nsuite runs on the defect line, summed over reachable fixes:")
    for repo in REPOS:
        n = sum(1 for r in reach if r["repo"] == repo)
        print(f"  {repo}: n={n} loop-order={tot[(repo,'loop')]} "
              f"recurrence-order(LOO)={tot[(repo,'recur')]} "
              f"winner-first(bound)={tot[(repo,'best')]}")
    # kinds preceding the winner on the line, under loop order
    ahead = collections.Counter()
    for r in reach:
        for k in r["per"]:
            if k != r["win_kind"]:
                ahead[KINDS[k][0]] += r["per"][k]
    print("candidates spent on NON-winning kinds ahead of the winner (loop order):",
          dict(ahead))
    # CHEAP bit slice: is the winner among the first two kinds on the line?
    outside = [r for r in reach if r["win_kind"] not in r["kinds_on_line"][:2]]
    print(f"reachable fixes whose winning kind is outside kinds[:2] (the CHEAP "
          f"slice in guard.rank_observations): {len(outside)} of {len(reach)}")

    with open(os.path.join(HERE, "scan_results.json"), "w") as f:
        json.dump(all_rows, f, indent=1, default=str)
    print("\nwrote", os.path.join(HERE, "scan_results.json"))


if __name__ == "__main__":
    main()
