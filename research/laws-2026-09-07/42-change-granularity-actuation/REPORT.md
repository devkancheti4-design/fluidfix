# 42 — CHANGE_GRANULARITY: what ladder exists, and is changing granularity better than re-confirming?

## 1. Target
`42-change-granularity-actuation` — enumerate the granularity ladder fluidfix
actually has (token / line / statement / block, and the record granularity the
HIDDEN lane is really about), prototype the granularity switch outside `src/`,
and measure it against re-confirmation on a code-correlated flake and a
code-independent flake.

## 2. Method
Read, in `/Users/kanchetidevieswar/neo/fluidfix/`: `src/fluidfix/engine.py`,
`acts.py`, `loop.py`, `oracle.py`, `lanes.py`, `observers.py`, `localize.py`,
`guard.py`; `tests/test_span_edits.py`, `tests/test_law_never_ruled_wrong.py`;
`CHANGELOG.md` (0.7.0, 0.13.0, and the 0.13.1 correction).

Wrote, all inside
`/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/42-change-granularity-actuation/`:

| file | what it is |
|---|---|
| `tmo` | timeout wrapper (this machine has no coreutils `timeout`; perl `alarm`, exit 124 on expiry). Every run below is `nice -n 15 ./tmo N ...`. |
| `ladder_audit.py` | static + dynamic audit of the edit-granularity rungs and of who consults the ruling |
| `granularity.py` | **the prototype**: `LadderOracle`, a subclass of the shipped `Oracle` whose RECORD GRANULARITY is a knob (rungs 0-3), plus `Profile`, the baseline flake profile |
| `run_experiment.py` | drives the **shipped, unmodified** `loop.repair()` with that oracle, one config at a time |
| `hidden_carry.py` | measures how often a search that OBSERVED HIDDEN still ends by asking the law a situation with HIDDEN clear |
| `run_all.sh`, `cost.sh`, `table.py` | the run chain, the cost measurement, the table renderer |
| `fixtures/shapeA`, `fixtures/shapeB`, `fixtures/shapeB_padded` | the two flake shapes and a 502-test padded copy used only for the cost measurement |
| `results/*.json`, `results/run_all.log` | raw per-trial records |

`src/`, `tests/`, `docs/` and every other agent's directory are untouched; no
git state was changed.

**The fixtures.** Both carry the same defect and take the same vocabulary path,
so only the flake shape differs. `src.py` is

```python
def combine(a, b):
    return a - b          # correct: return a + b
```

The real `MechanicalObserver` reports `kinds=[2, 3, 11]` for that line, `EMIT`
takes the lowest live bit first, so the search tries kind 2
(`_swap_return_operands` -> `return b - a`, **wrong**) *before* kind 3
(`_flip_additive` -> `return a + b`, **correct**). Greens accumulate across the
whole search and `_rule()` ships `greens[0]`, so a lucky green on the wrong
candidate is a shipped wrong repair. This is exactly the `return b - a` for
`return a + b` incident recorded in CHANGELOG 0.13.0.

* **shape A — flake CORRELATED with the code under test.** The only test wraps
  its assert in a bounded retry loop whose *budget is the value under test*
  (`for _ in range(abs(v)): if random.random() < 0.30: return`). The defect
  (`v == -1`) leaves the suite red ~70% of the time; the wrong candidate
  (`v == 1`) is green ~30% of the time; the correct candidate (`v == 5`) is
  always green.
* **shape B — flake INDEPENDENT of the code under test.** `test_combine`
  asserts deterministically; a second test `test_resource` raises 50% of the
  time for reasons unrelated to `combine`.

## 3. Findings

### F1. The EDIT-granularity ladder has three rungs; two are reachable by shipped code, and NOTHING selects a rung.

`nice -n 15 ./tmo 60 .venv/bin/python ladder_audit.py` (section A):

```
=== A. EDIT-granularity rungs: what do the 10 shipped appliers return? ===
  act  0  _reverse_minus_operands      returns=['str'] multiline_str=False
  act  1  _flip_boolean                returns=['str'] multiline_str=False
  act  5  _flip_strictness             returns=['str'] multiline_str=False
  act  6  _reduce_literal              returns=['str'] multiline_str=False
  act  7  _swap_return_operands        returns=['str'] multiline_str=False
  act  8  _flip_additive               returns=['str'] multiline_str=False
  act 13  _swap_minmax                 returns=['str'] multiline_str=False
  act 14  _flip_augmented              returns=['str'] multiline_str=False
  act 15  _flip_comparison             returns=['str'] multiline_str=False
  shipped appliers returning SpanEdit: 0 of 9
```

The ladder, with the code that is each rung:

| rung | unit | where | reachable today |
|---|---|---|---|
| **token** | one token inside one line | every applier in `acts.py` (`_flip_additive` rewrites one `+`/`-`, `_reduce_literal` one literal, ...) | yes — this is the only rung shipped acts use |
| **line** | one whole line | `loop.py:327-329` (`new[i] = cand + ending`) — the WRITE unit; a token change is delivered as a whole replacement line | yes |
| **statement** | one simple statement | **does not exist.** `ladder_audit.py` section B: `ast` appears 0 times in `acts.py` and 0 times in `loop.py`; `tokenize` 0 times everywhere. `localize.py` parses `ast` only to expand *coverage anchors* to their enclosing simple statement — that widens what an observer SEES, never what an act EDITS | no |
| **block / span** | lines `start..end` replaced atomically | `acts.SpanEdit` + `loop.py:306-323`; CHANGELOG 0.7.0 calls this "the engine law's CHANGE_GRANULARITY act, actuated" | only via `register()` / `--dictionary`; **0 of 9 shipped appliers can produce one** |

The decisive point is not that a rung is missing. It is that **no code anywhere
chooses a rung**. The rung is fixed by whichever applier the router picked for
the kind the observer reported. There is no function that takes a search in
trouble and moves it up or down this ladder, so `CHANGE_GRANULARITY` cannot be
actuated *as an edit-granularity change* even in principle today.

### F2. The ruling is computed and then used only inside an f-string.

`ladder_audit.py` section C:

```
=== C. does anything CONSULT the CHANGE_GRANULARITY ruling? ===
  loop.py:391: ruling = decide(situation(HIDDEN=True))
  loop.py:396: f"(engine law: HIDDEN -> {ruling}). "
  uses of the variable `ruling` after loop.py:391:
  loop.py:396: f"(engine law: HIDDEN -> {ruling}). "
```

`loop.py:391` is the only site in the package that sets `HIDDEN`. The value it
gets back reaches exactly one place: the text of `why`. The next statement is
`ok = False` — the body **rejects the candidate**. Rejecting is a different act
from `CHANGE_GRANULARITY`; the law's ruling is quoted, not obeyed.

### F3. `CHANGE_GRANULARITY` is ruled on 16 of 256 situations, and `BUILT+HIDDEN` is one of them — a situation the body can never build.

```
$ nice -n 15 ./tmo 60 .venv/bin/python -c "...decide over all 256..."
CHANGE_GRANULARITY ruled on 16 of 256 situations:
   HIDDEN
   BUILT+HIDDEN
   CAPPED+HIDDEN
   BUILT+CAPPED+HIDDEN
   HIDDEN+REFUTED
   ... (16 total)
without HIDDEN: []
```

Algebraically the lane is `HIDDEN & ~AMB & ~UNREAD & ~NOTWIN`. Note
`BUILT+HIDDEN -> CHANGE_GRANULARITY`, **not SHIP**. The only place a
search-ending situation is built is `_rule()` at `loop.py:217`:

```python
ruling = decide(situation(BUILT=True,
                          AMB=set_amb or len(sites) > 1,
                          CAPPED=capped))
```

`HIDDEN` is not a parameter there. So a search that watched the suite fail to
hold still, and then found a green, asks the law `BUILT` (-> SHIP) instead of
`BUILT+HIDDEN` (-> CHANGE_GRANULARITY). The law never sees the bit the body
already measured 200 lines earlier.

### F4. `FLUIDFIX_CONFIRM` is not a granularity change; it is more samples at the same granularity.

`loop.py:94-106` names `_confirm_runs()` "how many FINE records to take", and
`loop.py:381-385` takes them with `oracle.check()` — the same whole-suite call,
returning the same single boolean. `oracle.py:183-236` shows `check()` has
exactly one record granularity: a bool. It parses per-test `FAILED`/`ERROR`
lines and keeps only the *first one as a string* for the message. The finer
record already exists in the output the oracle reads, and is discarded.

So the body's answer to "you are judging at the wrong granularity" is to judge
the same way more times. That is what the measurements below test.

### F5. The prototype: a RECORD-granularity ladder, actuated outside `src/`.

`granularity.py` subclasses the shipped `Oracle` and overrides `check()` /
`green()` only. The shipped `loop.repair()` runs unmodified; `FLUIDFIX_CONFIRM`
is set to 0 for rungs 2-3 so the body adds no re-samples of its own.

| rung | the record a verdict is made of | cost per candidate |
|---|---|---|
| 0 `suite` | one full-suite run -> one bit (= `FLUIDFIX_CONFIRM=0`) | 1 full run |
| 1 `resample` | 1+n full-suite runs, ANDed (= `FLUIDFIX_CONFIRM=n`) — **same granularity, more samples** | 1+n full runs |
| 2 `test` | one full-suite run, verdict = per-TEST record set vs a baseline profile; a test whose baseline records disagree with each other is HIDDEN and carries no verdict | 1 full run + B profile runs/search |
| 3 `test+k` | rung 2, and every test that actually carries the verdict is re-run **alone** k times — k fine records at TEST granularity instead of k coarse records at SUITE granularity | 1 full run + k*T node runs |

`Profile` (B=5 full-suite runs on the pristine tree, kept at test granularity)
splits the suite into: tests that fail in **all** baseline runs (the fault's
signature), tests that fail in **some** (HIDDEN — the suite does not hold still
on them), and tests that fail in **none** (guards). The verdict rule at rung 3:

* every *target* (the deterministic failures if there are any; otherwise the
  flaky failures, because then they are all the evidence there is) must pass
  **k of k** runs of that test alone;
* a *guard* that now fails is re-run alone k times and only believed if it
  fails k of k (so one unprofiled flake cannot force a false refusal);
* every other flaky test is **ignored** — its record says nothing about this
  candidate.

Note rung 2/3 also change the granularity of the PRECONDITION: `loop.repair()`
opens with `oracle.green()`, one bit from one run, which on a flaky suite
aborts a large share of searches with *"no failing test — nothing to repair"*.
Rungs 2/3 answer that question from the profile instead. That difference is
visible in the `NO_FAILING_TEST` column below and is part of the result, not a
confound to be hidden.

### F6. MEASURED: on a code-CORRELATED flake, re-confirming works and rung 2 does not; only rung 3 (fine records at TEST granularity) reaches zero false accepts without losing repairs.

Command (each config run alone, `nice -n 15 ./tmo N ...`; raw records in
`results/shape*_*.json`, chain in `run_all.sh` / `run_rest.sh`):

```
nice -n 15 ./tmo 600 .venv/bin/python run_experiment.py A g0 100     # etc.
nice -n 15 .venv/bin/python table.py
```


### shape A

| config | n | CORRECT | FALSE_ACCEPT | REFUSED | NO_FAILING_TEST | pytest invocations/search (full+node) | s/search |
|---|---|---|---|---|---|---|---|
| rung 0  suite, 1 run (CONFIRM=0) | 100 | 50 (50%) | 24 (24%) | 0 (0%) | 26 (26%) | 2.48 (2.48+0.0) | 0.55 |
| rung 1  suite, 1+1 runs (CONFIRM=1, shipped default) | 100 | 66 (66%) | 10 (10%) | 0 (0%) | 24 (24%) | 3.45 (3.45+0.0) | 0.74 |
| rung 1  suite, 1+2 runs (CONFIRM=2) | 100 | 64 (64%) | 5 (5%) | 0 (0%) | 31 (31%) | 4.04 (4.04+0.0) | 0.88 |
| rung 1  suite, 1+4 runs (CONFIRM=4) | 100 | 78 (78%) | 0 (0%) | 0 (0%) | 22 (22%) | 5.94 (5.94+0.0) | 1.64 |
| rung 2  per-test record, 1 run | 30 | 20 (67%) | 10 (33%) | 0 (0%) | 0 (0%) | 7.0 (7.0+0.0) | 2.38 |
| rung 3  per-test record + k=4 fine records per target | 30 | 30 (100%) | 0 (0%) | 0 (0%) | 0 (0%) | 12.27 (7.0+5.27) | 3.94 |

### shape B

| config | n | CORRECT | FALSE_ACCEPT | REFUSED | NO_FAILING_TEST | pytest invocations/search (full+node) | s/search |
|---|---|---|---|---|---|---|---|
| rung 0  suite, 1 run (CONFIRM=0) | 30 | 12 (40%) | 0 (0%) | 18 (60%) | 0 (0%) | 3.0 (3.0+0.0) | 0.71 |
| rung 1  suite, 1+1 runs (CONFIRM=1, shipped default) | 30 | 3 (10%) | 0 (0%) | 27 (90%) | 0 (0%) | 3.37 (3.37+0.0) | 0.81 |
| rung 1  suite, 1+4 runs (CONFIRM=4) | 30 | 0 (0%) | 0 (0%) | 30 (100%) | 0 (0%) | 3.9 (3.9+0.0) | 0.96 |
| rung 2  per-test record, 1 run | 30 | 29 (97%) | 0 (0%) | 1 (3%) | 0 (0%) | 7.0 (7.0+0.0) | 1.65 |
| rung 3  per-test record + k=4 fine records per target | 30 | 29 (97%) | 0 (0%) | 1 (3%) | 0 (0%) | 12.07 (7.0+5.07) | 3.84 |

Reading shape A (the flake correlates with the value under test):

* `FLUIDFIX_CONFIRM` genuinely works here: false accepts 24% -> 10% -> 5% -> 0%,
  and CORRECT goes UP (50% -> 78%), because a candidate that was green only by
  luck stops occupying the answer. This reproduces the shape of CHANGELOG
  0.13.0's claim on this fixture.
* **Rung 2 alone is no better than rung 0**: 10/30 false accepts (33%) vs
  24/74 (32%) of the shape-A rung-0 searches that actually ran. Correct: the
  only informative test IS the flaky one, so a per-test reading of a single run
  is still one lucky record.
* **Rung 3 is the only config with 0 false accepts AND no lost repairs:
  30/30 CORRECT, 0 FALSE_ACCEPT.** `CONFIRM=4` also reaches 0 false accepts but
  only repairs 78/100, because its `oracle.green()` precondition — one bit from
  one run — aborts 22% of searches with "no failing test". Rung 3 answers that
  question from the profile and loses none.

### F7. MEASURED: on a code-INDEPENDENT flake, re-confirming DESTROYS correct repairs and changing granularity restores them.

Shape B, same table. `CONFIRM=0` repairs 12/30 (40%); the shipped default
`CONFIRM=1` repairs **3/30 (10%)**; `CONFIRM=4` repairs **0/30**. There are
zero false accepts at every rung, so every one of those extra suite runs buys
nothing and costs repairs. This reproduces the coordinator's 50% -> 3.3%
correction on an independently built fixture.

Changing the granularity instead repairs **29/30 (97%) at rung 2 — with ONE
full-suite run per candidate**, and 29/30 at rung 3. The reason is visible in
the profile: `test_resource` fails in some baseline runs and passes in others,
so it is HIDDEN and carries no verdict; `test_combine` fails in all of them and
is the verdict. Re-confirmation cannot make that distinction because a
whole-suite boolean does not say WHICH test failed.

The single rung-2/rung-3 refusal is an honest, measurable artifact of the
profile size (B=5), not of the rule. From
`results/shapeB_g2.json`:

```json
{"outcome": "REFUSED",
 "why": "every candidate left the suite red - fault is outside this vocabulary...",
 "profile": {"always_fail": ["test_it.py::test_combine",
                             "test_it.py::test_resource"],
             "mixed": [], "hidden": false}}
```

The 50/50 flake happened to fail all 5 baseline runs (p = 0.5^5 = 3.1%), so it
was mis-profiled as deterministic. Raising B shrinks this; the rate at B=5 is
1/30 measured.

### F8. MEASURED: 13 of 60 searches observed HIDDEN and then asked the law a situation with HIDDEN clear.

```
$ nice -n 15 ./tmo 400 .venv/bin/python hidden_carry.py A 60
{"shape": "A", "trials": 60,
 "saw_hidden": 13, "repaired": 41,
 "saw_hidden_AND_shipped": 13,
 "shipped_correct_among_those": 13, "shipped_wrong_among_those": 0,
 "law_on_BUILT": "SHIP", "law_on_BUILT_HIDDEN": "CHANGE_GRANULARITY",
 "example_reason": "engine law: BUILT -> SHIP"}
```

Every search that saw the suite fail to hold still went on to ship under
`BUILT -> SHIP`. The honest situation was `BUILT+HIDDEN`, on which the law
rules `CHANGE_GRANULARITY`. On this fixture all 13 shipped repairs happened to
be correct, so the missed lane cost no wrongness here — but the law was asked
the wrong question in 13 of 60 searches (21.7%), and the bit it was missing had
already been measured 200 lines earlier in the same function.

### F9. The cost of a node-granularity record, measured — and it is NOT a big saving on a cheap suite.

`cost.sh` on `fixtures/shapeB_padded` (502 tests), 5 runs each:

```
--- full suite (real seconds) ---   --- single node (real seconds) ---
real 1.10                          real 0.40
real 0.42                          real 0.39
real 0.48                          real 0.34
real 0.39                          real 0.26
real 0.45                          real 0.21
```

Median 0.45s (full, 502 tests) vs 0.34s (one node) — about **1.3x**, because
pytest process start-up dominates when the tests themselves take microseconds.
So on this fixture rung 3's advantage is *not* cheapness: rung 3 costs MORE
wall clock than `CONFIRM=4` (3.94s vs 1.64s per search on shape A). Its
advantage is that the record it takes is about the right thing. What the ratio
would be on a suite whose tests actually cost something is **unmeasured**.

## 4. Lanes

Engine law, the 16 `CHANGE_GRANULARITY` situations (`HIDDEN & ~AMB & ~UNREAD &
~NOTWIN`):

* **`HIDDEN` alone — reached, per candidate, and discarded.** `loop.py:391`
  constructs it every time a re-check disagrees with the first run. The ruling
  is interpolated into a string (F2). No behaviour depends on it.
* **`BUILT+HIDDEN` — never reached.** `_rule()` (`loop.py:217`) is the only
  builder of a search-ending situation and takes `BUILT`, `AMB`, `CAPPED` only.
  The observation that would make it reachable already exists: a
  search-scoped boolean set at `loop.py:391` and passed to `_rule()`. Measured
  frequency below (F8).
* **`CAPPED+HIDDEN`, `HIDDEN+REFUTED`, and the 12 combinations with `SELF` —
  never reached.** `CAPPED` and `REFUTED` are only ever fused with `BUILT`/`AMB`
  in `_rule()` and in `guard.py:539/612/618`; none of those sites carries
  `HIDDEN`. `SELF` is never measured anywhere (`engine.py` docstring says so).
* **Lanes this work did NOT reach:** every non-`HIDDEN` act. `RESHAPE`,
  `AUTHOR_SUCCESSOR`, `ADD_MATERIAL` and `ADD_STATE` were reached only as
  *rulings enumerated exhaustively* in `ladder_audit.py` section D, never
  actuated here.

Lanes law (`lanes.py`): `EMIT`/`ADVANCE`/`HALT` were exercised on masks
`{2,3,11}` only; the ordering they impose is what puts the WRONG candidate
first in this fixture, and that is load-bearing for every false accept measured.

## 5. Potential

* **A `BUILT+HIDDEN` situation costs one boolean.** Threading a
  search-scoped `saw_hidden` flag into `_rule()` would let the law rule
  `CHANGE_GRANULARITY` on exactly the searches that shipped a repair after
  watching the suite wobble. Measured frequency in F8.
* **The finer record is already paid for.** `oracle.check()` runs pytest and
  parses `FAILED`/`ERROR` lines, then throws all but the first away
  (`oracle.py:213-217 and 235-236`). Rung 2 needs no extra suite run at all — only
  a different reading of output the oracle already has.
* **Node-level re-checks are the cheap way to buy confidence.** Measured cost
  ratio in F9.
* **The edit-granularity ladder's top rung is unreachable without teaching.**
  A `CHANGE_GRANULARITY` ruling that meant "widen the edit from a line to a
  span" would need a shipped span-capable act; there are none (F1). What such
  a rung would be worth on the flake shapes measured here: **unmeasured** —
  the two are orthogonal, and nothing in either fixture needs a multi-line
  edit.
* **What rung 2 is worth, measured:** on the code-independent flake it took
  correct repairs from **3/30 (the shipped default) to 29/30**, for ONE
  full-suite run per candidate plus a 5-run baseline profile. On the
  code-correlated flake it was worth nothing on its own (33% false accepts).
* **What rung 3 is worth, measured:** the only configuration that reached
  **0 false accepts and 30/30 correct on shape A**, and 29/30 on shape B — the
  only one that is right on BOTH shapes. Cost: 12.3 pytest invocations per
  search vs 5.9 for `CONFIRM=4`, 3.94s vs 1.64s on this fixture.
* **What a bigger baseline profile is worth:** the one refusal at rung 2/3 on
  shape B came from B=5 mis-profiling a 50/50 flake as deterministic
  (p = 0.5^5 = 3.1%; measured 1/30). Raising B trades suite runs for that rate.

## 6. Defects

**D1 — ACTUATION.** `loop.py:391` measures `HIDDEN`, asks the law, receives
`CHANGE_GRANULARITY`, and puts the answer in a string (`loop.py:396`). The next
statement sets `ok = False`: the body REJECTS the candidate. Rejection is a
different act. Evidence: `ladder_audit.py` section C — the variable `ruling` has
exactly one use after the line that assigns it, inside an f-string.
`tests/test_law_never_ruled_wrong.py:42-44` classifies this incident as
OBSERVATION ("the lane was never measured, so the situation never reached the
law"). That classification was right in 0.12; since 0.13.0 wired the
measurement it is **stale** — the lane IS measured now, and what is missing is
the actuation.

**D2 — OBSERVATION.** `_rule()` (`loop.py:217`) builds the only search-ending
situation and never passes `HIDDEN`, although the same function measured it.
Measured frequency: 13 of 60 shape-A searches (F8) shipped under `BUILT ->
SHIP` when the honest situation was `BUILT+HIDDEN -> CHANGE_GRANULARITY`. The
fix is a search-scoped boolean, not a decision: `decide(situation(BUILT=True,
AMB=..., CAPPED=..., HIDDEN=saw_hidden))`. **No wrong repair was produced by
this on my fixtures** (13/13 of those shipped repairs were correct), so this is
a wrong QUESTION, not yet a measured wrong outcome.

**D3 — WORDING.** `loop.py:94-106`'s docstring for `_confirm_runs()` calls the
extra whole-suite runs "FINE records". They are not finer: `oracle.check()`
returns the same one bit over the same whole suite (`oracle.py:183-236`). They
are more SAMPLES at the same granularity. F7 shows the difference is not
cosmetic: on a code-independent flake more samples at suite granularity took
correct repairs from 12/30 to 0/30, while a genuinely finer record took them to
29/30.

**D4 — none found in any ruling.** Every ruling this work exercised was
correct for the situation it was given: `HIDDEN -> CHANGE_GRANULARITY`,
`BUILT -> SHIP`, `BUILT+HIDDEN -> CHANGE_GRANULARITY`. The wrong outcomes came
from the situation, not the law.

## 7. Verdict
The granularity ladder that exists is token->line (shipped) plus an
atomic span rung reachable only by a taught transform, and no code selects a
rung; the `HIDDEN` lane's real ladder is the RECORD, where the body answers
`CHANGE_GRANULARITY` with more samples at the same granularity — measured, that
is right on a code-correlated flake (24%->0% false accepts) and destructive on
a code-independent one (12/30->0/30 correct repairs), while an actual change of
record granularity, prototyped here, is the only setting correct on both
(shape A 30/30 correct with 0 false accepts, shape B 29/30) at about twice the
suite runs.
