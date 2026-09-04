# Changelog

## 0.13.0 — 2026-09-04

- **A FLAKY SUITE CAN MAKE A WRONG REPAIR, AND THE LAW ALREADY HAD THE
  REMEDY.** Measured against a test that skips its assert half the time:
  fluidfix accepted `return b - a` for `return a + b` in **14% of searches**
  (7 of 50; a second run measured 4 of 45). Correctness is bounded by the
  oracle, and an oracle that does not hold still is a weak one.

  The fix was NOT a patch to the decision. A green from ONE run is a COARSE
  record; re-checking produces FINE records, and when those disagree the
  situation is exactly the engine law's `HIDDEN` — *"fine records disagree,
  coarse records agree"* — whose ruling is `CHANGE_GRANULARITY`: stop judging
  at the granularity of a single run. That lane had never been measured.
  Wiring it took the false-accept rate to **0 of 49 and 0 of 46** across two
  A/B runs, and produced *more* correct repairs (10 vs 7, 10 vs 1) — a
  candidate that was only ever green by luck stops occupying the answer.
  Tunable with `FLUIDFIX_CONFIRM` (default 1; 0 restores the old behaviour).

- **The law has never ruled wrongly, and that is now a test.**
  `tests/test_law_never_ruled_wrong.py` audits every incident this project
  has recorded — nine of them — against what the law ruled and where the
  defect actually lived: observation (4), actuation (1), the wording of a
  report (1), **the ruling itself (0)**. The build fails if that ever
  changes. This replaces the older, weaker and false claim that fluidfix
  "never makes a wrong repair": it does, when its oracle lies to it. What
  holds is that the law rules correctly on the situation it is given.

- **C# / .NET works, and needed no adapter.** `cguard` is already generic
  over its build and test commands, so `dotnet build` and
  `dotnet test --no-build` slot straight in. Supporting the language cost
  **one source extension (`.cs`) and one regex** for the
  `Failed Class.Method [2 ms]` shape dotnet prints. Measured on a .NET class
  library with xunit: a cross-product sign flip repaired **byte-exact in 14
  suite runs (20.8s)**, warm cycle 1.63s. Java took 223 lines of adapter, C
  took ~450, C# took two.

  **Unity is not the same as C#**: the language works, but Unity's own test
  framework generally needs the Editor in batch mode, which is a harder
  oracle and is untested.

- The failure parser now reads three runner families that share nothing —
  cglm's cross mark with `assert fail in <file> on line <n>`, Box2D's
  `test failed: <Name>` with no file or line anywhere, and dotnet's
  `Failed <Class>.<Method> [2 ms]` — without any of them breaking the others.


## 0.12.0 — 2026-09-04

- **`fluidfix hotspots` — what should we test FIRST?** fluidfix maintains
  exactly what your tests cover, which makes that the highest-value question
  a team can ask before adopting it, and the repository already knows the
  answer: every bug fix in its history names the file that broke. Ranks files
  by defect density x coverage gap, and reports what testing them buys.
  Measured on Box2D's own history (1,383 commits):

      to guard 30% of past defects  ->  test  17 files
      to guard 50%                  ->  test  40 files
      to guard 60%                  ->  test  58 files
      to guard 80%                  ->  test 138 files

  **60% of defects costs ~30% of files, not 60%** — defects cluster, so
  coverage aimed at the cluster is worth roughly twice coverage spread
  evenly. "Get to 60% coverage" is a year nobody funds; "test the 58 files
  your own history named" is a sprint.

- **ROLLBACK NOW SURVIVES THE PROCESS DYING.** Candidates were applied to the
  real file and rolled back from memory — byte-exact and correct, right up
  until the process was killed mid-candidate. Then the mutation stayed on
  disk and NOTHING recorded the original bytes. Measured on Box2D: a
  literal-off-by-one candidate turned an atomic increment into `+ 0` inside a
  worker spin loop; the test binary hung, every core saturated (load average
  30), the guard was killed, and src/parallel_for.c was left holding
  fluidfix's mutation. Unattended on a studio's CI that is corrupted source
  with no audit trail. The original bytes are now journalled to
  `.fluidfix/inflight.json` before any mutation and recovered on the next
  start, by both the Python and C guards.

  The first fix was wrong in an instructive way: it scoped the journal to the
  first mutation window and discharged it inside the per-kind loop, but
  `wrote` stays true across iterations, so every LATER mutation ran
  unjournalled. A test now spies on every single write and asserts a live
  journal behind each one.

- **A hanging candidate is killed, not orphaned.** A candidate can hang
  rather than fail — ordinary in C, and not the same thing.
  `subprocess.run(shell=True)` kills only the SHELL on timeout, so a spinning
  test binary outlived its run and competed with every later candidate. The
  C oracle now starts a new session and signals the whole process group.

- **THE BUILD IS PART OF THE ORACLE.** Mutate a header and an incremental
  build may not rebuild every translation unit that includes it; the binary
  stops corresponding to the source and every verdict after that is noise.
  Measured on Box2D: a stale binary made the suite red for a reason unrelated
  to the defect, so all 35 candidates — INCLUDING THE CORRECT ONE — were
  rejected. Re-run after a clean rebuild, the same experiment repaired
  byte-exact in 34 runs. The C oracle now refuses to judge against a test
  binary older than the sources, and says how to fix it.

- **`fluidfix --version`, and a version that cannot drift.** `pip install
  fluidfix` is a NO-OP when any version is already present — it does not
  upgrade — so a stale install is silent and surfaces later as "this
  subcommand does not exist". Hit three times on one machine in a single day.
  `selfcheck` now prints the running version as its first line. Fixing that
  exposed a worse one: `__version__` sat at "0.9.1" in `__init__.py` through
  BOTH the 0.10.0 and 0.11.0 releases, so two shipped versions advertised the
  wrong number to anyone reading it. `pyproject.toml` now derives the
  distribution version FROM that attribute, `_version()` prefers the package
  attribute over installed metadata (an editable install reports whatever it
  was registered with — the same staleness trap in another costume), and a
  test pins the attribute against both the pyproject wiring and the newest
  CHANGELOG heading.
- Measured on Box2D, and the reason the release exists: **a taught class
  derives the fix from the codebase.** Taught ONE example —
  `shape->density = def->friction` -> `def->density`, a different file and
  different fields, describing only the SHAPE of the fault. Broke
  `body->mass += massData.mass` to `body->inertia` in another file: compiles
  clean, silently corrupts every mass computation, breaks DeterminismTest and
  MultithreadingTest. Repaired **byte-exact in 34 suite runs (116s)**. The
  field name `mass` appears in no worked example and in no transform — it was
  mined from the source and chosen by the suite. That is what "derives"
  means, and what it does not: a search over values the repository already
  contains, not invention. If the right field existed nowhere in that file,
  fluidfix refuses.


## 0.11.0 — 2026-09-04

- **C/C++ support: `fluidfix cguard` (alpha).** `src/fluidfix/coracle.py` is
  a compile-and-run oracle behind the SAME contract the repair loop already
  speaks, so `repair()`, `SpanEdit`, AMB refusal, deadlines and the
  per-candidate failure harvest are REUSED. **No kernel changed.** The five
  laws route integers and edit lines of text; they never knew what Python
  was and did not need to learn what C is. Java took a 223-line adapter;
  C took ~450.
- **The compiler is a second oracle, and it is cheaper than the tests.** In
  Python a nonsense candidate still runs and must be rejected by a full
  suite; in C most nonsense does not compile and the toolchain says so in
  milliseconds. A build failure on a MUTATED tree is an ordinary rejection;
  a build failure on the PRISTINE tree is a `CBuildError` — conflating them
  would be the C form of treating a missing pytest as a red suite.
- **A gcov tier.** A separate instrumented build directory beside the fast
  one, so the candidate loop never pays for instrumentation. Fail-only
  coverage in 0.5s and full-suite coverage in 0.3s on Box2D; the packet is
  anchored on lines the failing test actually executed (mode `coverage`),
  and files it never executed are dropped — but only when the coverage is
  credible (see below).
- **Measured on two real game repos, all byte-exact:**

      Box2D   b2Cross sign flip (shipped vocabulary, no teaching)
              -> byte-exact in 46 suite runs, 82.8s
      cglm    glm_vec3_add sign flip
              -> byte-exact in 100 suite runs, 326.7s
      Box2D   pointer arithmetic in contact_solver.c, with NO frame, NO
              discriminating literal and NO name affinity (the failing tests
              are MultithreadingTest / DeterminismTest, which name no source
              file at all)
              -> REFUSED at a 3600s budget before the gcov tier;
                 byte-exact in 428 suite runs (1479s) after it, and 5x
                 cheaper per candidate (18.8s -> 3.5s)

- **THE ORACLE IS NOT A CANDIDATE — the most important fix in this
  release.** Caught by this release's own end-to-end test: given a runner at
  a repo root that was not recognised as test code, the guard repaired the
  RUNNER rather than the defect. What it wrote:

      - { printf("test failed: AddTest\n"); return 1; }
      + { printf("test failed: AddTest\n"); return 0; }

  It did not fix the bug. It changed the harness's failure exit code, left
  the defect untouched, and declared success — while the output still said
  `test failed`. It silenced the alarm instead of putting out the fire. Any
  repair tool that can reach its own oracle will find that edit, because it
  is the cheapest path to green, and that single behaviour would void every
  other guarantee this project makes.

  TWO defences, because excluding harness files by NAME is a patch and not a
  cure — a project may call its runner anything:

    1. harness files are excluded by name as well as by directory;
    2. **a green exit code is no longer sufficient.** The suite's OUTPUT is
       cross-examined against its exit code, and a run that still reports
       failing tests is red no matter what it returns. A candidate that
       silences the oracle instead of repairing the fault is rejected with
       that reason named.

  Both are pinned by tests, including one that disables the first defence to
  prove the second forces a real repair on its own.

  **The Python oracle got the same cross-examination.** The exposure is
  structural, not language-specific: `_is_test_path` keeps test files out of
  the candidate set, but a project may keep its tests somewhere fluidfix does
  not recognise, and pytest's exit code was the only thing being trusted. A
  run that exits 0 while its summary still reports `N failed` or `N errors`
  is now rejected with that reason named.
- Four more C-specific corrections, each found by measurement:
  - a stem maps to EVERY file that shares it: `vec3.c` and `vec3.h` collided
    and the five-line wrapper beat the header holding the implementation;
  - do not split a letter from a digit: `vec3` is the token that identifies
    the module, and `vec` + `3` identifies nothing;
  - camelCase test names are split, so `MathTest` reaches `math_functions.c`;
  - `samples/`, `shared/`, `benchmark/` and `examples/` are never candidates
    — `DeterminismTest` matched `shared/determinism.c` while the real fault
    sat in `src/contact_solver.c`.
- **Coverage must earn the right to DROP a file.** The first failing test a
  runner reports may pass in isolation: Box2D's `MultithreadingTest` fails
  only in combination and covers 47 lines alone. Probing it produced
  coverage of two files, and the "drop what the failure never executed"
  rule then discarded the real defect file. Coverage is now the union over
  every failing test, and may only remove candidates when it covers at
  least five real files; below that it may reorder but never drop.
- C test runners have no pytest monoculture: cglm prints a cross mark and
  `assert fail in <file> on line <n>`, Box2D prints `test failed: MathTest`
  with no file or line anywhere. The parser handles both, and widens as new
  projects are guarded.


## 0.10.0 — 2026-09-03

- **A fifth machine-authored kernel: the SIGHT LAW.** The ranking law
  ordered *lines*; *file* order was still a hand-written blend in which a
  filename coincidence could outrank direct evidence. Measured on click
  8.5.1: a defect at `src/click/types.py:499` whose failing tests live in
  `tests/test_shell_completion.py` — and click HAS a `shell_completion.py`,
  so the NAMED lane fired for the wrong file. The defect file ranked 6th,
  then took a further penalty for being executed by every test.
  `src/fluidfix/sight.py` vendors the authored law verbatim (the C source is
  in `docs/laws/sight.c`): eight lanes in two tiers, with two rules that hold
  *algebraically* rather than by a comparison that could be written
  backwards —

      R1  POINTING evidence (FRAMED / SCARCE / LITERAL) outranks
          circumstantial evidence at any quantity.
      R2  the UBIQUITOUS penalty cannot reach a pointed-at file.

  Both the circumstantial sum and the penalty are ANDed with a gate that is
  identically zero whenever a pointing bit is set, so the inversion that cost
  the click search is *unrepresentable*, not merely tested against. Verified
  exhaustively: 0 violations on all 256 inputs, 1.22 ns per candidate file.
  `fluidfix selfcheck` now re-derives **five** laws.
- **SCARCE — the taught class is itself a localiser.** A signal regex that
  matches lines in only one or two files repo-wide has said where to look
  before a single candidate is tried. Broad signals name many files and are
  ignored, so the lane cannot hand out free promotions.
- **A refusal now names the right cause, and there are three.** Running out
  of clock with *no* pointing evidence is not the same as running out of
  clock with some, and they need opposite advice. Previously both got
  "raise the budget", which is right for one of them:

      vocabulary gap  candidates generated, all rejected  -> teach the class
      search limit    a POINTING lane named a file        -> more budget helps
      evidence gap    nothing pointed anywhere            -> name the file
                                                             (--file), or make
                                                             the failure carry
                                                             a locating value

  The escalation hint no longer asserts "the search space is real" when
  nothing pointed at anything — with no evidence the search order is
  arbitrary, and saying otherwise sent users to buy budget that could not
  help.
- **A missing pytest is no longer reported as a red suite.** `python -m
  pytest` exits 1 when pytest is absent — indistinguishable by exit code
  from a genuine failure. `fluidfix estimate` on this very repo, run by an
  interpreter without pytest, reported a confident "suite runtime: 0.03s"
  and blamed the user's suite for being red. The suite had never run.
  `_check_harness` now detects this, names the interpreter, and gives the
  `--python` fix — which protects `guard` and `repair` too.
- **`estimate` refuses rather than guesses.** It will not print a number
  when the suite did not actually execute: missing pytest, a harness error
  (exit 3/4/5), a suite timeout, or a run with no test results at all. For
  the timeout case the refusal *is* the answer, with the arithmetic shown.
- Measured, and published because it corrects an earlier claim in this
  project's own docs: `types.py:499` — no traceback frame, no discriminating
  literal, and a taught signal matching 3 files where SCARCE needs <= 2, so
  **no pointing lane fired at all** — repaired **byte-exact in 17 suite runs
  (87.1s)** once run uncapped. Earlier runs of that exact defect were
  reported as misses; they were capped at 420s and 600s, below the wall clock
  it needed. The absence of pointing evidence costs *search time*, not the
  repair. The engine law's CAPPED -> RAISE_BUDGET was correct and the
  operator was not.


## 0.9.1 — 2026-09-03

- **`fluidfix estimate` — know your number before you install.** Times your
  suite once and projects repair time from the model that independent
  third-party testing surfaced and this project confirmed:

      repair time ~= suite runs x (your suite's runtime + ~0.5s startup)

  **Test COUNT barely matters — your suite's RUNTIME is the entire bill.**
  105 tests running in 0.07s are cheaper to guard than 20 tests taking 5s.
  Validated against real repairs: the 105-test engine predicted 1.4-7s and
  repaired in 1.7s; click (1,990 tests, 4.5s) predicted 12.2-61s and
  repaired in 36s and 50s — both inside the band. It also tells slow-suite
  repos to guard a subset or run on `--interval`, and says plainly when the
  suite is already red.
- Credit where due: the scaling model came from an independent tester who
  built a 105-test game engine to probe the middle of the curve after being
  told the toy-project numbers were the easy regime.


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
