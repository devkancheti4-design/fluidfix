# 43-add-material-actuation

## 1. Target
Prototype ADD_MATERIAL — widening the candidate FILE set when the material in hand is
insufficient (every candidate is a harness/assertion-helper file) — on a misdirection
fixture, and measure whether widening finds the defect file and at what cost in suite runs.

## 2. Method

Read (no edits anywhere outside this directory; no git state changes):
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/engine.py` (the law + its docstring spec)
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py` (`find_candidate_files` 118-330,
  `guard_once` 439-625, `_is_test_path` 111)
- `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/oracle.py`, `acts.py`, `cli.py:468-476`

Wrote (all in this directory):
- `rt.sh` — the run wrapper. **This machine has no coreutils `timeout`**, so this is
  `nice -n 15` + a `perl` `alarm` wrapper, exit 124 on timeout. Verified:
  `./rt.sh 2 /bin/sleep 10; echo $?` -> `124`. Every python/pytest invocation below went
  through it. One run at a time.
- `make_fixture.py` — fixture **A**: package `shop/` (5 modules, 19 tests) where every test
  asserts through one shared non-test helper `shop/support/expect.py`. Defect: one token,
  `if qty >= BULK_QTY:` -> `if qty > BULK_QTY:` in `shop/discount.py`.
- `make_fixture_b.py` — fixture **B**: same, plus a helper assertion an act can flip
  (`assert got >= want`). This is the wrong-repair channel.
- `make_fixture_c.py` — fixture **C**: the defect moved to a *different* file
  (`shipping` / `cart` / `formatting`), so the result is not a one-file fluke.
- `make_fixture_d.py` — fixture **D**, the CONTROL: identical code, tests assert DIRECTLY
  (no helper). Widening must not fire here.
- `measure_candidates.py`, `run_baseline.py`, `dump_attempts.py`, `run_widened.py`,
  `compare.py`, `check_observation.py` — measurement drivers. All wrap `Oracle.run` to count
  suite runs. **No monkeypatching of decision code**: the prototype hands its file list to
  the body's existing `guard_once(..., files=[...])` parameter.
- `widen.py` — the prototype: the missing OBSERVATION (`assertion_carriers` -> UNREAD) and
  the missing ACTUATION (`widen` -> the SIGHT tier-2 file set).

Raw outputs kept next to the report: `out_candidates.txt`, `out_baseline.txt`,
`out_attempts.txt`, `out_baseline_b.txt`, `out_widened_a.txt`, `out_widened_b.txt`,
`out_cmp_shipping.txt`, `out_cmp_cart.txt`, `out_cmp_formatting.txt`, `out_cmp_control.txt`,
`out_observation.txt`, `out_law_rulings.txt`.

Interpreter: `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python` (3.14.7, pytest 9.1.1,
pytest-cov 7.1.0 — so the UNREAD-as-missing-pytest-cov condition at `guard.py:489` is FALSE
throughout; nothing here is that lane).

---

## 3. Findings

### F1. ADD_MATERIAL is wording only, and its one gate is unreachable whenever the traceback names any non-test file.

```
$ grep -c ADD_MATERIAL src/fluidfix/guard.py src/fluidfix/acts.py src/fluidfix/loop.py
src/fluidfix/guard.py:2
src/fluidfix/acts.py:0
src/fluidfix/loop.py:0
```

Both hits are one site, `guard.py:489-496`: the condition `if not candidates and not
_has_pytest_cov(oracle):` and the hint string it sets. It changes no file set, no budget, no
search. The message tells the user to install a coverage plugin. Confirmed as briefed.

### F2. The FRAMED tier returns the assertion helper and returns EARLY, so the defect file is not in the candidate set at ANY limit.

`guard.py:146` is `if ordered: return ordered[:limit]` — one non-test frame in the traceback
makes the whole SIGHT tier-2 (coverage) ranking below it dead code.

```
$ ./rt.sh 180 .venv/bin/python measure_candidates.py $PWD/fx      # out_candidates.txt
...
shop/support/expect.py:13: AssertionError
FAILED tests/test_discount.py::test_tier_bulk - AssertionError
...
find_candidate_files(limit=3) -> ['shop/support/expect.py']
   evidence={'pointed': ['shop/support/expect.py'], 'lanes': {'FRAMED': ['shop/support/expect.py']}}
   defect file 'shop/discount.py' present: False
   suite runs consumed by this call: 0 []
find_candidate_files(limit=999) -> ['shop/support/expect.py']
   defect file 'shop/discount.py' present: False
```

`limit=999` is the escalation call at `guard.py:614`. It returns the same single file, so
`capped0 = capped0 or len(all_files) > len(candidates)` is `1 > 1` = False: **the
CAPPED/RAISE_BUDGET lane cannot rescue this shape either.** More budget buys nothing.

### F3. On fixture B the body SHIPS A WRONG REPAIR: it inverts the shared assertion helper, the suite goes green, the defect stays on disk.

```
$ ./rt.sh 280 .venv/bin/python run_baseline.py $PWD/fxb_run 120   # out_baseline_b.txt
status      : repaired
file        : shop/support/expect.py
candidates  : ['shop/support/expect.py']
summary     : shop/support/expect.py: repaired line 17 in 8 suite runs (2.8s):
  - assert got >= want
  + assert got <= want
SUITE RUNS  : 14
discount.py still has the defect (`qty > BULK_QTY`): True
```

This is the red-team outcome, reproduced. It is a *sound* run by the oracle's own rule (the
suite is genuinely green) and a wrong repair by any human standard.

The near miss is visible on fixture A too — the body reached for the tolerance literal and
merely did not reach far enough:

```
$ ./rt.sh 200 .venv/bin/python dump_attempts.py $PWD/fx_att       # out_attempts.txt
{'at': 'shop/support/expect.py:12', 'tried': 'def expect_close(got, want, tol=1e-8):', ...}
```

### F4. The engine law would NOT have shipped it. `BUILT+UNREAD -> ADD_MATERIAL`.

```
$ ./rt.sh 60 .venv/bin/python -c "...decide(situation(**kw))..."   # out_law_rulings.txt
['BUILT'] -> SHIP
['UNREAD'] -> ADD_MATERIAL
['BUILT', 'UNREAD'] -> ADD_MATERIAL
['REFUTED'] -> HARVEST_COUNTEREXAMPLE
['REFUTED', 'UNREAD'] -> ADD_MATERIAL
['CAPPED'] -> RAISE_BUDGET
['CAPPED', 'UNREAD'] -> ADD_MATERIAL
```

UNREAD **dominates** BUILT, REFUTED and CAPPED. The lane that stops the wrong ship already
exists in the kernel. The body packed `BUILT` alone because it never measures UNREAD when
`candidates` is non-empty. Per the standing principle: this is an **observation** defect
(and a missing actuation), never a ruling defect.

### F5. The missing observation, measured at 0 suite runs.

`widen.py:assertion_carriers(out)` reads the long traceback pytest already printed: a frame
whose raising line (the `>` line) is a bare `assert`, in a non-test file, is carrying
somebody else's assertion — an instrument, not a suspect.
`UNREAD := candidates and set(candidates) <= carriers`.

```
$ ./rt.sh 60 .venv/bin/python check_observation.py                # out_observation.txt
helper carries the assert (fixture A/B shape)   carriers=['shop/support/expect.py'] expected=['shop/support/expect.py'] OK
test carries the assert (ordinary case)         carriers=[]                        expected=[]                        OK
the DEFECT FILE itself raises on an assert ...  carriers=['shop/discount.py']       expected=['shop/discount.py']      OK
exception, not an assert, inside a source file  carriers=[]                        expected=[]                        OK
```

Cost: pure text over output already in hand — **0 suite runs**.

### F6. The missing actuation, and what it costs: 2 suite runs.

`widen.py:widen()` re-runs the body's OWN `find_candidate_files()` with the carrier mentions
scrubbed from the traceback. That forces the SIGHT tier-2 coverage-specificity path that
`guard.py:146` otherwise makes unreachable. No src edit, no monkeypatch.

```
$ ./rt.sh 280 .venv/bin/python run_widened.py $PWD/fx_wide 120     # out_widened_a.txt
FRAMED (what the body searches today): ['shop/support/expect.py']
assertion carriers                   : ['shop/support/expect.py']
UNREAD measured                      : True
engine law ruling on UNREAD          : ADD_MATERIAL
widened set (SIGHT tier 2)           : ['shop/discount.py', 'shop/shipping.py', 'shop/cart.py', 'shop/tax.py', 'shop/formatting.py', 'shop/support/expect.py']
defect file rank in widened set      : 1
suite runs: failing_output=1 framed=0 widening=2
```

**The widening step itself costs exactly 2 suite runs** (tier 2's `--lf --cov` + full `--cov`
pair). The rest of any delta below is the cost of *searching* the files it found.

### F7. Widening put the defect file at rank 1 on 4 of 4 defect sites, and prevented the wrong ship.

Commands: `./rt.sh 290 .venv/bin/python compare.py <fixture> <defect> <label> 90` (fresh
`cp -R` copy per arm; `out_cmp_*.txt`), plus `out_baseline*.txt` / `out_widened*.txt` for A and B.

| fixture | defect file | baseline | widened | defect rank when widened |
|---|---|---|---|---|
| A `fx` (helper `expect_close`) | `shop/discount.py` | refused, 10 runs, "outside the taught vocabulary", no file | refused **on the right file**, AMB -> ADD_STATE, 19 runs | **1** |
| B `fxb` (helper `assert got >= want`) | `shop/discount.py` | **repaired the WRONG FILE** (`shop/support/expect.py`), 14 runs, defect still on disk | refused on the right file, AMB -> ADD_STATE, helper intact, 19 runs | **1** |
| C-shipping | `shop/shipping.py` | refused, 9 runs | **repaired correctly** `- if weight_kg < 1.0:` / `+ if weight_kg <= 1.0:`, 24 runs | **1** |
| C-cart | `shop/cart.py` | refused, 9 runs | **repaired correctly** `- sum(q - 1 for _, q in lines)` / `+ sum(q for _, q in lines)`, 12 runs | **1** |
| C-formatting | `shop/formatting.py` | refused, 9 runs | **repaired correctly** `- "%.3f" % x` / `+ "%.2f" % x`, 11 runs | **1** |
| D CONTROL (direct asserts) | `shop/discount.py` | refused AMB, 18 runs | UNREAD **False**, no widening, identical refusal, 19 runs | 1 (unchanged) |

Excerpt, `out_cmp_shipping.txt`:

```
  arm          baseline
  searched     ['shop/support/expect.py']
  status       refused
  runs         9
  ------------------------------------------------------------
  arm          WIDENED
  carriers     ['shop/support/expect.py']
  UNREAD       True
  ruling       ADD_MATERIAL
  searched     ['shop/shipping.py', 'shop/support/expect.py']
  defect_rank  1
  status       repaired
  edited       shop/shipping.py
  correct_file True
  runs         24
```

**Honest accounting of the run counts.** Every WIDENED total above includes **one duplicate
`pytest -x --tb=long`** that is an artifact of prototyping outside the body: the driver calls
`oracle.failing_output()` to get the traceback, then `guard_once()` calls it again. In-body
the widening would reuse the output already in hand. Subtract 1 from each WIDENED figure for
the in-body cost:

| fixture | baseline runs | widened runs (in-body) | delta |
|---|---|---|---|
| A | 10 | 18 | +8 |
| B | 14 (wrong ship) | 18 | +4 |
| C-shipping | 9 | 23 | +14 |
| C-cart | 9 | 11 | +2 |
| C-formatting | 9 | 10 | +1 |
| D control | 18 | 18 | **+0** |

Median delta on the four widening-triggered repairs/refusals: **+6 suite runs**; range
+1..+14. Of that, 2 runs are the widening itself and the remainder is the search of files the
body previously could not see.

### F8. The AMB refusal on fixtures A and B is intrinsic to that fixture, not an artifact of widening.

Fixture D reaches `shop/discount.py` *through the ordinary traceback* (no widening at all)
and lands on the same ambiguity:

```
# out_cmp_control.txt, baseline arm
  searched     ['shop/discount.py']
  status       refused
  hint         AMBIGUOUS: 2 candidates at 2 different lines (3, 10) all pass the suite ...
               (engine law: BUILT+AMB -> ADD_STATE, never guess)
```

(`BULK_QTY = 10` -> `9` and `qty >` -> `qty >=` are the same program spelled twice.) So on A
and B widening delivered the guard to the correct file and the correct refusal; the residual
ambiguity belongs to target 04/41, not here.

---

## 4. Lanes

Engine law lanes this work reached:
- **UNREAD -> ADD_MATERIAL** — reached only in the prototype (`widen.py`), never in `src/`.
  The body's one gate (`guard.py:489`) requires `candidates == []` **and** pytest-cov
  missing; with pytest-cov installed it is unreachable for any input.
- **BUILT -> SHIP** — reached by the body on fixture B, on a wrong file (F3).
- **BUILT+AMB -> ADD_STATE** — reached on fixtures A, B (widened) and D.
- **REFUTED -> HARVEST_COUNTEREXAMPLE** — reached as the baseline refusal on A and all three
  C fixtures.
- **CAPPED -> RAISE_BUDGET** — NOT reached on any misdirection fixture, and provably cannot
  be: `len(all_files) > len(candidates)` is `1 > 1` (F2). The observation that would make it
  reachable is a candidate list that is *truncated*; here it is *complete and wrong*, which
  is a different bit — exactly UNREAD.

Lanes never reached: **NOTWIN, HIDDEN, SELF, RESHAPE, CHANGE_GRANULARITY, AUTHOR_SUCCESSOR**.
Those bits are never set by fluidfix (documented in `engine.py`'s docstring) and nothing in
this target could set them.

`BUILT+UNREAD -> ADD_MATERIAL` is the lane the body most needs and has never once
constructed: it is the only ruling that would have stopped fixture B's wrong ship.

---

## 5. Potential

- **Wrong repairs prevented.** Measured: 1 of 1 constructible wrong-ship fixtures (fixture B)
  — the body ships `assert got >= want` -> `assert got <= want`; with UNREAD measured, the law
  rules ADD_MATERIAL and the helper is left intact (`helper assertions intact: True`,
  `out_widened_b.txt`). How often this shape occurs in real repos is **unmeasured** here.
- **Repairs gained.** Measured: 3 of 5 misdirection fixtures moved from `refused` to
  `repaired`-with-the-correct-token (C-shipping, C-cart, C-formatting); 2 moved from a
  wrong-file refusal / wrong-file ship to a correct-file ADD_STATE refusal. Defect file at
  rank 1 in 5 of 5 widened sets.
- **Price.** Widening itself: **2 suite runs**, always. End-to-end delta: **+1 to +14 suite
  runs, median +6** on the fixtures above. On the control it is **+0** — the observation is
  free and it does not fire.
- **Price on a large repo: unmeasured.** Tier 2 runs the suite twice under coverage; on a
  2,000-test suite that is a real cost, and nothing here measures it.
- The correct in-body site is `guard.py:489`. Its condition is one clause too narrow and its
  message names one cause (pytest-cov) out of two. The second cause — *the candidate list is
  complete and consists entirely of instruments* — needs `assertion_carriers()` (0 runs) and
  a call into the tier-2 path that `guard.py:146` currently short-circuits.

---

## 6. Defects

1. **OBSERVATION (primary).** UNREAD is never measured when `candidates` is non-empty.
   `guard.py:489` gates it on `not candidates`, so a candidate list that is *complete and
   useless* packs `BUILT`/`REFUTED` alone. Evidence: F3 (`out_baseline_b.txt`, status
   `repaired`, file `shop/support/expect.py`, defect still on disk) + F4
   (`decide(situation(BUILT=1, UNREAD=1)) == "ADD_MATERIAL"`). The law had the lane; the body
   handed it the wrong byte. Not a ruling defect.

2. **OBSERVATION (contributing).** The FRAMED bit is mismeasured on assertion helpers.
   `find_candidate_files` (guard.py:132-150) treats *any* non-test traceback frame as the
   failure POINTING at that file, and `evidence["lanes"]["FRAMED"]` records it as POINTING
   evidence. A file the failure merely asserts *in* is the instrument, not the suspect.
   Evidence: F2 — `pointed: ['shop/support/expect.py']` on a fixture whose defect is in
   `shop/discount.py`.

3. **ACTUATION.** ADD_MATERIAL actuates nothing: 2 textual hits in `guard.py`, 0 in `acts.py`
   and `loop.py` (F1). The material it could add already exists and is already implemented —
   the SIGHT tier-2 ranking — and is unreachable behind
   `guard.py:146 if ordered: return ordered[:limit]`. Evidence: F6/F7, where calling the
   body's own function with the carrier scrubbed produced the defect file at rank 1 for 2
   suite runs.

4. **WORDING.** The refusal on fixture A says "fault is outside the taught vocabulary
   (candidate files tried: shop/support/expect.py)". The fault (`>=` -> `>`) is squarely
   *inside* the taught vocabulary — `acts.py:_flip_strictness` repairs it as soon as the right
   file is searched (F7, C-shipping repaired exactly that shape). The true cause is that the
   vocabulary was never applied to the defect file. Evidence: `out_baseline.txt` summary line
   vs `out_cmp_shipping.txt` WIDENED arm.

**Known limitation of the prototype, stated rather than hidden.** `assertion_carriers` also
flags a *source* file that raises its own `assert` (a precondition check), which would fire
UNREAD and spend 2 suite runs unnecessarily — measured in `out_observation.txt`, case 3:
`carriers=['shop/discount.py']`. The prototype keeps the framed file in the search order
(widened set first, framed remainder appended) so nothing is lost, but it is demoted. The
refinement that removes this false positive is to require *in addition* that the carrier is
executed by tests other than the failing one — a UBIQUITOUS-style bit — which the tier-2
coverage runs already compute. **Unmeasured** here.

---

## 7. Verdict
ADD_MATERIAL is wording-only and structurally unreachable when the traceback names an
assertion helper; measuring UNREAD from the traceback (0 suite runs) and actuating it via the
body's own SIGHT tier-2 ranking (2 suite runs) put the defect file at rank 1 on 5 of 5
misdirection fixtures, turned 3 refusals into correct repairs, and prevented one measured
wrong ship — an observation-and-actuation gap, not a ruling defect.
