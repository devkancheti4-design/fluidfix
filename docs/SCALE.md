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
