#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Of the real one-line fixes, how many change CODE rather than text? The clustering forced this question.

Reducing each one-line fix to a transformation signature collapsed 67 of 134 to "nothing changed", which is
not a bug in the reduction: the edit lives inside a STRING LITERAL or a COMMENT. A typo in a warning, a
missing space in a message, a translated locale string, a `# noqa` — real fixes, all of them, and none of
them something a repair tool should ever touch.

So the 46% headline has to be split before it means anything. Strings and comments are masked out of both
lines; if what remains is identical, the commit changed text, not logic.
"""
from __future__ import annotations

import io, json, re, tokenize
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def mask(line: str) -> str | None:
    """The line with every string and comment replaced by a placeholder. None when it will not tokenise."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(line.strip() + "\n").readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    out = []
    for t in toks:
        if t.type == tokenize.STRING:
            out.append("«S»")
        elif t.type == tokenize.COMMENT:
            out.append("«C»")
        elif t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.INDENT,
                        tokenize.DEDENT):
            continue
        else:
            out.append(t.string)
    return " ".join(out)


def main():
    d = json.load(open(HERE / "real_history.json"))
    ones = [r for r in d["rows"] if r["before"] is not None and r["after"] is not None and r["hunks"] == 1]

    kinds = Counter()
    code_rows, text_rows = [], []
    for r in ones:
        mb, ma = mask(r["before"]), mask(r["after"])
        if mb is None or ma is None:
            kinds["did not tokenise"] += 1
            continue
        if mb == ma:
            kinds["text only — string, comment or whitespace"] += 1
            text_rows.append(r)
        else:
            kinds["code"] += 1
            code_rows.append(r)

    print(f"{len(ones)} one-line fixes from four real repositories\n")
    for k, v in kinds.most_common():
        print(f"  {k:46} {v:>4}  {v/len(ones):>4.0%}")

    print(f"\nSo the headline splits: of {len(ones)} one-line fixes, {len(code_rows)} touch logic "
          f"({len(code_rows)/len(ones):.0%} of one-liners, "
          f"{len(code_rows)/d['commits']:.0%} of all {d['commits']} fix commits).")

    print("\nwhat the TEXT-only fixes look like (a repair tool must never touch these):")
    for r in text_rows[:4]:
        print(f"    {r['repo']:8} {r['subject'][:58]}")
        print(f"        - {r['before'].strip()[:80]}")
        print(f"        + {r['after'].strip()[:80]}")

    print("\nwhat the CODE fixes look like — this is the real teachable space:")
    for r in code_rows[:8]:
        print(f"    {r['repo']:8} {r['subject'][:58]}")
        print(f"        - {r['before'].strip()[:80]}")
        print(f"        + {r['after'].strip()[:80]}")

    json.dump({"one_line": len(ones), "code": len(code_rows), "text": len(text_rows),
               "untokenised": kinds.get("did not tokenise", 0), "all_fix_commits": d["commits"],
               "code_rows": code_rows}, open(HERE / "code_vs_text.json", "w"), indent=1)
    print("\nSPLIT_DONE")


if __name__ == "__main__":
    main()
