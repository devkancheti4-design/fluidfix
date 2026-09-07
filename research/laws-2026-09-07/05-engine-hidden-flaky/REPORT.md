# 05-engine-hidden-flaky

## 1. Target
Build a flaky test fixture; measure the false-accept rate with `FLUIDFIX_CONFIRM=0,1,2`
over >= 30 runs each; report what `CHANGE_GRANULARITY` actually does in the body today.

## 2. Method

**Inventory of the earlier interrupted work in this directory, done first.**
`results_fixture_a.jsonl` held exactly 150 records, 50 per CONFIRM level, run indices
0-49 with no gaps. Each record was cross-checked against the surviving copy tree: for all
150 runs the second line of `runs/fixture_a/c<N>/r<NNN>/calc.py` matches the label in the
JSONL (**0 mismatches**), and 150 run directories exist. Recorded wall time totals 308.5 s
for 150 runs (means 1.61 / 2.13 / 2.43 s at CONFIRM 0/1/2), which is the right order for a
2-test pytest suite — so this file is trustworthy and the "finished too fast" suspicion
does not apply to it. `results_fixture_a_PRIOR_INTERRUPTED.jsonl` (89 records) and
`sweep_PRIOR_INTERRUPTED.log` are the first, abandoned attempt; **no number in this report
uses them**. `fixture_b` had **zero** runs on arrival, and no replication batches existed;
those are new work here, as are findings F3-F9.

Read (nothing outside this directory was modified):

- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/engine.py` (docstring spec, `BITS`, `ACTS`, `LAW`)
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/loop.py` 94-107 (`_confirm_runs`), 185-245
  (`_rule`), 300-410 (candidate loop, confirm loop, the HIDDEN site), 422-431 (final refusal wording)
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/oracle.py` 185-248 (`check`, `failing_output`)
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py` 485-545, 598-625
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/acts.py` 30-52 (`SpanEdit`)
- `/Users/kanchetidevieswar/neo/fluidfix/tests/test_law_never_ruled_wrong.py` 25-53
- `/Users/kanchetidevieswar/neo/fluidfix/CHANGELOG.md` 0.13.0 (55-80) and 0.7.0 (468-490)

Ran (all under `nice -n 15`, one at a time; the 300 s cap is enforced by
`subprocess.run(timeout=300)` because macOS has no `timeout` binary — noted in
`run_flaky.py`). 426 end-to-end `fluidfix repair` runs in total.

| script (all in this directory) | what it does | output |
|---|---|---|
| `fixture_sanity.py` | per-variant pytest green rate on both fixtures, 20 runs each | `fixture_sanity.out` |
| `run_flaky.py fixture_a 50 0 1 2` | 150 runs (the inventoried batch) | `results_fixture_a.jsonl`, `sweep_a.log` |
| `TAG=_rep0 run_flaky.py fixture_a 50 0` | replication batch | `results_fixture_a_rep0.jsonl`, `sweep_a_rep_c0.log` |
| `TAG=_rep1 run_flaky.py fixture_a 50 1` | replication batch | `results_fixture_a_rep1.jsonl`, `sweep_a_rep_c1.log` |
| `TAG=_rep  run_flaky.py fixture_a 50 2` | replication batch | `results_fixture_a_rep.jsonl`, `sweep_a_rep_c2.log` |
| `run_flaky.py fixture_b 30 0 1 2` | 90 runs | `results_fixture_b.jsonl`, `sweep_b.log` |
| `PYWRAP=1 run_flaky.py fixture_a 12 0 1 2` | 36 runs with every interpreter call logged by `pywrap.sh` | `results_fixture_a_wrapped.jsonl`, `pytest_cost*.out` |
| `pool.py` | pools the four fixture_a batches | `pooled_fixture_a.out` |
| `summarize.py fixture_a|fixture_b` | outcome tables | `summary_fixture_b.out` |
| `engine_hidden_lanes.py` | all 128 HIDDEN=1 situations through `decide()` | `engine_hidden_lanes.out` |
| `actuation_static.py` | AST: does the HIDDEN ruling reach control flow? | `actuation_static.out` |
| `hidden_never_reaches_final_ruling.py` | AST: which bits each `situation(...)` site passes | `hidden_never_reaches_final_ruling.out` |
| `ruling_is_not_branched.py` | monkeypatches `loop.decide` in-process to force HIDDEN -> SHIP | `ruling_is_not_branched.out` |
| `model.py` | analytic expectation from the code paths read | `model.out` |

### Fixtures (built here; the repo has none)

`grep -rln "flaky\|random" tests/` in the fluidfix repo returns only
`tests/test_law_never_ruled_wrong.py` and `tests/test_router_law.py`. **The flaky fixture
behind CHANGELOG 0.13.0's "7 of 50" is not in the repository**, so both fixtures here were
built from the shape the CHANGELOG describes and are mine, not reproductions of theirs.

- `fixture_a/` — flakiness **correlated with the code**. `test_add_sign_anchor` is
  deterministic and weak (red on the defect `a - b`, green on the wrong repair `b - a` and
  on the right one `a + b`); `test_add_value_flaky` skips its assert half the time and is
  the only test that separates `b - a` from `a + b`. Measured green rates
  (`fixture_sanity.out`): defect 0/20, `b - a` 12/20, `a + b` 20/20.
- `fixture_b/` — flakiness **independent of the code** (a timing test's shape).
  `test_add_anchor` is deterministic and strong; `test_add_noisy` fails about half the time
  on any code. Measured: defect 0/20, `b - a` 0/20, `a + b` 10/20. The only wrong outcome
  available here is a refusal of the *correct* repair.

## 3. Findings

### F1. False-accept rate on a code-correlated flaky suite: 52% / 7% / 4% at CONFIRM 0/1/2 (300 runs, 100 per level)

Command: `nice -n 15 .venv/bin/python pool.py` over the four batches above.

```
fixture_a, pooled over 4 batches: 300 runs

CONFIRM    N  CORRECT  FALSE_ACCEPT  false-accept rate  HIDDEN fired
      0  100       48            52              52.0%             0
      1  100       93             7               7.0%            43
      2  100       96             4               4.0%            38

per-batch, to show the batch-to-batch spread:
  CONFIRM=0: (first)=26/50  _rep0=26/50
  CONFIRM=1: (first)=3/50  _rep1=4/50
  CONFIRM=2: (first)=0/50  _rep=4/50
```

A "false accept" is `fluidfix repair` shipping `return b - a` where the intended repair is
`return a + b`; every label is confirmed against the file left on disk in the run's own
copy tree.

**The lane reduces false accepts by roughly an order of magnitude; it does not remove
them.** This is the one place my measurement contradicts a published number. CHANGELOG
0.13.0 (lines 68-70) states that wiring the lane "took the false-accept rate to **0 of 49
and 0 of 46**". My first CONFIRM=2 batch also gave 0 of 50 — and its replication gave 4 of
50. Pooled, CONFIRM=1 is 7/100 and CONFIRM=2 is 4/100, neither distinguishable from the
other at this n. The reason is structural, not incidental: a re-check is another sample of
the same lying oracle, so `model.py` derives P(false accept) = q^(1+2N) for a suite green
with probability q on a wrong candidate — 50% / 12.5% / 3.1% for q=0.5 — which decays but
never reaches zero. Measured 52% / 7% / 4% against that model. A single 50-run batch
cannot tell 3% from 0%; the report of "0" is a sample, not a rate.

### F2. On a suite whose flakiness is independent of the code, the same lane destroys correct repairs at the same exponential rate: 50% -> 10% -> 3.3% (90 runs)

Command: `nice -n 15 .venv/bin/python run_flaky.py fixture_b 30 0 1 2`, then
`.venv/bin/python summarize.py fixture_b` (`summary_fixture_b.out`):

```
fixture_b: 90 runs
CONFIRM   N  CORRECT FALSE_ACC REF_AMB REFUSED GREEN_AB other | hidden fired
      0  30       15         0       0      15        0     0 |            0
        false-accept rate = 0/30 = 0.0%   correct-repair rate = 15/30 = 50.0%
      1  30        3         0       0      27        0     0 |           13
        HIDDEN fired on: {'return a + b': 13}
      2  30        1         0       0      29        0     0 |           12
        HIDDEN fired on: {'return a + b': 12}
```

Here HIDDEN fires **only on the correct candidate**. `model.py` predicts a correct-repair
rate of `(1-r)^(1+2N)` = 50% / 12.5% / 3.1%; measured 50% / 10% / 3.3%. So the confirm loop
is not a filter that separates luck from truth — it is the same exponential decay applied
to *every* candidate, and which candidate it kills depends only on whether the flakiness
correlates with the code. Both fixtures are the situation the law calls HIDDEN and rules
`CHANGE_GRANULARITY` on; the body applies "reject" to both (F3).

### F3. The HIDDEN ruling is computed and then discarded — the body branches on its own boolean

Two independent proofs.

(a) Static, `.venv/bin/python actuation_static.py` (`actuation_static.out`):

```
loop.py:391  in repair(): `ruling = decide(...)`
   reaches an if/while test at: NOWHERE
   reaches an f-string at     : [393]
   => NOT ACTUATED: the ruling reaches the WORDING only
loop.py:217  in _rule(): `ruling = decide(...)`
   reaches an if/while test at: [221]
   reaches an f-string at     : [228, 233, 240]
   => ACTUATED: control flow depends on the ruling
```

`src/fluidfix/loop.py:386-397` sets `ok = False` unconditionally inside `if fine_disagree:`;
`ruling` appears only inside the `why` f-string.

(b) Dynamic, `.venv/bin/python ruling_is_not_branched.py` (`ruling_is_not_branched.out`) —
`fluidfix.loop.decide` is monkeypatched **in that process only** (no src/ file touched) so
the HIDDEN situation rules `SHIP`:

```
--- decide patched for HIDDEN: True ---
  repaired: False | refused: True | greens: []
  rejected: return b - a | green on one run, RED on re-check ... (engine law: HIDDEN -> SHIP). last ...
VERDICT: with the HIDDEN ruling forced to SHIP the candidate is STILL REJECTED
         -> the body branches on fine_disagree; the ruling only reaches the message.
```

Forcing the law to rule `SHIP` changes the *message* and nothing else. At this site
"CHANGE_GRANULARITY" is a label printed on a decision the code has already made.

### F4. The HIDDEN bit never reaches the ruling that ends a search — so `CHANGE_GRANULARITY` can never be a search's outcome

Command: `.venv/bin/python hidden_never_reaches_final_ruling.py`
(`hidden_never_reaches_final_ruling.out`):

```
every situation(...) the body builds, with the bits it passes:
  loop.py:217  situation(BUILT, AMB, CAPPED)
  loop.py:391  situation(HIDDEN)   <-- HIDDEN
  guard.py:491  situation(UNREAD)
  guard.py:539  situation(CAPPED, REFUTED)
  guard.py:618  situation(REFUTED)
  guard.py:612  situation(REFUTED)

  REFUTED alone            -> HARVEST_COUNTEREXAMPLE    (what guard.py:612/618 asks today)
  REFUTED+HIDDEN           -> CHANGE_GRANULARITY    (the situation as measured)
  BUILT+HIDDEN             -> CHANGE_GRANULARITY
  BUILT alone              -> SHIP    (what loop.py:217 asks when a coarse green survives)
```

`loop.py:391` is the only site that sets HIDDEN, and it is per candidate and thrown away.
The search-ending ruling at `loop.py:217` is asked with `BUILT/AMB/CAPPED` only, and it is
asked *at all* only when `greens` is non-empty — a search in which the HIDDEN lane rejected
every candidate leaves `greens` empty, `_rule()` returns `None`, and **the law is not
consulted**. The guard then asks `situation(REFUTED=True)` and is told
`HARVEST_COUNTEREXAMPLE`. Had the already-measured HIDDEN bit been carried up, the same law
would have ruled `CHANGE_GRANULARITY` on the same search. That is one bit of plumbing, not
a new decision.

### F5. The refusal a flaky suite produces says something false

All 56 refusals across fixture_b's CONFIRM=1/2 runs carry this top-level reason (grouped
from `results_fixture_b.jsonl`; source `src/fluidfix/loop.py:427-430`):

```
27 (1, 'REFUSED', 'every candidate left the suite red — fault is outside this vocabulary or the observations are wrong')
29 (2, 'REFUSED', 'every candidate left the suite red — fault is outside this vocabulary or the observations are wrong')
```

In 12 of the 30 CONFIRM=2 runs the correct candidate went **green** and was then rejected
on re-check — it did not "leave the suite red", and neither the vocabulary nor the
observations were wrong. The true sentence ("the suite does not hold still here") exists
only inside `res.tried_log[i]["why"]`; it never reaches `res.reason`, and the guard-level
hint (`guard.py:613-621`) repeats the same REFUTED wording. The code comment at
`loop.py:386-390` records this as deliberate: "not recorded in `acts_tried` — ... the ruling
reaches the user through `why`".

### F6. `suite_runs` under-reports actual full-suite executions by 44% at CONFIRM=1 and 83% at CONFIRM=2

Command: `PYWRAP=1 nice -n 15 .venv/bin/python run_flaky.py fixture_a 12 0 1 2`, with
`pywrap.sh` passed as `--python` so every interpreter invocation is logged from outside the
process (`pytest_cost_breakdown.out`):

```
CONFIRM  n  mean FULL-suite runs  mean --lf fast-gate runs  mean baseline(-x)  | fluidfix reports suite_runs=
      0  12         3.00                  3.00               1.00   | 3
      1  12         4.33                  4.42               1.00   | 3
      2  12         5.50                  5.75               1.00   | 3
```

`res.suite_runs += 1` at `src/fluidfix/loop.py:355` counts candidates *written*, once,
before `oracle.check()`; the confirm re-checks at `loop.py:382-384` call `oracle.check()`
again and never increment it. The number is exact at CONFIRM=0 and wrong whenever the lane
is on. It is user-visible at `loop.py:68` ("repaired line N in {suite_runs} suite runs") and
`guard.py:686`. Total pytest-bearing interpreter invocations: 7.00 / 9.75 / 12.25 for
CONFIRM 0/1/2 (`pytest_cost.out`).

### F7. `engine.py`'s own docstring says HIDDEN is never set; `loop.py` has set it since 0.13.0

`src/fluidfix/engine.py:27-28`:

```
NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set
(documented limitation, not an omission by accident).
```

`src/fluidfix/loop.py:391`: `ruling = decide(situation(HIDDEN=True))`. The law's
specification document is one release stale with respect to the body.

### F8. What `CHANGE_GRANULARITY` actually does in the body today

Two different things wear the name, and neither is the law governing a search:

1. **At the HIDDEN site (`loop.py:386-397`)**: nothing. Proven in F3. The effect is "reject
   this candidate and keep searching", chosen by the local `fine_disagree` flag.
2. **At `loop.py:305-320`**, commented *"the engine law's CHANGE_GRANULARITY act,
   actuated"*: the `SpanEdit` handler — a coarser **edit** granularity (one candidate
   replaces lines start..end atomically), not a coarser **judgment** granularity. It is not
   gated on any ruling, and `grep -rn "SpanEdit(" src/` returns only the class's own
   `__repr__` at `acts.py:50`, so no shipped fault class constructs one; on the shipped
   vocabulary this path is reachable only through a user-registered taught transform.

No ladder of judgment granularities (re-run one test, N-of-M majority, discount a test that
also fails on the untouched file) exists anywhere in the body: `grep -rn "granularit" src/`
returns only `loop.py:99`, `loop.py:307`, `loop.py:363` and `engine.py:38` — three comments
and the act name.

### F9. A single 50-run batch is not enough to measure this rate

Batch-to-batch spread at fixed CONFIRM (from `pooled_fixture_a.out`, quoted in F1):
CONFIRM=2 gave 0/50 in one batch and 4/50 in an independent replication; CONFIRM=1 gave
3/50 and 4/50. The count of runs in which the wrong candidate `b - a` passed its first
(coarse) check also moved from 16/50 to 26/50 between the two CONFIRM=2 batches, against a
model expectation of 25/50. This is why the report of "0 of 49" in CHANGELOG 0.13.0 should
be read as one sample. Every rate in F1 is therefore given at n=100.

## 4. Lanes

Reached by this work:

- `HIDDEN` alone -> `CHANGE_GRANULARITY` — fired at runtime 106 times across the 390
  measured repair runs (43 at fixture_a CONFIRM=1, 38 at CONFIRM=2, 13 + 12 on fixture_b),
  every time as a per-candidate message only.
- `BUILT` -> `SHIP` — the reason string of every repaired run (`"engine law: BUILT -> SHIP"`),
  319 of the 390 runs (all 300 fixture_a runs plus 19 of the 90 fixture_b runs).
- `REFUTED` -> `HARVEST_COUNTEREXAMPLE` — the guard-level lane behind fixture_b's 56
  refusals; in the `repair` CLI path used here the refusal text comes from `loop.py:427-430`'s
  hardcoded string rather than from a ruling.

Never reached:

- **`CHANGE_GRANULARITY` as the outcome of a search.** No code path can produce it: the only
  situation carrying HIDDEN is built at `loop.py:391` and discarded (F3), and no
  search-ending `situation(...)` accepts a HIDDEN argument (F4). The observation that would
  make it reachable already exists — the body computes `fine_disagree` per candidate; it
  needs a `hidden=` argument threaded into `_rule()` at `loop.py:217` and into
  `guard.py:612/618`.
- **112 of the 128 HIDDEN situations.** `engine_hidden_lanes.out`: the 128 HIDDEN=1 inputs
  rule `{CHANGE_GRANULARITY: 16, ADD_STATE: 56, ADD_MATERIAL: 32, RAISE_BUDGET: 8,
  AUTHOR_SUCCESSOR: 8, RESHAPE: 8}`. Only the 16-member `CHANGE_GRANULARITY` block is even
  nameable by today's body, and only through the single input `situation(HIDDEN=True)`
  (x = 16).
- `AMB` was never set in any of the 390 runs (0 `REFUSED_AMB` labels): the fixtures never
  produced two greens inside one candidate set.
- `NOTWIN`, `SELF`, `UNREAD`, `CAPPED`: not exercised by this target — **unmeasured** here.

## 5. Potential

- **Threading the measured HIDDEN bit into the search-ending ruling (F4).** Cost: one
  argument. Measured effect on the ruling: `situation(REFUTED=True)` ->
  `HARVEST_COUNTEREXAMPLE` becomes `situation(REFUTED=True, HIDDEN=True)` ->
  `CHANGE_GRANULARITY` (`hidden_never_reaches_final_ruling.out`), which would change what 56
  of the 90 fixture_b runs reported. Effect on repair *outcomes*: none by itself —
  **unmeasured**, because nothing actuates the act yet.
- **An actual granularity change on a re-check disagreement.** Measured upper bound on
  fixture_b at CONFIRM=2: **12 of 30 runs** rejected the correct repair after it had already
  gone green once (`HIDDEN fired on: {'return a + b': 12}`), and 1 more shipped it — so 13 of
  30 runs saw the right answer green at least once while only 1 kept it. An actuation that
  discounted a re-check failure caused by a test that *also* fails on the untouched file
  (data `oracle.failing_output()` already collects) could recover at most those 12, taking
  the correct-repair rate from 1/30 to at most 13/30 on this fixture. I did not build it, so
  the realised figure is **unmeasured**.
- **Cost of the lane as actuated today.** +1.33 full-suite runs per repair at CONFIRM=1 and
  +2.50 at CONFIRM=2 over CONFIRM=0, on a 3-candidate search (F6). On a repo where one full
  suite run dominates, that is the price of "reject and re-search". A granularity change
  that re-ran one test instead of the whole suite would pay a fraction of it —
  **unmeasured**, because no such path exists.
- **What the guarantee actually is.** F1 and F2 bound it with measured numbers: at the
  default CONFIRM=1 a code-correlated flaky suite still produced a wrong repair in 7 of 100
  searches, and a code-independent flaky suite refused the correct repair in 27 of 30. Both
  are properties of the oracle. The law ruled correctly in both.

## 6. Defects

1. **ACTUATION** — `src/fluidfix/loop.py:386-397`. The law rules `CHANGE_GRANULARITY`; the
   body performs "reject the candidate". The ruling reaches only the message, and forcing it
   to `SHIP` changes nothing (F3: `actuation_static.out`, `ruling_is_not_branched.out`).
   Measured consequence (F2): on a suite whose flakiness is independent of the code this
   actuation refuses the correct repair in 29 of 30 runs at CONFIRM=2.
2. **OBSERVATION** — `src/fluidfix/loop.py:217` and `src/fluidfix/guard.py:612/618`. HIDDEN
   is measured per candidate and then dropped, so the situation the law is asked at the end
   of a search cannot carry it and the law is asked about a search it is not told the truth
   about (F4). The fix is a bit, not an if-statement.
3. **WORDING** — `src/fluidfix/loop.py:427-430`, repeated at `guard.py:613-621`. "every
   candidate left the suite red — fault is outside this vocabulary or the observations are
   wrong" is false in exactly the case the HIDDEN lane exists to catch: the candidate went
   green and the suite moved (F5). All 56 fixture_b refusals at CONFIRM=1/2 carry it, as
   do the 15 at CONFIRM=0.
4. **WORDING** — `src/fluidfix/loop.py:355` vs `loop.py:382-384`. `suite_runs` omits every
   confirm re-check: 3 reported against 4.33 and 5.50 measured full-suite runs at CONFIRM=1
   and 2 (F6). Printed to users at `loop.py:68` and `guard.py:686`.
5. **WORDING** — `src/fluidfix/engine.py:27-28` states HIDDEN is "not yet measured ... never
   set"; `loop.py:391` sets it (F7).
6. **WORDING** — `CHANGELOG.md:68-70` reports the post-fix false-accept rate as "0 of 49 and
   0 of 46". On my fixture the pooled rate is 4 of 100 at CONFIRM=2 and 7 of 100 at
   CONFIRM=1, and one of my own 50-run batches did give 0 of 50 (F1, F9). The published
   number is a sample presented as a rate; the mechanism (q^(1+2N)) cannot reach zero. Their
   fixture is not in the repo, so their exact figures are **unmeasured** here and this is a
   claim about how the number is stated, not proof that their run was wrong.

No wrong **ruling** found. On every situation the body actually constructed — `HIDDEN`
alone, `BUILT`, `BUILT+AMB+CAPPED`, `REFUTED` — `decide()` returned the act named for it by
the engine docstring and by `tests/test_law_never_ruled_wrong.py`.

## 7. Verdict

The engine law's HIDDEN lane rules `CHANGE_GRANULARITY` correctly and the body never
actuates it — it rejects the candidate instead, which cut false accepts from 52% to 7%
(CONFIRM=1) and 4% (CONFIRM=2) rather than to zero on a code-correlated flaky suite (300
runs), cut correct repairs from 50% to 3.3% on a code-independent one (90 runs), and leaves
the measured HIDDEN bit unable to reach the ruling that ends a search.
