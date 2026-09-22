# Does the vocabulary cover real history? A census — 2026-09-22

The question asked: with the knowledge it has now, how much of real work does fluidnet cover? Measured the
honest way — replay real maintainer fixes against the vocabulary — and the honest scope: this is the
**knowledge** question only. "Reached" means the maintainer's exact line was among the candidates the net
would have proposed. No suite ran, so nothing here is certified; it is the ceiling, not the result.

Source: 565 real fixes mined from click, arrow, rich and python-sortedcontainers
(`research/real-history-2026-09-19/remine.json`). Every dictionary ran in its own process and the results
were unioned — that union is the swarm, one overseer over N nets, and it is why the swarm reaches 10 where
the best single net reaches 9.

## The number

| | fixes | reached | |
|---|---|---|---|
| all real fixes | 565 | 10 | **1.8%** |
| removed side is one line | 276 | 10 | 3.6% |
| …of which single-token mechanical logic (a number, an operator, a boolean) | 12 | 9 | **75%** |

Both of those last two rows are true at once, and the gap between them is the whole finding.

## Where the vocabulary is strong

Where a real fix is one mechanical token — `>` to `>=`, `[1]` to `[0]`, `True` to `False`, `== 1` to
`== 0` — the current vocabulary reaches **9 of 12**. That includes the `rich`
`segment.py` fix, reached with the correct placement `(len(text) - 1)` by class 7 under the placement law.
This is the vocabulary doing exactly what it was taught, on repositories it was mostly not taught from.

Of the ten reached, nine are code. One (`rich 4aca2c06ce`) is a docstring — the maintainer's fix really
was `Defaults to False` → `Defaults to True`, and the vocabulary really did reach it, but no suite could
judge it, so it does not count toward anything certifiable.

## Where the mass is, and why it is not covered

The single-token mechanical band is **12 of 276 one-line fixes — about
4%**. The rest, by shape:

| shape of the real one-line fix | count | reached |
|---|---|---|
| one line became several | 60 | 0 |
| one name swapped | 42 | 0 |
| one string literal swapped | 37 | 0 |
| rewritten, many tokens | 25 | 0 |
| one punctuation swapped | 24 | 0 |
| a call or attribute added | 23 | 1 |
| tokens removed | 15 | 0 |
| punctuation added | 14 | 0 |

Two things about that table.

**A great deal of it is not code.** By a conservative test — docstring, comment, `:param`, a locale-table
entry, a prose sentence — **43 of the 276 one-line fixes (16%) are
text, not logic**: `"una settimana,"` → `"una settimana"`, `inpute locale` → `input locale`. arrow alone
contributes 51 one-line fixes and 9 of them are locale strings. No test
suite judges these and no repair guard should touch them. They inflate "one-line fixes" without being
bugs in the sense that matters here.

**The largest code bucket is expansion.** 60 fixes turned one line into several. The
mechanism can express that — a candidate containing newlines splices into multiple lines, and the span
classes hit 24/24 on unseen instances of the shapes they were taught — but those shapes were not taught,
and this census shows how much of the surface they own.

## What this says about "open-ended"

It sharpens the earlier answer. Even among one-line fixes in generic open-source history, only about
4% are single-token mechanical logic changes — the band a taught class owns
outright. Most one-line fixes are one line because *finding* them was the work, or because they are data.

That is exactly the design premise, measured: **generic knowledge covers very little of someone else's
history.** The vocabulary reaches what it was taught, at a high rate, and it was taught from a handful of
incidents. The coverage an engineer gets is a function of how much of *their own* work repeats — and the
way to know that number is to run this census against their own history, not to quote this one.

## Recognised but not reached

The swarm's signals fired on 108 lines and produced the maintainer's line for 10. The other 98 are the
dangerous middle: a class that *thinks* it knows the shape and proposes something else. That is the case
the property gate exists for, and the reason "recognises" is not a number to advertise.

## Honest boundaries

- Knowledge only. A reached fix may still be rejected by the suite, or be one of several candidates the
  suite must choose between. Certification is a separate measurement (`research/certify-2026-09-18`).
- Whitespace-insensitive line equality. A semantically identical fix written differently counts as missed.
- One-line removals only (276 of 565); the 289 larger diffs were not
  attempted here, and the earlier study found 91% of real fixes are twenty lines or fewer.
- The text/code split is a regex heuristic, deliberately conservative; the true text share is probably
  higher.
