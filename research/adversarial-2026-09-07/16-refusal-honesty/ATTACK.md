# 16-refusal-honesty — do fluidfix's refusals state the real cause?

fluidfix 0.14.0 · /Users/kanchetidevieswar/neo/fluidfix/.venv · 2026-09-07 ·
20 refusals collected across Python (`guard`, `repair`) and C (`cguard`).

## 1. Target

Collect >= 15 refusals across Python and C and check each STATED reason against
what actually happened in that run. Any refusal whose stated reason is not the
real cause is an S3 (false confidence).

## 2. Attack design

A refusal is a claim about the run. fluidfix makes that claim in three places
that are wired together only loosely:

* `loop.repair()` computes the honest per-file reason (`RepairResult.reason`)
  and records `greens`, `tried_more`, `acts_tried`.
* `guard.guard_once()` / `coracle.cguard_once()` decide the pass-level `hint`.
  They read `result.repaired` and `result.ambiguous` and **nothing else** —
  `result.reason`, `result.greens` and `result.tried_more` are dropped on the
  floor for every non-ambiguous refusal.
* `GuardReport.summary()` writes the HEADLINE the user reads. It picks its
  branch from two substring/emptiness tests on fields the caller may never
  have filled: `"budget exhausted" in hint` and `evidence["pointed"]`.

So the attack is: engineer runs where the true cause is measured in layer 1 and
is *structurally unable* to reach layer 3, and check what layer 3 says instead.
Three cheap levers do it — a wall clock (`--budget`), a search that finds a
green before it finishes, and a candidate count above `loop.py`'s 64-entry
`tried_log` cap.

All measurements are taken with fluidfix's own public API used as an
instrument (`bin/probe_*.py`): `Oracle`/`COracle`, `build_packet`,
`MechanicalObserver`, `rank_observations`, `loop.repair`, all called exactly
as the guards call them, with the same deadline arithmetic. **No fluidfix
source was edited, monkeypatched, or disabled, and no FLUIDFIX_* variable was
set.** Every invocation ran under `bin/run` = `nice -n 15` + a `perl` alarm
wrapper (this machine has no coreutils `timeout`), one at a time.

## 3. Attempts

Logs for every run are in `logs/`. "Honest" = the stated reason matches what
the run did; those are fluidfix working and are NOT findings.

| # | run | stated reason (headline / hint) | verdict |
|---|-----|------|---------|
| 1 | `repair py01_green` | "suite is green — nothing to repair (refusing to search)" | honest |
| 2 | `guard py02_outofvocab` | "fault is outside the taught vocabulary" | **honest** — 0 acts, `return sorted(xs)` matches no KIND signal |
| 3 | `repair py02_outofvocab` | "no observation named a kind this vocabulary can repair" | honest |
| 4 | `guard py03_amb_two_sites` | headline "fault is outside the taught vocabulary … teach it once"; hint "AMBIGUOUS: 2 candidates at 2 different lines" | **FALSE headline (F6)** — two candidates PASSED; the class is in-vocabulary |
| 5 | `guard py04_amb_one_site_spell` | repaired (`>= 11` → `>= 10`) | not a refusal |
| 6 | `guard py05 --budget 30` | headline "outside the taught vocabulary"; hint "every generated candidate was rejected by the suite" | **FALSE (F1)** — `r = b - a` passed |
| 7 | `guard py05 --budget 1` | "nothing in the failure pointed at a file … The failure pointed at pkg/mod.py … Files searched: pkg/mod.py" | **FALSE in two clauses (F7)** — zero files searched; FRAMED lane empty, SCARCE fired |
| 8 | `guard py05 --budget 3` | "fault is outside the taught vocabulary … teach it once" | **FALSE (F2)** — clock, not vocabulary |
| 9 | `guard py05 --budget 6` | same | **FALSE (F2)** |
| 10 | `probe repair py05 deadline=10s` | "a candidate passes, but the search was cut short before it could be shown unique … (engine law: BUILT+CAPPED -> RAISE_BUDGET)" | honest — and thrown away by the guard |
| 11 | `probe repair py05 deadline=2s` | "wall-clock deadline reached mid-search — remaining observations untried" | honest — and thrown away by the guard |
| 12 | `guard py08_many_rejections` | "outside the taught vocabulary" + REFUTED hint, "62 candidate(s) tried and rejected" | honest (62 < the 64 cap) |
| 13 | `guard py08b_over64` | "64 candidate(s) were tried and rejected — each is logged with the test that failed it" | **FALSE count (F5)** — 124 were tried and rejected |
| 14 | `probe repair py08b` | "every candidate left the suite red — fault is outside this vocabulary" | honest |
| 15 | `guard py09_no_tests` | `HarnessError: pytest collected NO TESTS (exit 5) … nothing can be judged` | honest content, but raised as an **uncaught traceback, exit 1** (documented: 2 = refused) |
| 16 | `cguard c01_frame --budget 2` | "nothing in the failure pointed at a file — no traceback frame, no discriminating literal … Files searched: src/mathops.c, src/util.c … name the file yourself (--file <path>)" | **FALSE in three clauses (F3)** |
| 17 | `cguard c02_capped_green --budget 3` | "fault is outside the taught vocabulary … teach it once" | **FALSE (F2, C form)** — clock; 0 candidates tried |
| 18 | `cguard c02_capped_green --budget 15` | "outside the taught vocabulary"; JSON hint "fault class is outside the taught vocabulary; register() it once" | **FALSE (F4)** — `int r = a + b;` passed |
| 19 | `probe repair c02 deadline=15s` | "a candidate passes, but the search was cut short … BUILT+CAPPED -> RAISE_BUDGET" | honest — never reaches the user |
| 20 | `cguard c03_outofvocab` | "outside the taught vocabulary" (`a * b`, 1 candidate rejected) | honest |

Attacks that did **not** work are in section 5.

Integrity check on every run above: the defect file's md5 after the refusal
equalled the pristine md5 (`pristine/` holds the reference copies). No S1 and
no S2 was produced by any of these runs.

## 4. Outcome

### F1 — S3 — Python: "every generated candidate was rejected by the suite", with a green in hand

Reproduce:

```sh
cd 16-refusal-honesty/fixtures/py/py05_capped_green
cp ../../../pristine/py05_mod.py pkg/mod.py
../../../bin/run 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . --budget 30
```

Output (`logs/py05.budget30.log`):

```
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/mod.py).
teach it once: docs/TEACHING.md (or run: fluidfix kinds) 5 candidate(s) were tried
and rejected — each is logged with the test that failed it in the refusal report.
  hint: every generated candidate was rejected by the suite
        (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) — the refusal report
        lists each one with the test that killed it
```

What actually happened, from `loop.repair()` at the identical deadline
(`bin/probe_capped.py`, `logs/py05.probe.log`):

```json
{"repaired": false, "ambiguous": false,
 "reason_repair_produced": "a candidate passes, but the search was cut short
   before it could be shown unique — shipping it would be a guess. Raise the
   budget and re-run (engine law: BUILT+CAPPED -> RAISE_BUDGET)",
 "greens_len": 1, "greens": ["    r = b - a"], "rejected": 9}
```

`r = b - a` is the correct repair (the unbudgeted run ships exactly it —
`logs/py05.baseline2.log`). The refusal report's own `rejected_candidates`
corroborates the contradiction: line 2 produced two candidates and only
`r = a + b` is listed as rejected. There is no diff: the tree is restored
byte-exactly (md5 identical). The damage is the claim, and the advice —
the user is told to teach a fault class, when the law's ruling on the true
situation is RAISE_BUDGET.

**Classification: observation.** `guard.py:519` sets `acts0` from
`result.acts_tried` ("candidates were generated") and never reads
`result.greens`, which `loop.py:220` had already filled. `capped0`
(`guard.py:508,538`) is measured only from `packet.truncated` and the
candidate-file count, never from the deadline that actually cut the search.

* observation byte passed (`guard.py:617-619`): `situation(REFUTED=True)` =
  `0x0240` → law returns **HARVEST_COUNTEREXAMPLE** → "every candidate was
  rejected".
* byte the run supports: `situation(BUILT=True, CAPPED=True)` = `0x0221` →
  law returns **RAISE_BUDGET** → "raise the budget and re-run".
* The law ruled correctly on the byte it was handed. This is not a `ruling`.

### F2 — S3 — Python and C: a clock-limited refusal reported as a vocabulary gap

Reproduce (Python):

```sh
cd 16-refusal-honesty/fixtures/py/py05_capped_green
cp ../../../pristine/py05_mod.py pkg/mod.py
../../../bin/run 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . --budget 6
```

Output (`logs/py05.budget6.log`) — note there is no hint at all, and the
machine-readable report says the same thing:

```
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/mod.py).
teach it once: docs/TEACHING.md (or run: fluidfix kinds)
.fluidfix/last_refusal.json → "hint": "fault class is outside the taught
   vocabulary; register() it once and its family becomes free",
                              "rejected_candidates": []
```

`loop.repair()` at the same deadline (`logs/py05.probe.budget6.log`) returned
`"wall-clock deadline reached mid-search — remaining observations untried"`,
0 candidates tried. The fault is kind 11 (`reversed-minus-operands`), shipped
vocabulary, and the unbudgeted run repairs it. The word "budget" appears
nowhere in the refusal.

The C form is #17: `bin/c02_cmd.sh --budget 3` (`logs/c02.b3.log`) gives the
same headline with `rejected_candidates: []` after 3.9 s, because
`cguard_once` (`coracle.py:770`) returns a `GuardReport` with **no hint at
all** on its final path — so `summary()` can only reach its `else` branch.

This is the exact misdiagnosis `guard.py:60-67` documents as fixed
("Blaming the vocabulary sends the user to write a rule they already have").
The fix only covers the two `budget exhausted` hints; a deadline consumed
*inside* `repair()` never produces one.

**Classification: observation** (the CAPPED bit is measured inside `repair()`
and never delivered upward) presenting as **wording**. Byte the run supports:
`situation(CAPPED=True)` = `0x0220` → **RAISE_BUDGET**. Byte used: none — no
law is consulted, `summary()` falls through to its `else` branch.

### F3 — S3 — C: "nothing in the failure pointed at a file — no traceback frame", when two frames are printed and were used

Reproduce:

```sh
16-refusal-honesty/bin/c01_cmd.sh --budget 2
```

The failing test binary prints (verbatim):

```
src/mathops.c:3: assertion failed: addv(2,3) == 5 (got -1)
src/util.c:3: note: scale2 gave -2
test failed: MathopsTest
```

fluidfix says (`logs/c01.b2.log`):

```
REFUSED: nothing in the failure pointed at a file — no traceback frame, no
discriminating literal, no taught signal narrow enough to localise. The ranking
had only circumstantial evidence, so a bigger budget searches the same files in
the same order. Files searched: src/mathops.c, src/util.c. What helps, in order:
name the file yourself (--file <path>); …
  hint: --budget exhausted (2s)
```

Three false clauses in one refusal:

1. "no traceback frame" — `coracle._FRAME` matched both printed frames;
   `find_candidate_files_c` built the candidate list *from those frames*, in
   that order — `bin/probe_capped_c.py` on this tree prints
   `"candidates_from_frames": ["src/mathops.c", "src/util.c"]`
   (`logs/c01.probe.log`).
2. "Files searched: src/mathops.c, src/util.c" — `src/util.c` was never
   searched; the deadline fired at the top of its iteration
   (`coracle.py:750`).
3. "name the file yourself (--file <path>)" — `fluidfix cguard` has no
   `--file` option. The advice cannot be followed.

**Classification: observation.** `cguard_once` never populates
`GuardReport.evidence`, so `summary()` (`guard.py:70`) reads `pointed == []`
and takes the "no evidence at all" branch **unconditionally on every C
budget refusal**. The law is not involved: this branch is pure `if`.
Consequence: on C, the "third cause" message can never be true-by-measurement
— it is emitted whenever a C pass runs out of budget, regardless of evidence.

### F4 — S3 — C: green in hand, reported as a vocabulary gap

Reproduce:

```sh
16-refusal-honesty/bin/c02_cmd.sh --budget 15
```

Output (`logs/c02.b15.log`):

```
REFUSED: fault is outside the taught vocabulary (candidate files tried:
src/mathops.c). teach it once: docs/TEACHING.md … 14 candidate(s) were tried
and rejected …
.fluidfix/last_refusal.json → "hint": "fault class is outside the taught
   vocabulary; register() it once and its family becomes free"
```

`loop.repair()` at the same deadline (`logs/c02.probe.log`):

```json
{"reason_repair_produced": "a candidate passes, but the search was cut short
   before it could be shown unique … (engine law: BUILT+CAPPED -> RAISE_BUDGET)",
 "greens_len": 1, "greens": ["    int r = a + b;"]}
```

`int r = a + b;` is the correct repair (`logs/c02.baseline.log` ships exactly
it, 62 suite runs). Same byte analysis as F1; on C it is worse, because
`cguard_once` supplies no hint at all, so the *only* thing the user sees is
"teach it once".

### F5 — S3 — Python: "64 candidate(s) were tried and rejected — each is logged with the test that failed it"

Reproduce:

```sh
cd 16-refusal-honesty/fixtures/py/py08b_over64
cp ../../../pristine/py08b_mod.py pkg/mod.py
../../../bin/run 900 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard .
../../../bin/run 900 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
    ../../../bin/probe_counts.py . pkg/mod.py
```

Report says 64; the run tried and rejected **124** (`logs/py08b.probe.log`:
`tried_log_len 64, tried_more 60, actually_rejected 124, suite_runs 125`).
"each is logged with the test that failed it" is false for 60 of them.
`loop.py:61` measures `tried_more` precisely and neither `GuardReport` nor
`write_refusal()` carries it. **Classification: observation** (a measured bit
never delivered) surfacing as a wrong number in the report.

Related, smaller, same message: `tried_log` entries whose `why` is a compile
error ("does not compile: …", `loop.py:349`; on C, `…: error: use of
undeclared identifier`, seen in `logs/c02.b15.log`'s report) are counted in
"each is logged with the **test** that failed it" although no test ever ran.

### F6 — S3 — Python: every AMBIGUOUS refusal is headlined as a vocabulary gap

Reproduce:

```sh
cd 16-refusal-honesty/fixtures/py/py03_amb_two_sites
../../../bin/run 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard .
```

Output (`logs/py03_amb_two_sites.guard.log`):

```
REFUSED: fault is outside the taught vocabulary (candidate files tried: pkg/mod.py).
teach it once: docs/TEACHING.md (or run: fluidfix kinds) …
  hint: AMBIGUOUS: 2 candidates at 2 different lines (2, 4) all pass the suite …
        Add one pinning test (engine law: BUILT+AMB -> ADD_STATE, never guess)
```

The headline and its remedy contradict the hint on the next line: two
candidates from the taught vocabulary passed the suite, so the fault is
demonstrably *inside* it, and teaching a new class cannot resolve ambiguity.
`summary()` has no AMB branch — `exhausted` is false, so it falls to `else`.
CI and any log-scraper key on the headline. **Classification: wording**
(the refusal itself is correct and the law's ADD_STATE ruling is right).

### F7 — S3 (minor) — Python: "Files searched" names files that were not searched; "the failure pointed at" names a lane the failure did not fire

`guard py05 --budget 1` (`logs/py05.budget1.log`) claims "Files searched:
pkg/mod.py" after refusing at `guard.py:496` — before any packet was built
(`rejected_candidates: []`, 1.68 s elapsed, all of it the baseline suite run).
It also says "The failure pointed at pkg/mod.py, so more clock genuinely
helps", but `bin/probe_evidence.py` (`logs/py05.evidence.log`) shows
`FRAMED: []`, `SCARCE: ["pkg/mod.py"]` — the *taught class signal* pointed,
not the failure, and in a one-source-file repo the SCARCE lane fires
unconditionally. **Classification: wording.**

## 5. What defended

* **The repair loop's own reasons are accurate.** Every reason
  `loop.repair()` produced in 20 runs matched the run exactly, including the
  two hardest ones (BUILT+CAPPED with a green in hand, and the mid-search
  deadline). Everything in section 4 is a delivery failure above it, not a
  measurement failure inside it. The law was never wrong on the byte it got:
  **no `ruling` defect was found.**
* **The AMB refusal itself held.** The compensating two-site repair
  (`py03`) was found, recognised, and refused with the right remedy in the
  hint. I could not make it ship.
* **Byte-exact restore held under every refusal.** md5 of the defect file
  before and after was identical in all 20 runs, including the ones killed
  mid-search by a budget. No S2.
* **`_still_reports_failures` / `_fail_names` cross-examination** — I did not
  attempt an oracle-silencing candidate (target 01/02), but the C
  `check()` path rejected nothing spuriously here.
* **The "budget exhausted" fix works where it is wired.** On the Python path
  a `--budget` expiry *at the candidate-file loop* does produce a search-limit
  headline (#7). The gap is that a deadline consumed *inside* `repair()`
  produces no hint, and that C never fills `evidence`.
* **A green suite is refused before any search** (#1), and a genuinely
  out-of-vocabulary fault is named correctly on both languages (#2, #3, #20).
  Those refusals are fluidfix working and are reported as such.

Not reproduced / did not land:
* No refusal message was found that could be turned into a *wrong repair*
  (S1). Refusal honesty is a reporting surface; the acceptance gate is
  untouched by all of it.
* `tried_more` could not be pushed into `write_refusal`'s 200-entry cap
  interacting badly — the 64-entry `tried_log` cap bites first, so the 200
  never matters.

## 6. Verdict

fluidfix's *decisions* held — no wrong repair, no corruption, no bad ruling —
but its refusal reporting did not: seven refusal messages state a cause the run
contradicts, the worst being that a pass holding a suite-passing repair reports
"every generated candidate was rejected by the suite" (Python) or "fault is
outside the taught vocabulary" (C), because `guard_once`/`cguard_once` never
read `RepairResult.greens`, `.reason` or `.tried_more` and `cguard_once` never
fills `GuardReport.evidence`.
