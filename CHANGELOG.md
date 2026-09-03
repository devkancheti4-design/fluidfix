# Changelog

## 0.9.0 — 2026-09-02

- **A fourth machine-authored kernel: the RANKING LAW.** fluidfix had laws
  for *what* to repair (fluid-router), *how* to drive candidates
  (fluid-router2) and what to do when *blocked* (the engine law) — but the
  order in which files and lines were examined was hand-written heuristics.
  Measured on click: a taught class that had just repaired two instances of
  itself spent 1,934s and 474 rejected candidates on a third without ever
  opening the defect file. `src/fluidfix/rank.py` vendors the authored law
  verbatim — seven evidence lanes with the RETRIED veto folded into each,
  priority 0..7, lower examined first — and it governs both file and line
  order. Verified exhaustively (all 256 situations against the
  specification, veto dominance, monotonicity in evidence).
- **`fluidfix selfcheck` now re-derives all FOUR laws**, not two: router
  (4,096 cases + identity + composition), lanes (256 states + termination),
  the engine law (verbatim fingerprint + the rulings the guard depends on),
  and the ranking law (256 situations + veto + monotonicity).
- **The failure's own evidence is now read.** An assertion prints the values
  it compared. Measured: a failing test printed
  `assert '\x1b[95m…' == '\x1b[94m…'`, and the literal `95` appeared in
  exactly ONE of 17 source files — the defect — while neither coverage
  specificity nor test-name affinity distinguished it at all (#6 under the
  old heuristic AND under the law). Feeding it into the law's FRAME lane
  moved it to #1, and the repair went from **1,740s and failing** to
  **50s byte-exact**. A literal naming one or two files is evidence; one
  naming many is noise and is ignored.
- **Refusals name the right cause.** Running out of clock while files were
  still unsearched is a SEARCH limit, not a vocabulary gap — it used to
  report "fault is outside the taught vocabulary" for a class that had just
  been taught and had already repaired two of its members, sending the user
  to write a rule they already had.
- **A suite that never RAN is no longer judged as a failing suite.**
  pytest exit 3/4/5 raise `HarnessError` naming the cause (found on
  SQLAlchemy 2.1: 1,466 tests collected with `-p no:cacheprovider`, ZERO
  with the cache provider `--lf` requires). A candidate in the tree owns
  whatever pytest chokes on, so `check()` rejects rather than aborting; and
  the fail-fast gate disables itself on harnesses that cannot support it.
- **Fusion integrity, enforced.** Two paths cited the engine law in strings
  while branching on hardcoded conditions; both now consult `decide()`, and
  a test parses every "engine law: X → Y" claim in the shipped source and
  re-derives it from the vendored law, so a comment can never drift from
  the ruling it names.
- `--max-candidates` / `FLUIDFIX_CANDIDATE_CAP`: the 32-candidate bound is a
  budget, not a safety limit — the suite still adjudicates every candidate.
- 122/122 tests.


## 0.8.0 — 2026-09-02

The 82-agent fresh-eyes fleet (24 real `pip install` personas, 24 adversarial
auditors, 18 identity judges, 14 market forecasters) produced a ranked fix
list; this release clears the engineering items. Every fix is test-pinned.

- **The teaching loop is documented** (~19/24 fresh users were blocked on
  this): `docs/TEACHING.md` — the full register() contract, kind numbering
  (4–7 reserved for user dictionaries), SpanEdit, and a 30-minute
  refusal-to-taught-class walkthrough — plus a runnable
  `examples/company_rules.py` (3 classes: rule, repo-mined set, span). A test
  extracts the walkthrough dictionary from the doc verbatim and proves it
  repairs its incident.
- **Five new shipped fault classes** (kinds 8–12; every one was a fresh
  user's FIRST bug and was refused): min/max swap, `+=`/`-=` flip,
  comparison-direction flip, reversed minus operands, boolean flip.
  `register()` now warns loudly before a user kind clobbers a shipped one.
- **`fluidfix kinds`** lists all 16 slots — shipped, taught, and free.
- **CLI**: readable `--help` (examples in an epilog), exit codes documented
  per subcommand, and relative `--python` now resolves against your shell's
  cwd and fails with ONE line instead of a 40-line traceback.
- **`--dry-run` — the propose-only channel** (the audit's top adoption
  blocker): repairs are captured as a unified diff in
  `.fluidfix/proposed.patch`, the tree is restored byte-exactly, and the
  patch applies cleanly with `git apply`. Mutually exclusive with
  `--commit`. Refusals unchanged.
- **Hygiene**: stale `last_refusal.json` cleared on green/repaired passes;
  stray `.coverage` files cleaned up; `.fluidfix/` gitignore guidance;
  refusal messages point at docs instead of marketing copy; harvest `why`
  entries doubled to 400 chars; repairs carry `restored_original`
  provenance when git can attest it.
- **Candidates that don't compile no longer burn suite runs**: a `compile()`
  pre-filter rejects syntax-error candidates instantly and logs them as
  such (Python targets only; jguard untouched).
- **PyPI publishing is now test-gated**: publish.yml runs the full suite
  before build/publish — nothing ships on red.
- 108/108 tests.


## 0.7.1 — 2026-09-01

- **Fail-fast candidate adjudication.** Every candidate now faces the
  last-failed tests first (~10× cheaper); only a candidate that fixes those
  runs the FULL suite, which remains the only acceptance gate — soundness
  untouched, rejections (~97% of all repair work) massively cheaper.
  Measured on the seeded span bench: click termui pair 1189s → **170s**,
  click parser pair 604s → **115s**, both byte-exact. Coverage fail-under
  gates are neutralized on the fast run only (subset coverage is
  meaningless); the confirming run keeps the repo's own configuration.
- **`--budget` — one wall clock for the whole guard pass.** First pass gets
  at most a third; the full-sight escalation stage gets all the rest
  (overriding `--escalate-budget`). Expiry anywhere is an honest refusal
  that names the budget. The three-round measurement history that shaped
  the split (half/half starved escalation; the split alone without
  fail-fast lost previously-won repairs) is in docs/SCALE.md — published,
  not hidden.
- Span bench final (seeded coordinated pairs, triple liveness proof, one
  generic taught class): **3/4 byte-exact atomic two-line repairs** at
  `--budget 1500`; the fourth (arrow locales.py, the 6,500-line data
  table) refuses boundedly at 1015s with every rejected candidate logged
  against the test that killed it. Zero wrong repairs, zero impostors,
  zero dirty trees across all four rounds.
- 69/69 tests (budget honesty + first-pass→escalation handoff pinned).


## 0.7.0 — 2026-09-01

- **Span edits — the engine law's CHANGE_GRANULARITY act, actuated.** A
  taught transform may now return `SpanEdit(start, end, text)`: ONE atomic
  candidate replacing several existing lines together — the fix for defects
  where no single-line change can green the suite (that boundary was
  measured and pinned in 0.6.1's tests; the same scenario now repairs).
  Every contract carries over unchanged: suite-adjudicated per candidate,
  byte-exact rollback on rejection (CRLF-pinned test), two different green
  spans refuse as AMBIGUOUS with the pinning-test ask, and a span may only
  edit lines its own observation points into (bounds + anchor safety,
  tested). Also closes the dead-code shadowing hazard: block rewrites now
  replace the whole wrong region instead of stranding unreachable lines.
- **Per-candidate failure logs — the engine law's HARVEST_COUNTEREXAMPLE
  act, actuated.** Every rejected candidate is recorded WITH the exact
  failing test that rejected it (same suite run, zero extra cost) and
  written to `.fluidfix/last_refusal.json` as `rejected_candidates`;
  refusal summaries state how many candidates were tried. Teaching a class
  after a refusal now starts from evidence, not archaeology.
- `SpanEdit` is in scope inside dictionary files (like `re` and
  `register`) and exported from the package root. 67/67 tests
  (`tests/test_span_edits.py` is the new battery).


## 0.6.1 — 2026-08-31

- **All four v0.5 misses now repair byte-exact** (byte-faithful replays, raw
  logs + injection scripts in `docs/data/scale/`): `arrow/locales.py:5468`
  at the DEFAULT budget (3 suite runs / 8.5s once sighted; 781s total),
  `click/_textwrap.py:18` (326s) and `click/termui.py:744` (203s) at the
  default budget, `click/utils.py:70` at `--escalate-budget 1800` (553s —
  2.6× faster than 0.6.0; refuses honestly and boundedly at the 600s
  default). Zero wrong repairs under clean-room conditions.
- **Depth-first escalation scheduler.** CAPPED→RAISE_BUDGET no longer walks
  breadth-first factor rounds (measured: they spent the whole clock on
  packets too small to see the arrow defect). Each candidate file, in rank
  order, now gets full sight at once — packet at 990 lines, rebuilt
  unbounded if still truncated — one repair per file, under the wall clock.
- **Line-level affinity ranking.** The failing test names its subject:
  `TestOdiaLocale::test_ordinal_number` points at `OdiaLocale.
  _ordinal_number`, so observations inside name-matching classes/defs are
  tried first. Measured: the arrow defect sat ~900th of 931 observations in
  line order — unreachable inside any honest budget — and ranks in the
  first handful by affinity. Tokens come only from FAILED/ERROR node ids.
- **Five fixes from an adversarial review of the scheduler** (each pinned by
  a test): a deadline can never interrupt a candidate set after one green —
  the ambiguity proof always completes, so a repair shipped under time
  pressure can no longer be an unproven guess; a signal-filter drop now
  counts as CAPPED (in-vocabulary lines like `a // b` match no filter
  token, and "untruncated" packets missing them defeated escalation); files
  whose first-pass packet was already complete are not redundantly
  re-searched; one file can eat at most half the escalation budget (a wrong
  rank-1 must not starve the rest); no observer calls are spent after the
  deadline.
- **Multi-line logic fixes are now CI-pinned**: a taught class rewriting one
  defective line into a corrected block (zero-guard control flow), taught
  from one example and generalising to a second member with zero new
  examples, is a committed test — the claim goes red if it stops being true.
- Lab-notebook honesty note: two intermediate replay rounds were discarded
  after discovering an orphaned benchmark process concurrently writing
  candidate lines into the arrow clone (it made one contaminated run look
  like a wrong repair of `arrow/arrow.py`). The published verdicts come from
  a verified-quiet environment; the discarded logs ship in
  `docs/data/scale/` too, labeled as contaminated.
- 59/59 tests.

## 0.6.0 — 2026-08-31

- **The engine law fused into the guard.** The third machine-authored kernel
  (`act = (4 & ntzb(x-7)) + ntzb(x + (x&128))`) is vendored verbatim in
  `fluidfix/engine.py` — pinned by a fingerprint test (sha256 `48bf50bf…`,
  1,555 chars) — and now rules on every non-green pass instead of hard-coded
  policy:
  - **BUILT+AMB → ADD_STATE**: when two *different* candidates both green the
    suite, the guard refuses and asks for one pinning test instead of
    shipping whichever came first. It never guesses between
    suite-indistinguishable repairs.
  - **CAPPED → RAISE_BUDGET**: when a budget truncated the search (packet
    sampling, or more implicated files than the pass tried), the guard
    escalates — packet ×3/×9, candidate files 24/72 — under a wall-clock cap
    (`--escalate-budget`, default 600s). Refusals state the cap was hit.
  - **REFUTED → HARVEST_COUNTEREXAMPLE / UNREAD → ADD_MATERIAL**: honest,
    specific stops (what was tried; what to install) — never silent.
- **Measured: byte-faithful replays of all four v0.5 misses** (same seeded
  sites, columns, tokens; injection asserted against pinned baselines; raw
  logs in `docs/data/scale/`). Three now repair byte-exact:
  `click/_textwrap.py:18` and `click/termui.py:744` at the default budget,
  `click/utils.py:70` at `--escalate-budget 1800`. The fourth
  (`arrow/locales.py:5468`) still refuses — boundedly, tree untouched, with
  the honest hint — at both 600s and 1800s. Full table in `docs/SCALE.md`.
- **Zero-padded literals now decrement width-preserving** (`034`→`033`,
  never `33`). The round-1 termui replay measured the green-only imposter
  this generated; with the fix the byte-exact restore is generated and wins.
  Regression-tested against the exact replay line.
- 55/55 tests. The law's rulings and each fused path (AMB refusal, CAPPED
  escalation, REFUTED stop) have dedicated tests in
  `tests/test_engine_fusion.py`.

## 0.5.0 — 2026-08-31

- **Large-repo localisation, measured then fixed.** A strict seeded benchmark
  (docs/SCALE.md) scored the shipped pipeline 0/6 on click. Three general
  fixes — file ranking by failing-test-name affinity + coverage specificity
  (not file size), spread-sampled packets (no first-N truncation), and
  appliers that emit every-occurrence candidate sets — took the identical
  sites to 14/18 byte-exact across click, arrow, and sortedcontainers, with
  both held-out repos beating the diagnosed one. All misses autopsied and
  named in docs/SCALE.md; out-of-vocabulary safety 3/3 refused.
- Precision wording sharpened after the first-ever green-only repair on a
  weakly-tested line: fluidfix never ships a repair its suite rejects;
  byte-exactness is bounded by suite strength (14/15 accepted repairs exact
  in this benchmark).

## 0.4.0 — 2026-08-31

- **`fluidfix init` — the zero-tests on-ramp.** Scans the repo, probes every
  module in a subprocess, and generates `test_fluidfix_smoke.py` covering the
  ones that import cleanly today — so a repo with NO tests becomes guardable
  in three commands (install, init, guard). Modules that don't import are
  reported and excluded; existing files are never clobbered without --force.
  The generated file carries the paste-trick template for leveling up to
  value-level guarding. End-to-end tested: init -> guard repairs an
  import-breaking operator flip and commits the restoration.

## 0.3.0 — 2026-08-31

- **Repo-searchable value classes.** Taught transforms may now return a
  candidate SET (list of lines) mined from repo context — `Observation`
  carries `file`, `root`, and `all_lines`; the loop tries each candidate in
  order (bounded at 32) and the suite adjudicates every one. Measured before:
  rule-shaped classes generalized 11/11 exact from one example, value-shaped
  0/5 (all refused). With one context-aware registration, the same held-out
  value bugs now repair byte-exact — and when the correct value exists
  nowhere in the repo, every candidate fails and the guard still refuses with
  the tree byte-identical. The no-wrong-repairs contract is unchanged;
  precision is bounded by suite strength.
- `apply()` retained as the single-candidate back-compat API.

## 0.2.1 — 2026-08-31

- Guard refusals now diagnose themselves: when no candidate file is found and
  `pytest-cov` is missing from the target interpreter, the refusal (and
  `.fluidfix/last_refusal.json`) says exactly that and gives the install
  command. Found live: on pallets/click (1,990 tests) an assert-only failure
  names no source file, so without pytest-cov the guard refused; with it, the
  guard localised and repaired the fault unaided in 71s. Verified again on
  sortedcontainers. Docs now list pytest-cov as a prerequisite.

## 0.2.0 — 2026-08-30

- `--dictionary FILE` on `guard` and `repair`, and `load_dictionary()`: ship a
  versioned per-repo fault-class dictionary (a Python file of `register()`
  calls). One hard example teaches a class; the guard loads it at startup and
  every member of the class is repaired autonomously from then on.
- `commit_repair()` now returns "committed" / "clean" / "failed" so a
  restoration that already matches HEAD is not reported as a failure.
- `docs/media/`: five sub-30s terminal recordings from real runs (live PyPI
  install, guard commit-and-forget, real-library repair, teach-a-class,
  one-hard-example -> whole-class across three files).

## 0.1.0 — 2026-08-30 (r3)

- `fluidfix guard`: commit-and-forget maintenance. Mechanical fault-file
  discovery (traceback frames, else failing-test coverage ranking), one-shot
  CI mode (exit 2 on refusal) or `--interval` watch mode, opt-in `--commit`
  of each restoration, and a machine-readable `.fluidfix/last_refusal.json`
  teach-me signal on refusal. Library API: `guard_once`,
  `find_candidate_files`, `commit_repair`, `write_refusal`.

## 0.1.0 — 2026-08-30 (r2, pre-release review applied)

- `register()`: teach a new fault class from one registration — observation
  contract + transform; the router infers the act code from the same worked
  example. Mechanical observer now covers registered kinds generically.
- Review fixes (all reproduced before fixing): site-local zero simplification
  in `_reduce_literal` (was able to eat an unrelated `-0.5` elsewhere on the
  line); byte-preserving file handling (CRLF/FF-safe, no write on refusal);
  path-boundary coverage matching (same-suffix sibling packages can no longer
  shadow the defect file); root-level modules get a correct default `--cov`
  target; CLI timeout flags (`--suite-timeout`, `--test-timeout`,
  `--candidate-timeout`, defaulting consistently); observer errors are
  diagnosable (truncation, missing text, wrong echoed ids raise instead of
  masquerading as refusals); injected observer clients work without the SDK;
  `acts_tried` counts only real candidates.

## 0.1.0 — 2026-08-30

Initial release.

- Vendored routing kernel (fluid-router, verbatim, `minimal in D∩I`) and
  EMIT/ADVANCE/HALT loop discipline (fluid-router2, verbatim).
- Mechanical localisation: traceback frames ∪ failing-test coverage
  (pytest-cov `--lf`, no `-x`) ∪ AST statement-span expansion. 33/33 true
  lines captured on the benchmark corpus at 0 tokens.
- Observers: `MechanicalObserver` (zero-token) and `ClaudeObserver`
  (Claude Opus 5, batched, schema-forced, with server-side refusal fallbacks).
- Clear-data applier pointers: `literal_value`/`literal_occurrence` (17/27 →
  26/27 in-vocabulary byte-exact on the corpus) and `op_occurrence` (closes
  the last measured miss).
- Safety: green-suite refusal, out-of-vocabulary refusal, byte-exact rollback,
  candidate timeouts, defended oracle (five encoded harness-defect classes).
- `fluidfix` CLI: `repair`, `packet`, `selfcheck`.
