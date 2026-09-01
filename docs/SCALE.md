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

## v0.6.1 — the fourth miss falls (all four now byte-exact)

The arrow refusal above was autopsied to two scheduler faults, both fixed:
the escalation walked breadth-first rounds whose packets were too small to
see line 5468 at all, and the repair loop tried observations in line order
— the defect sat ~900th of 931, beyond any honest wall clock at ~6s of
suite per candidate. v0.6.1 escalates DEPTH-FIRST (each ranked file gets
full sight at once) and ranks observations by failing-test-name affinity:
`TestOdiaLocale::test_ordinal_number` names `OdiaLocale._ordinal_number`,
which is exactly where line 5468 lives. An adversarial review of the new
scheduler surfaced five defects — including a deadline path that could
have shipped a repair whose uniqueness was never proven — all fixed and
each pinned by a test before the re-runs below.

| v0.5 miss | v0.6.0 | v0.6.1 (rounds 5–6, clean-room) |
|---|---|---|
| `click/termui.py:744` | byte-exact @default | **byte-exact @default**, 203s |
| `click/_textwrap.py:18` | byte-exact @default | **byte-exact @default**, 326s |
| `click/utils.py:70` | byte-exact @1800 | **byte-exact @1800**, 553s (2.6× faster); bounded honest refusal @600 |
| `arrow/locales.py:5468` | refused @600 and @1800 | **byte-exact @DEFAULT 600** — 3 suite runs / 8.5s once sighted, 781s total |

Lab-notebook note, in full: rounds 4 and part of 5 were discarded after
forensics found an orphaned benchmark process (a killed measurement probe)
still writing candidate lines into the arrow clone concurrently — it made
one contaminated run appear to commit a wrong repair to `arrow/arrow.py`.
The environment was verified quiet (process tree killed, file stability
watched) before round 6, whose verdict is the published one. The
contaminated logs ship here too (`v6-replays-round5.log`, arrow entry),
labeled invalid: misses get autopsies, and so do our own benchmark
mistakes.

## v0.7.0 — span edits benchmarked on real repos (seeded, coordination-proven)

Pairs of single-token mutations on lines ≤3 apart, seed 20260901, with a
TRIPLE liveness proof per pair: each mutation ALONE breaks the suite, and
both together break it — so no single-line fix can green the trial and only
an atomic `SpanEdit` can. One generic taught class (paired-drift: candidates
mined from the observed line's own ±3-line neighborhood, capped at 32 —
nothing site-specific). Protocol and raw logs: `data/scale/span_bench*`.

| trial | pair | verdict |
|---|---|---|
| click `termui.py:50+53` | lit+lit, 3 apart | **byte-exact**, 1189s |
| click `parser.py:409+410` | cmp+lit, adjacent | **byte-exact**, 604s |
| arrow `arrow.py:1044+1046` | lit+lit, 2 apart | **byte-exact**, 39s |
| arrow `locales.py:3346+3347` | lit+lit, adjacent | timeout at the 1800s harness cap |

Three coordinated two-line defects on 1,990/1,902-test repos restored
byte-identical in one atomic candidate each; zero wrong repairs, zero
suite-green impostors, zero dirty trees. The locales.py timeout is the
known first-pass-unbounded gap amplified: a span class multiplies suite
runs per observation (≤32 candidates each), and the paired-drift signal
matches nearly every line of a 6,500-line locale table. Guidance shipped
with the feature: keep span-class signals TIGHT; a global `--budget` for
the first pass is the queued fix.


## v0.7.1 — the span bench drives two product fixes (4 rounds, all published)

| round | config | termui pair | parser pair | arrow.py pair | locales pair |
|---|---|---|---|---|---|
| 1 | unbounded first pass | exact 1189s | exact 604s | exact 39s | TIMEOUT 1800s |
| 2 | `--budget 1500`, half/half | refused | exact 606s | exact 40s | refused 1268s |
| 3 | split fixed (⅓ + rest) | refused | refused 1500s | exact 40s | refused 1122s |
| 4 | **+ fail-fast adjudication** | **exact 170s** | **exact 115s** | exact 39s | refused 1015s |

Round 3's regression was the decisive measurement: budget arithmetic was
never the bottleneck — candidate cost was (32-span sets × full 1,990-test
runs ≈ 2.5 min per observation). v0.7.1's fail-fast gate (last-failed
tests first, full suite as the only acceptance) made rejections ~10×
cheaper and returned every normal-code case to byte-exact at 5–7× round-1
speed. The locales data table remains the named hard case: bounded honest
refusal, tree clean, every rejected candidate logged with its killing
test. Round 2's "dirty tree" flags were a HARNESS bug (uncommitted
injections scored as guard writes) — disproven by direct byte-comparison
and fixed in round 3's protocol; rollback integrity never broke.
