# Large-repo benchmark — strict, seeded, report-everything (2026-08-31)

**Protocol** (pre-registered in [data/scale/protocol.py](data/scale/protocol.py)):
three large green-suite repos; mutation sites found by regex over library
files only, shuffled with seed 20260831, taken in order — no human choice;
dead mutants (suite doesn't catch) recorded and skipped; per live mutant the
break is committed and `fluidfix guard . --commit` runs with no file named;
serial execution for honest wall-clocks; and/or flips included as
out-of-vocabulary safety trials. Raw logs ship in [data/scale/](data/scale/).

## Results (mechanical observer, zero tokens)

| Repo | LOC / tests | In-vocab trials | Byte-exact | Green-only | Refused | OOV safety |
|---|---|---|---|---|---|---|
| click | 28,581 / 1,990 | 6 | 3 | 1 | 2 | refused ✓ |
| arrow *(held-out)* | 19,928 / 1,902 | 6 | 5 | 0 | 1 | refused ✓ |
| sortedcontainers *(held-out)* | 11,324 / 366 | 6 | 6 | 0 | 0 | refused ✓ |
| **total** | | **18** | **14 (78%)** | **1 (5%)** | **3 (17%)** | **3/3 ✓** |

Repair wall-clock: 18s–891s, median ≈ 200s. Before v0.5.0's localisation
fixes the same seeded click sites scored **0/6 (all refused)**; the fixes
were diagnosed on click only — arrow and sortedcontainers are genuine
held-outs, and both outperformed click.

## Every miss has a named cause (autopsied, none mysterious)

- `click/_textwrap.py:18`, `click/utils.py:70` — the fault file never entered
  the candidate list: no test is named after these files and the failing
  tests execute many files (file-localisation limitation).
- `arrow/locales.py:5468` — file ranked #1, but the defect sits at line 5,468
  of a 6,000-line file and fell outside the 110-line packet budget (packet
  retention limitation).
- All three are perception limits, safely refused, and are the exact cases
  the model-observer escalation tier (`--observer claude`) targets.

## The green-only finding (`click/termui.py:744`)

Wider candidate search produced our first-ever suite-passing repair that is
NOT the original line: a different literal on a weakly-tested line satisfied
all 1,990 tests. Precise wording from now on: **fluidfix has never shipped a
repair its suite rejects; byte-exactness is bounded by suite strength** —
measured here at 14 byte-exact of 15 accepted repairs (93%). Strong suites
get exact restorations; weak coverage admits suite-equivalent imposters, the
known cost every automated-repair system pays.

## v0.6.0 addendum — the engine law replayed against every miss

v0.6.0 fuses the third machine-authored kernel (the engine law,
`fluidfix/engine.py`, vendored verbatim and fingerprint-tested) into the
guard: AMB refuses when two different candidates both green the suite,
CAPPED escalates truncated searches (packet ×3/×9, files 24/72) under
`--escalate-budget` (default 600s), REFUTED and UNREAD stop honestly with
specific hints.

Every v0.5 miss above was then replayed **byte-faithfully** — same seed-
derived sites, same columns, same tokens, injection asserted against
baseline content, repos hard-reset to pinned SHAs (raw logs:
`data/scale/v6-replays-round*.log`, scripts alongside):

| v0.5 miss | v0.5 verdict | v0.6 verdict |
|---|---|---|
| `click/_textwrap.py:18` (cmp) | REFUSED 209s | **byte-exact repair**, default budget, 432s total |
| `click/termui.py:744` (lit `\033`→`\034`) | GREEN-ONLY imposter | **byte-exact repair**, default budget, 198s total |
| `click/utils.py:70` (lit) | REFUSED 814s | **byte-exact repair** at `--escalate-budget 1800` (refuses boundedly at the 600s default) |
| `arrow/locales.py:5468` (cmp) | REFUSED 765s | still refuses — boundedly, tree untouched, honest hint — at 600s and 1800s |

Three of the four former misses now restore byte-exact. The fourth is a
~6,500-line file whose failing tests execute thousands of lines; the
refusal hint says exactly that and names the ways out (raise the budget,
`--observer claude`, fix by hand). The termui imposter's root cause was a
generator bug — literal decrement lost zero-padding ("034"→"33") — fixed
width-preserving and regression-tested; the byte-exact candidate now exists
and wins. No unbounded runtime remains: every escalation is wall-clock
capped and every stop states its reason.
