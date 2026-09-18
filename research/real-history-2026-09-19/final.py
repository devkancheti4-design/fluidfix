#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The shape coverage of REAL fixes, after two corrections. This is the number the growth claims needed.

Three passes were needed to get an honest split, and both earlier ones were optimistic:

  1  46% of real single-file fix commits replace exactly one line.
  2  masking strings and comments said 66% of those touch code — but a line INSIDE a docstring tokenises as
     bare names, so prose was still counted as code.
  3  the arbiter used here: a change our own abstraction cannot see is not a change to the program's shape.
     Tokenise both lines, replace strings, comments, numbers and non-keyword identifiers with placeholders,
     and if the two sequences are then identical, the commit changed TEXT, not logic.

The last rule is the one a repair tool must obey anyway: it is exactly the set of edits whose difference it
has no way to represent.
"""
from __future__ import annotations

import io, json, sys, tokenize
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from fluidfix.acts import KINDS, ACTS, Observation, act_for, load_dictionary   # noqa: E402

DICTS = [HERE.parents[1] / "examples" / "taught-2026-09-16" / "rules_session.py",
         HERE.parents[1] / "examples" / "taught-2026-09-18" / "kinds_from_ladder.py"]
KEEP = {"True","False","None","and","or","not","if","else","return","in","is","for","while",
        "len","min","max","int","str","sorted","range","self","lambda","import","from","elif"}


def abstract(line):
    try:
        ts = list(tokenize.generate_tokens(io.StringIO(line.strip() + "\n").readline))
    except Exception:
        return None
    out = []
    for t in ts:
        if t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT):
            continue
        out.append("STR" if t.type == tokenize.STRING else
                   "CMT" if t.type == tokenize.COMMENT else
                   "N" if t.type == tokenize.NUMBER else
                   (t.string if t.string in KEEP else "ID") if t.type == tokenize.NAME else
                   t.string)
    return out


def produces(before, after):
    hits = []
    for kind, entry in sorted(KINDS.items()):
        sig = entry[2]
        if sig is None or not sig.search(before):
            continue
        ap = ACTS.get(act_for(kind))
        if ap is None:
            continue
        obs = Observation(lineno=1); obs.kinds = [kind]; obs.all_lines = [before]
        try:
            cands = ap(before, obs)
        except Exception:
            continue
        for c in (cands if isinstance(cands, list) else [cands]):
            if isinstance(c, str) and c.rstrip() == after.rstrip():
                hits.append(entry[0]); break
    return hits


def main():
    for d in DICTS:
        load_dictionary(str(d))
    data = json.load(open(HERE / "real_history.json"))
    rows, total = data["rows"], data["commits"]
    ones = [r for r in rows if r["before"] is not None and r["after"] is not None and r["hunks"] == 1]

    code, text, bad = [], [], []
    for r in ones:
        a, b = abstract(r["before"]), abstract(r["after"])
        if a is None or b is None:
            bad.append(r)
        elif a == b:
            text.append(r)
        else:
            code.append(r)

    hits = [(r, produces(r["before"], r["after"])) for r in code]
    covered = [(r, h) for r, h in hits if h]

    print(f"{total} single-file fix commits mined from four real repositories\n")
    print(f"{'':44} {'n':>5} {'of one-liners':>14} {'of all fixes':>13}")
    print(f"{'one-line diffs':44} {len(ones):>5} {'—':>14} {len(ones)/total:>12.0%}")
    print(f"{'  … text only (prose, message, comment)':44} {len(text):>5} {len(text)/len(ones):>13.0%} {len(text)/total:>12.0%}")
    print(f"{'  … would not tokenise':44} {len(bad):>5} {len(bad)/len(ones):>13.0%} {len(bad)/total:>12.0%}")
    print(f"{'  … CODE — the teachable space':44} {len(code):>5} {len(code)/len(ones):>13.0%} {len(code)/total:>12.0%}")
    print(f"\n{'vocabulary produces the committed line exactly':44} {len(covered):>5} "
          f"{len(covered)/len(code):>13.1%} {len(covered)/total:>12.1%}")

    print("\nthe ones it already gets right, on real history:")
    for r, h in covered:
        print(f"  {r['repo']:22} {','.join(h)[:28]:28} {r['subject'][:44]}")
        print(f"      - {r['before'].strip()[:82]}")
        print(f"      + {r['after'].strip()[:82]}")

    sig = Counter()
    ex = {}
    for r in code:
        a, b = abstract(r["before"]), abstract(r["after"])
        i = 0
        while i < min(len(a), len(b)) and a[i] == b[i]:
            i += 1
        j = 0
        while j < min(len(a), len(b)) - i and a[len(a)-1-j] == b[len(b)-1-j]:
            j += 1
        g, t = " ".join(a[i:len(a)-j]) or "·", " ".join(b[i:len(b)-j]) or "·"
        if len(g.split()) <= 5 and len(t.split()) <= 5:
            k = f"{g}  →  {t}"
            sig[k] += 1; ex.setdefault(k, []).append(r)
    rec = [(k, v) for k, v in sig.most_common() if v >= 2]
    print(f"\nrecurrence among the {len(code)} code fixes: {len(rec)} shapes seen twice or more, "
          f"covering {sum(v for _k,v in rec)}")
    for k, v in rec[:10]:
        repos = sorted({x['repo'][:5] for x in ex[k]})
        print(f"  {k[:46]:46} {v:>3}  {','.join(repos)}")

    json.dump({"fix_commits": total, "one_line": len(ones), "text": len(text), "untokenised": len(bad),
               "code": len(code), "vocabulary_exact": len(covered),
               "recurring_shapes": len(rec), "recurring_covered": sum(v for _k, v in rec),
               "hits": [{"repo": r["repo"], "sha": r["sha"], "classes": h, "subject": r["subject"],
                         "before": r["before"], "after": r["after"]} for r, h in covered]},
              open(HERE / "final.json", "w"), indent=1)
    print("\nFINAL_DONE")


if __name__ == "__main__":
    main()
