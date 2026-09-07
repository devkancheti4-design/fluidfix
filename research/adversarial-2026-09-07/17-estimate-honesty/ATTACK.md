# 17-estimate-honesty — attack report

Agent 17 of 20. fluidfix 0.14.0, `.venv/bin/fluidfix`, macOS 25.5.0 (arm64).
Everything below was run `nice -n 15`, one at a time, through `./run.sh SECS CMD...`
(a perl-alarm timeout wrapper; this machine has no coreutils `timeout`).
No fluidfix source, test, doc or law was edited, and no git state was changed.

## 1. Target

`fluidfix estimate` — the first command a prospective user runs. Attack the
honesty of the number it prints: find a number the actual run contradicts, a
refusal where a number was available, and a number given for a repo fluidfix
cannot in fact repair.

## 2. Attack design

`cmd_estimate` (src/fluidfix/cli.py:326-415) makes exactly one measurement —
one plain `pytest -q --no-header --tb=no` run — and then multiplies:

```
startup  = 0.5
per_run  = secs + startup
typical in-vocabulary defect (2-10 suite runs):  2*per_run .. 10*per_run
harder localisation (up to 80 runs):             80*per_run
"The arithmetic: time ~= runs x (suite time + startup). Nothing else
 in fluidfix costs measurable wall clock — the kernels decide in
 nanoseconds; your tests are the entire bill."
```

Three properties are attackable, and each maps to one of the three things the
task asked for:

* **The unit.** "suite runs" is assumed to be the number of candidates. It is
  not. `Oracle.check()` (oracle.py:184-238) spawns **two** pytest processes per
  candidate (the `--lf` fast gate, then the full suite), and `FLUIDFIX_CONFIRM`
  defaults to 1, so an accepted green costs **four**. Separately,
  `find_candidate_files` (guard.py:158-176) does **coverage** localisation runs
  (`--cov=. --cov-report=json`) that estimate never timed and whose existence
  its closing line denies. If the run count can be driven far above 80, the
  printed ceiling is false.
* **The body.** `_oracle(args)` (cli.py:47-51) hard-wires the **pytest** Oracle.
  `estimate` takes no `--build-cmd`/`--test-cmd` and has no language routing,
  while fluidfix ships `cguard` and `jguard`. A C project should therefore be
  refused a number that `COracle` could have measured — coracle.py:30-40 even
  states the same timing model for C.
* **The predicate.** estimate refuses "when the suite did not actually
  execute". Executing is not the property that makes a repo repairable —
  *pinning* is. A suite that runs and pins nothing should still get a number.

`cmd_estimate` contains no `decide`/`situation` call (verified by grep over
cli.py:326-415): the engine law is never consulted on this path, so no finding
here can be a `ruling`. They are all body defects.

## 3. Attempts

Seven repos, all built inside this directory under `repos/`, all green (or
building) before injection. Logs in `logs/`. Re-run with `sh reproduce.sh`.
`pyshim.sh` is a legitimate `--python` that appends each invocation to a log
and then execs the venv interpreter — it counts the **actual** pytest suite
runs, the unit estimate's arithmetic is denominated in. fluidfix is unmodified.

1. **r1_fast** — 2-test package, kind-0 (strictness) defect, `>` → `>=`.
   In vocabulary, repaired. *Baseline: does the band hold at all?*
2. **r2_slow** — same defect, plus a 1.2 s integration test.
   *Does a slow suite change the shape of the error?*
3. **r3_c** — CMake C project, library + `build/tests` binary, kind-0 defect in
   `src/clamp.c`. *Refusal where a number was available.*
4. **r4_oov** — out-of-vocabulary defect (a dropped multiplicand,
   `total += v * w` → `total += v`). *Number given, no repair delivered.*
5. **r5_many** — 20 files (`lib/core.py` + 18 equal-rank modules), kind-3
   defect (`+` → `-`) buried in `lib/mod17.py`, surfaced by a pure-assert
   failure so no traceback frame names a source file and the coverage spectrum
   path has to run. *Drive the run count past the printed 80-run ceiling.*
6. **r6_red** — byte-identical to r5 in its **red** state, so estimate prints
   its "NOTE: ... this is the realistic number". *Best case for estimate.*
7. **r7_smoke** — a repo with no tests. Follow estimate's own instruction:
   run `fluidfix init`, then estimate again, then inject a kind-0 defect.
   *Number given for a repo fluidfix cannot repair.*

### Attempts that FAILED — defences that held

* **Timeout refusal.** A suite exceeding `--suite-timeout` gets no number at
  all; `out.strip() == "TIMEOUT"` is checked before any arithmetic
  (cli.py:356). Could not get a number past it.
* **Missing pytest.** `_NO_PYTEST` (oracle.py:66-70) exists *because* of a
  previous estimate-honesty incident ("`fluidfix estimate` ... reported a
  confident 0.03s estimate and blamed the user's suite for being red. The suite
  had never run."). It holds.
* **No summary line.** With pytest exit 0 but no `N passed` line, estimate
  refuses rather than fabricating — "an estimate built on zero tests is a
  fabrication" (cli.py:380-388). r7 before `init` hit exactly this.
* **exit 3/4/5.** `_check_harness` refuses. r3_c and r7-before-init both
  refused here (correctly as to the pytest fact — see F2 for the part that is
  not correct).
* **The per-run cost itself is conservative, not optimistic.** `secs` already
  contains process startup and estimate then *adds* another 0.5 s. Every
  overrun below is in the RUN COUNT, never in the price of a run.
* **No S1 and no S2 anywhere.** `repos/r5_shim/lib/mod17.py` is byte-identical
  to the pristine correct file after the repair; `repos/r4_shim` still carries
  its injected defect untouched after the refusal; no repo was left holding a
  `.coverage`, a `_fluidfix_guard_cov.json` or a mutation. Only `.fluidfix/`
  and `.pytest_cache/` are added, both intended.

## 4. Outcome — predicted versus actual

`estimated` columns are what `fluidfix estimate` printed on that repo before the
run. `runs (said)` is fluidfix's own `repaired ... in N suite runs`. `runs
(real)` is pytest processes actually spawned, counted by `pyshim.sh`.

| # | repo | suite timed | estimate: typical in-vocab | estimate: ceiling ("up to 80 runs") | what the run actually did | actual wall clock | runs (said) | runs (real) |
|---|------|-----------|---------------------------|------------------------------------|---------------------------|-------------------|-------------|-------------|
| r1 | `r1_fast` | 0.23 s | **1.5 s – 7 s** | ~59 s | repaired (kind 0) | 4.16 s | 3 | **11** |
| r2 | `r2_slow` | 1.42 s | **3.8 s – 19 s** | ~153 s | repaired (kind 0) | 12.15 s | 3 | **11** |
| r3 | `r3_c` (C/CMake) | *refused: "pytest collected NO TESTS ... no tests in this root"* | — | — | `cguard` **repaired** `src/clamp.c:10` | 9.15 s | 7 | build+test oracle |
| r4 | `r4_oov` | 0.20 s | **1.4 s – 7 s** + "repairs will land in seconds" | ~56 s | **REFUSED** — outside the taught vocabulary | 3.07 s | — | 11 |
| r5 | `r5_many` | 0.20 s | **1.4 s – 7 s** | **~56 s** | repaired (kind 3) | **34.74 s** | 9 | **139** (118 of them `--cov`) |
| r6 | `r6_red` (= r5, red) | 0.20 s, **"this is the realistic number"** | **1.4 s – 7 s** | **~56 s** | same defect as r5 | **34.74 s** | 9 | **139** |
| r7 | `r7_smoke` after `fluidfix init` | 0.34 s | **1.7 s – 8 s** + "Ideal for the GitHub Action on every push" | ~67 s | guard: **"suite green — nothing to do"** — no defect in this repo is ever repairable | 0.39 s | — | 1 |

Three findings.

---

### F1 — S3 FALSE CONFIDENCE. The printed band and the printed ceiling are both contradicted, on the same repo, in the same state, by an in-vocabulary defect.

**Reproduction**

```sh
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/17-estimate-honesty
sh reproduce.sh r5
```

or by hand:

```sh
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/17-estimate-honesty
rm -rf $D/repos/r5_shim && cp -R $D/repos/r5_many $D/repos/r5_shim
sed -i '' 's/^    return x + 17$/    return x - 17/' $D/repos/r5_shim/lib/mod17.py
$D/run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix estimate $D/repos/r5_shim
FLUIDFIX_SHIM_LOG=$D/logs/f1.log; export FLUIDFIX_SHIM_LOG; : > $FLUIDFIX_SHIM_LOG
$D/run.sh 900 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard $D/repos/r5_shim --python $D/pyshim.sh
grep -c -- '-m pytest' $FLUIDFIX_SHIM_LOG      # 139
grep -c -- '--cov'     $FLUIDFIX_SHIM_LOG      # 118
```

**What estimate said** (`logs/estimate_r6_red.txt`, run on the red tree, so this
is estimate at its most favourable — it labels this number "realistic"):

```
  1 failed, 1 passed in 0.01s
  suite runtime: 0.20s  (+~0.5s pytest startup per run)

EXPECTED REPAIR TIME on this repo
  typical in-vocabulary defect (2-10 suite runs):  1.4s - 7s
  harder localisation (up to 80 runs):             ~56s
  ...
  The arithmetic: time ~= runs x (suite time + startup). Nothing else
  in fluidfix costs measurable wall clock — the kernels decide in
  nanoseconds; your tests are the entire bill.

  NOTE: your suite is currently RED, so this timing includes failing
  tests. fluidfix only acts on a red suite, so this is the realistic
  number.
```

**What the run did** (`logs/guard_r5.txt`, `logs/shim_r5.log`):

```
[14:40:00] lib/mod17.py: repaired line 9 in 9 suite runs (3.1s):
  - return x - 17
  + return x + 17
WALL_CLOCK_SECONDS = 34.74
pytest suite runs : 139   (118 --cov, 11 plain full-suite, 10 `-x --tb=long`)
```

The diff fluidfix wrote is the correct one — this is not a wrong repair:

```diff
--- a/lib/mod17.py
+++ b/lib/mod17.py
@@ -7,4 +7,4 @@
 def offset17(x):
-    return x - 17
+    return x + 17
```

**Why it is a finding.** The defect is squarely in vocabulary (kind 3,
flipped-additive) on a 20-file repo with a 0.01 s suite:

* predicted **1.4 s – 7 s**, actual **34.74 s** — 5.0x above the top of the band;
* predicted ceiling **80 runs / ~56 s**, actual **139 runs** — 1.7x above the
  stated absolute maximum, on a repo far smaller than anything estimate's
  docstring benchmarks (it cites 1,990 tests);
* the closing sentence "Nothing else in fluidfix costs measurable wall clock —
  ... your tests are the entire bill" is false here: **118 of 139 runs (85 %)**
  were coverage-instrumented localisation runs that estimate never timed;
* fluidfix's own report says "9 suite runs" for 139 pytest processes. The two
  numbers a user has — the estimate's `runs x per_run` and the report's
  `N suite runs` — use the same words for quantities 15x apart, so the user
  cannot reconcile them even after the fact. The same divergence is present in
  the passing cases: r1 and r2 each said 3 and each really ran 11.

**Classification: observation.** The law was never asked — `cmd_estimate`
contains no `decide`/`situation` call, so there is no observation byte and no
act to quote; this is a body-only path (this is emphatically not a `ruling`).
The body measured **one** plain suite run and delivered it as the whole cost
model. The two bits it never measured or delivered are:

* `Oracle.check()` = 2 pytest processes per candidate (oracle.py:203 fast gate,
  oracle.py:218 full suite), 4 for an accepted green with `FLUIDFIX_CONFIRM=1`;
* `find_candidate_files`'s spectrum path (guard.py:158-176) runs the suite twice
  under `--cov`, and does so again per file during escalation — 118 runs here.

Had those been measured, the honest line for this repo would have been roughly
`139 x 0.25 s ≈ 35 s`, which is what happened. The defect is entirely in what
was measured; the arithmetic on top of it is sound.

---

### F2 — S3. A refusal whose stated consequence is false, on a repo fluidfix repairs in 9 s.

**Reproduction**

```sh
sh reproduce.sh r3
```

**What estimate said** (`logs/estimate_r3_c.txt`):

```
timing your suite (one run, .../.venv/bin/python3.14)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in .../repos/r3_c ...
--- last output ---
no tests ran in 0.01s
```

and, on the identical shape of repo, the branch a user reaches when the tree has
no `.py` at all (`logs/estimate_r7_before_init.txt`) sends them to
`fluidfix init` — which for a C project would generate a Python import-smoke
file.

**What the same tree actually does** (`logs/cguard_r3.txt`):

```
  build: cmake --build build -j8
  test:  ./build/tests
[14:38:01] src/clamp.c: repaired line 10 in 7 suite runs (8.3s):
  - return amount >= limit;
  + return amount > limit;
WALL_CLOCK_SECONDS = 9.15
```

**Why it is a finding.** The brief says a refusal with a *correct* reason is not
an attack. The pytest fact is correct; the reason built on it is not. The
message asserts "the suite did not run, so there is nothing to time" and
"nothing can be judged" about a repo that has a full test suite, that fluidfix
judged 7 times, and that fluidfix repaired. The number was available and the
model for it is already written down in fluidfix's own source — coracle.py:30-40:
"repair time ~= suite runs x (build time + test time)", with measured cglm
figures. `COracle.build()` and `COracle.test()` are exactly the two timings
estimate would need. A prospective C/C++ user — the audience `cguard` exists
for — is told at the front door that their repo has nothing for fluidfix to be
judged by.

**Classification: observation.** The law is not on this path either. The body
measured the wrong oracle: `_oracle(args)` (cli.py:47-51) returns the pytest
`Oracle` unconditionally, and the `estimate` subparser (cli.py:746-749) takes
neither `--build-cmd` nor `--test-cmd`, so no C/Java measurement can be
requested even explicitly. "No pytest tests" was measured correctly and then
delivered as "no tests", which is a different claim.

---

### F3 — S3. A number, plus a sales line, for a repo in which fluidfix can repair nothing — reached by following estimate's own instruction.

**Reproduction**

```sh
sh reproduce.sh r7
```

**The sequence** (`logs/estimate_r7_before_init.txt`, `logs/r7_init.txt`,
`logs/estimate_r7_after_init.txt`, `logs/guard_r7.txt`):

1. `fluidfix estimate repos/r7_smoke` → refuses; the sibling branch at
   cli.py:384-387 is the one that names the remedy: "Run `fluidfix init` to
   generate a starter smoke suite, then estimate again."
2. `fluidfix init repos/r7_smoke` → `wrote test_fluidfix_smoke.py guarding
   3 module(s)`. The generated suite is a single parametrised
   `importlib.import_module(mod)` — import smoke, nothing else.
3. `fluidfix estimate repos/r7_smoke` now prints:

```
  3 passed in 0.01s
  suite runtime: 0.34s  (+~0.5s pytest startup per run)

EXPECTED REPAIR TIME on this repo
  typical in-vocabulary defect (2-10 suite runs):  1.7s - 8s
  harder localisation (up to 80 runs):             ~67s

  Fast suite: repairs will land in seconds. Ideal for the GitHub Action
  on every push.
```

4. Inject an in-vocabulary kind-0 defect into `app/invoice.py`
   (`if total > threshold:` → `if total >= threshold:`) and guard:

```
[14:38:49] suite green — nothing to do
WALL_CLOCK_SECONDS = 0.39
```

**Why it is a finding.** "typical in-vocabulary defect: 1.7 s – 8 s" is not a
slow number for this repo, it is a number for an event that cannot occur: an
import-smoke suite pins no value, so *every* in-vocabulary value defect leaves
it green and the guard correctly declines to act. Expected repair time is not
1.7–8 s; it is never. The command whose contract is "REFUSES to print a number
when the suite did not actually execute" (its own docstring) has the wrong
predicate: it checks that the suite *ran*, and the property that decides whether
a repair can ever land is whether the suite can *reject* anything. estimate then
adds a purchase recommendation ("Ideal for the GitHub Action on every push") on
top of it. Note that fluidfix is honest about this everywhere else — the
generated file's own header says "import smoke can't see a wrong *value*", and
`cmd_init` prints the paste trick. `estimate` is the one place that does not
know.

**Classification: observation.** No law on this path. The body had the
discriminating evidence in hand and did not deliver it: `summary` at
cli.py:375-379 already holds the pass/skip counts, and `cmd_init` knows it just
wrote a file whose only assertion is an import. A single measured bit — does
this suite contain any assertion beyond import, or (stronger, and cheap on a
0.34 s suite) does a trivial mutation of a guarded module turn it red — would
separate "fast suite, repairs land in seconds" from "fast suite, nothing here
can ever be repaired".

---

## 5. What defended

* **Refuse-rather-than-guess is real and load-bearing.** Four separate gates
  fired against me: `TIMEOUT` (cli.py:356), `_NO_PYTEST` (oracle.py:66-70,
  itself the scar from a prior estimate-honesty incident), `_check_harness`
  exits 3/4/5, and the empty-`summary` branch (cli.py:380-388). I could not get
  a fabricated number past any of them. Every number I did obtain came from a
  suite that had genuinely executed.
* **The per-run price is deliberately pessimistic.** `secs` already includes
  process startup, and estimate adds 0.5 s again. Every overrun I found is in
  the run COUNT; the cost of one run is never understated.
* **Integrity held completely.** No S1 and no S2. `repos/r5_shim/lib/mod17.py`
  is byte-identical to the pristine correct file; `repos/r4_shim/pkg/stats.py`
  still holds its injected defect after the refusal, unmodified; the accepted
  repairs are byte-exact single-line edits; no `.coverage`, no
  `_fluidfix_guard_cov.json`, no stale journal was left in any of the seven
  repos (evidence: `logs/integrity.txt`). One artefact worth noting for
  whoever owns integrity: `cguard` leaves a `covbuild/` directory behind in
  the guarded C repo (`repos/r3_shim/covbuild`). It is an added build tree,
  not a mutation of anything the user had, so I am not scoring it — flagging
  it for agents 11/13/20.
* **The guard's own refusals were honest** in every case I produced: r4's
  "outside the taught vocabulary" was true (a dropped multiplicand is in no
  fault class) and it named the file it tried; r7's "suite green — nothing to
  do" is exactly right. The dishonesty is upstream, in `estimate`, not in the
  guard.
* **`--tb=no` timing matched the real full-suite runs closely** — the plain
  full-suite runs inside the guard cost what estimate measured. The model's
  price is right; only its quantity and its scope are wrong.

## 6. Verdict

fluidfix's *repair* path held — no wrong repair, no corruption, and every
guard-side refusal named its true cause — but `fluidfix estimate` did not: on
r5/r6 it promised 1.4–7 s and an 80-run ceiling for an in-vocabulary defect that
actually cost 34.74 s and 139 suite runs (S3, observation), it refused a C repo
`cguard` then repaired in 9.15 s (S3, observation), and after its own
`fluidfix init` advice it sold a repair-time number for a repo where no repair
can ever land (S3, observation).
