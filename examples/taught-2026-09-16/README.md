# Five fault classes, taught once by hand (2026-09-16)

`rules_session.py` (kinds 4–7) and `rules_session_b.py` (kind 4) are the dictionaries used in
`research/llm-fusion-2026-09-16/RESULT.md` §6. Each class was taught from ONE worked example — a line
the seeded real-repo bench had broken in click (range start: in sortedcontainers) — with no model
anywhere, and frozen (sha256 recorded in the write-up) before the held-out cases in arrow,
sortedcontainers and rich were judged. Use:

    fluidfix guard . --dictionary examples/taught-2026-09-16/rules_session.py --budget 900

A user dictionary owns kinds 4–7, four classes per file; the fifth class lives in the second file.
