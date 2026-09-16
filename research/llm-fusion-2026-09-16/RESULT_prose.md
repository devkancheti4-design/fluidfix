# Can fluidfix find and fix a bug quickly in hundreds of files, and what does escalating to a model cost? (measured 2026-09-16)

Asked as a CTO would: on real repositories, with the repository's own suite as the only judge, how often does the
zero-token guard restore the exact line, how long does it take, how often is it wrong, what does it refuse, and
when it refuses, what does it cost in tokens to let a model author a rule that the same suite then judges.
Every number below is written by the harness that measured it (`scale_results.json`, `bench_real_results.json`,
`cases/*/*/rerun_budget*.json`, `ladder_*.json`); `report.py` renders the tables. Nothing is typed in by hand.

## 1. Protocol (fixed before the run)

- Repositories: click, arrow, sortedcontainers, rich. Shallow clones, own venv each, suite green at baseline
  (rich: 8 environment-dependent tests deselected in its pyproject, committed on the clone).
- Seed 20260916. Mutation sites found by regex over library files only, shuffled once with the seed, taken in
  order; no human choice. Liveness checked twice (red, restore green, red); dead and flaky mutants recorded.
- Classes. In vocabulary (tier 0 should repair): comparison strictness, additive +/- flip, numeric literal +1.
  Out of vocabulary (tier 0 must refuse; the ladder then runs): and/or flip, `.get(k, d)` -> `.get(k)`,
  `if not X` -> `if X`, `range(1, n)` -> `range(n)`, `len(x) - 1` -> `len(x)`. Two live mutants per in-vocab
  class, one per out-of-vocab class, at most 25 attempts per class.
- Tier 0: `fluidfix guard . --commit --budget 300`; verdict EXACT (pristine bytes back), WRONG-GREEN (suite passes,
  bytes differ), REFUSED, NO-ACTION. Refused cases are saved with the guard's refusal report.
- Ladder: each saved out-of-vocab refusal is replayed from the recorded refusal through `fuse.py` with one author
  at a time. Tier 1: the author writes a rule (signal + applier) from a compact packet; it is validated offline
  and installed in a throwaway dictionary; the guard re-runs with the same 300 s budget. Tier 2: the author
  proposes up to three direct replacements, wrapped as a one-line rule; same guard, same judge. The author never
  judges. Tokens are the runtime's own counts (Ollama `prompt_eval_count`/`eval_count`); my own authoring is
  counted as characters/4 and marked approximate.
- Hardware: one 12-core Mac. The click trials ran with at most one other job on the machine. The arrow trials
  ran while several of my follow-up jobs competed for CPU (load average 10.5); every arrow case is therefore
  replayed alone in the clean pass below, and the clean numbers are the ones to quote.

## 2. Hundreds of files: does it find the one that broke?

{scale}

## 3. Real repositories, tier 0 (zero tokens)

{bench}

## 4. Replays: following the guard's own advice, and running the contended cases alone

{rerun}

## 5. The ladder: a model authors, the suite judges

Verdicts: EXACT = pristine bytes restored; WRONG-GREEN = the mutated line changed to something else and the
suite passed; SUSPECT = the suite passed but the mutated line is untouched (the author patched a different line,
a workaround, not a restoration); REFUSED = no proposal survived the suite.

{ladder}

## 6. Teach once by hand, judged on another developer's repo (zero tokens)

One worked example per class met in this study, written by hand from the click incident (`taught/rules_session.py`, `taught/rules_session_b.py`), no model anywhere. The suite of each target repo judges the taught candidates on the same class as it occurs there.

{taught}

## 6b. Debugging mode: many searchers, one judge (prototype, no product change)

The router law's own domain is the sharding key: one guard per kind, each in its own clone, all in parallel, and a judge that runs no suite and rules with the engine law's outcomes over the guards' reports (`shards/judge.py`). Measured on the cases the serial guard found but could not finish (arrow's 6,000-line locale file) or reach (rich `pretty.py`).

{shards}

## 7. What the measurements say

**Finding the file.** In a 302-file tree the true file ranked first 10/10 and the exact line came back in ~16 s. On the
real repos the ranking was right whenever the failure named a file; it went wrong in two measured ways, both fixed
today: a traceback frame inside the virtualenv was taken for project source (rich: every search died in pytest's own
code), and a rare-but-unrelated signal pointed the search at arrow's hub module (the SCARCE lane, now limited to
taught classes on the failing test's path — and still ambiguous with a multi-class dictionary, which no observation
can resolve).

**Repairing in vocabulary, zero tokens.** 7 of 22 real breaks restored byte-exact at 300 s in the pre-fix bench; the
refusals split into the honest kind (a passing candidate found, uniqueness unprovable under a capped view of a
3,000–6,000-line file), the hang kind (a mutant that also stalls a test makes every candidate cost the per-test
timeout), the bug kind (fixes 1–7), and my own harness's two out-of-class mutants. One wrong repair shipped (arrow: a
comparison flipped four lines above the fault, accepted by the suite) — the suite is the judge, so its blind spots are
the tool's.

**Escalating to a model.** Three 4B local models: 0 of 4 each on click, with the corrected full-sight packet; they
anchor on the crash line, not the guard above it, and their wrong proposals cost tokens (4k–14k per case), never a
wrong repair, because the same suite judges them. I (having seen the bench log) restored 3 of 4 on the same packets; that row is labelled for what it is. Haiku, run as a
sandboxed subagent that saw only the packet, wrote four answers (`cases/click/*/author_haiku-4.5/`): the right line on
and/or and `if not`, a workaround on `.get`, an invented line on `len-1`. They were never judged by the suite: the
judging lane was stopped at the user's request before it ran, so Haiku has no row in the table.

**Teaching once by hand.** One worked example per class from click, frozen (sha256 in `examples/taught-2026-09-16/`),
judged on the same classes in arrow, sortedcontainers and rich at the guard's advised 900 s: teaching examples 5/5,
held-out 6/11 byte-exact, 0 wrong, 5 refused with reasons (two found-but-held on a 6,000-line file, one doctest
pointer, one search-breadth miss, one ranking miss). Note the budget: a taught dictionary widens the search, and the
click `len-1` example needed 355–497 s because its file ranked fifth. Where it refuses, the table
says whether the correct line was found and held (uniqueness) or never reached.

**The PyPI release, side by side.** `fluidfix==0.15.0` installed in each clone, tier 0, 300 s, on nine in-vocabulary cases
(§4): same verdict as the source tree on click (hang refused, padded literal exact in 74 s) and on arrow's strictness and
second additive case (found, held); the same wrong repair on arrow additive 1 (117 s on the release, 221 s on the fixed tree:
the suite's blind spot, not the code's); rich additive 1 and 2 refused in 20 s on the release for the virtualenv bug and
refused at 300 s on the fixed tree for a ranking miss (`markdown.py` / `panel.py` never opened); sortedcontainers
strictness 2 exact in 62 s on the release, where the current tree, alone, holds it as found-but-unproven at 253 s — an open
difference (the tree is 0.15.0 plus the 2026-09-10 maintenance commits plus today's seven fixes; which change made the
uniqueness pass slower on this 3,000-line file is not diagnosed here). Net: the fixes remove a class of
false refusals (pytest's own code as a candidate) and one search defect (the escalation re-judging the first pass); they
do not change what the suite accepts.

**Where the clock goes.** Judging a candidate costs 2–5 s per suite run and 16–78 runs per repair; finding the file costs two
coverage runs, 5–40 s once; each file opened ahead of the right one costs a coverage pass, 30–90 s (click `len-1` spent ~300 of
355 s there); proving uniqueness after a green under a capped view costs more than 900 s on a 6,000-line file; a hanging
test costs 60 s per candidate; a wrong file first costs 50–500 candidates. None of it is the guard's own compute.

**Debugging mode, prototype.** Routed by kind — thirteen guards, one per shipped or taught class, each in its own clone, all
at once, a judge that runs no suite — the two arrow faults the serial guard had found and held in the 6,000-line locale
file were shipped byte-exact: only the matching kind's guard went green, one program, SHIP (§6b). The cost is honest and
large: 900–930 s wall for the slowest guard because thirteen suites shared twelve cores, and ~12,000 CPU-seconds per
incident. Rich and/or refused under the same contention with the ranking miss inherited by every shard. What routing buys
is exactly what the serial cost map predicted: one kind's candidates on a huge file fit the uniqueness pass; thirteen
kinds' do not.

**Seven product fixes came out of the run** (all applied, `fluidfix selfcheck` PASS): virtualenv paths are harness
paths; SCARCE from taught classes only, on the failing test's path; the refusal names the per-test timeout when the
red run hit one; the capped packet's sampler no longer repeats lines; an empty coverage report is "no coverage",
not a crash; and the escalation pass no longer re-judges the first pass's rejected candidates (before this, a fault
ranked 44th of 56 lines was unreachable at any budget).

**What was wrong with the measuring, and how it was handled.** My follow-up jobs and a second session's run shared
clones and CPU with the bench for parts of the evening; every affected row was discarded and re-measured alone, and
notes.md records each instance with times.

## 8. Not measured

- Claude Haiku / Sonnet / Opus and GPT as authors: no API key is available to this session and I will not enter
  one. `fuse.py --backend anthropic` is wired and runs the moment a key is set; a GPT backend would be ~15 lines.
- My own token counts are approximate (characters/4): I am not called through an API here.
