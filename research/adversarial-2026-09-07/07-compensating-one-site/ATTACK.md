# 07-compensating-one-site — two different programs, one line, both green

## 1. Target

Two genuinely different programs reachable at ONE line by two different acts, both
passing the suite: per attack surface C the AMB proxy in `loop.py:_rule` should call
this unambiguous and ship one. Reproduce it, and measure over >= 10 fixtures how
often the shipped program is the wrong one.

## 2. Attack design

`loop.py:217-219` asks the engine law with

```python
ruling = decide(situation(BUILT=True,
                          AMB=set_amb or len(sites) > 1,
                          CAPPED=capped))
```

Both AMB terms are proxies for WHERE greens came from, never for WHETHER they are
the same program:

* `sites` is `{g[3] for g in greens}` — the *line numbers*. Two greens at one line
  collapse to one site, whatever they do.
* `set_amb` is set at `loop.py:400-404` only when `len(greens) - green_at_set_start > 1`,
  i.e. when two greens land inside **one candidate set**. A candidate set is one act,
  and one act is one kind (`loop.py:297-305`: `kind = kind_of(EMIT(mask))`,
  `act = act_for(kind)`).

So the attack is: put **one** green in each of **two different kinds' candidate sets**,
at the same line. Then `green_at_set_start` is reset between them, `set_amb` stays
`False`, `sites` has one element, `AMB` is measured `False`, and the law is handed
`BUILT` alone — whose correct ruling is `SHIP`.

Which of the two greens gets shipped is `greens[0]` (`loop.py:221`), i.e. the one
from the **lowest-numbered kind**, because `lanes.EMIT` returns the lowest live bit
and `MechanicalObserver` reports every matching kind ascending
(`observers.py:37-40`). Kind index is a vocabulary numbering. It carries no evidence
about which repair is correct, so the choice should be right about as often as a coin.

To measure that honestly the fixtures are built in **six matched pairs**. Inside a
pair the defect line and the test file are byte-identical; only which of the two
suite-passing programs is the pristine one differs. fluidfix therefore produces
byte-identical output for both members, and is correct on exactly one of them by
construction — which is itself the finding: the decision is provably independent of
the ground truth.

## 3. Attempts

1. **Direct probe of the law.** Confirmed the law is not the defect before touching a
   fixture:

   ```
   BUILT=1 AMB=0 CAPPED=0 -> byte 513 (0x201) -> SHIP
   BUILT=1 AMB=1 CAPPED=0 -> byte 515 (0x203) -> ADD_STATE
   ```

   The law rules correctly on both bytes. Anything that follows is an observation
   defect, not a ruling defect.

2. **Fixture A1 (`fixtures/F01_index_strict/`, kept as first-shot evidence).**
   Array-index defect at `gate.py:5`, kind 0 (strictness) and kind 1
   (literal-off-by-one) each yielding one green. **Landed on the first attempt.**
   `readings[1] >= limit` written to disk, `"repaired": true`,
   `"ambiguous": false`.

3. **Scaled to 12 fixtures across 6 collision shapes** (`fixtures.py`,
   `run_attack.py`). Every fixture is sanity-gated: the pristine program must leave
   the suite green and the defect must leave it red, both checked before fluidfix
   runs. All 12 passed sanity. 12/12 shipped, 2 greens each, 0 refusals.

4. **Full `fluidfix guard .` path** (`guardrun/`) — not just `repair`. Same wrong
   program written, exit code 0, one-line summary.

5. **FAILED — strictness flip rescuing a literal off-by-one.** Tried to build the
   mirror where the kind-0 candidate repairs a wrong *literal*. Algebraically
   impossible: `_flip_strictness` changes behaviour only at the equality point, so
   any test that makes a literal defect red also kills the strictness variant. Not a
   fluidfix defence — an act-algebra constraint that shaped which shapes are
   reachable.

6. **FAILED — min/max defect rescued by a strictness flip.** For all tests
   `(max(a,b) >= L) == (min(a,b) > L)` forces `min > L`, and then `max > L` holds
   too, so the defect is never red. Also impossible.

7. **FAILED, and this one is fluidfix defending — control `control_G1/`.** The same
   situation shape (two *different* programs, one line, suite blind to the
   difference), but arranged so both greens come from ONE candidate set: kind 1 on
   `return matrix[1][1]` proposes `matrix[0][1]` and `matrix[1][0]`, and a symmetric
   test matrix cannot tell them apart. fluidfix **refused**, tree untouched:

   > `AMBIGUOUS: 2 candidates at 1 different lines (5) all pass the suite — the tests
   > cannot tell them apart, and one may CANCEL the fault rather than repair it. Add
   > one pinning test (engine law: BUILT+AMB -> ADD_STATE, never guess)`

   Identical semantics, opposite outcome, and the only difference is which candidate
   set the greens arrived in. That is the defect stated as an experiment.

## 4. Outcome

### S1 — WRONG REPAIR SHIPPED (primary)

**Reproduction (whole measurement, ~90s):**

```sh
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/07-compensating-one-site
nice -n 15 ./tmo 1500 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python run_attack.py
```

**Single-fixture reproduction (the diff below):**

```sh
cd .../07-compensating-one-site/fixtures/F01_index_strict
nice -n 15 ../../tmo 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix repair . --file gate.py --json
# or the full user-facing path:
nice -n 15 ../../tmo 600 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard .
```

**The diff fluidfix wrote** (`guardrun/`, `fluidfix guard .`, exit 0):

```diff
--- gate.py.defect-before
+++ gate.py
@@ -2,4 +2,4 @@
 def alarm(readings, limit):
-    return readings[1] > limit
+    return readings[1] >= limit
```

against a pristine of `return readings[0] > limit`. The shipped program reads a
**different element of the array** with a **different operator**. Differential
witness: `alarm([9, 1], 5)` — pristine `True`, shipped `False`.

fluidfix's own report:

```
[14:29:46] gate.py: repaired line 5 in 4 suite runs (2.2s):
  - return readings[1] > limit
  + return readings[1] >= limit
```

**Measured over 12 fixtures** (`results.json`; `probe differs` is the differential
witness proving the two greens are two programs, not two spellings):

| fixture | greens | shipped | probe differs |
|---|---|---|---|
| A1_index_vs_strict__pristine_is_index | 2 | **WRONG** | yes |
| A2_index_vs_strict__pristine_is_strict | 2 | correct | – |
| B1_threshold_vs_strict__pristine_is_literal | 2 | **WRONG** | yes |
| B2_threshold_vs_strict__pristine_is_strict | 2 | correct | – |
| C1_slice_vs_strict__pristine_is_slice | 2 | **WRONG** | yes |
| C2_slice_vs_strict__pristine_is_strict | 2 | correct | – |
| D1_minmax_vs_strict__pristine_is_max | 2 | **WRONG** | yes |
| D2_minmax_vs_strict__pristine_is_min_ge | 2 | correct | – |
| E1_index_vs_additive__pristine_is_index | 2 | correct | – |
| E2_index_vs_additive__pristine_is_minus | 2 | **WRONG** | yes |
| F1_index_vs_reversal__pristine_is_index | 2 | correct | – |
| F2_index_vs_reversal__pristine_is_reversed | 2 | **WRONG** | yes |

```
fixtures: 12   shipped a repair: 12   shipped the WRONG program: 6 (50% of ships)
refused as AMBIGUOUS: 0
fixtures failing sanity (pristine green / defect red): none
```

Read the pairs, not just the rate. `greens` and `shipped_line` are byte-identical
inside every pair — e.g. both A1 and A2 record
`greens = ['    return readings[1] >= limit', '    return readings[0] > limit']`
and ship the first. **fluidfix emits the same bytes whether that program is the
right answer or the wrong one.** The 50% is therefore not a property of fluidfix's
judgement but the base rate of the kind numbering happening to be lucky; on a corpus
where the correct repair tends to sit at a higher-numbered kind the rate would be
worse, and fluidfix has no mechanism that would notice either way.

The six wrong ships are not near-misses. Shipped vs pristine:

* `readings[1] >= limit` vs `readings[0] > limit` — reads the wrong array element
* `weight_kg >= 21` vs `weight_kg > 20` — threshold moved 1kg on a float domain
* `sum(values[1:]) >= threshold` vs `sum(values[0:]) > threshold` — drops an element
* `min(a, b) >= limit` vs `max(a, b) > limit` — inverted admission rule
* `values[0] + bonus` vs `values[1] - bonus` — wrong element AND wrong operator
* `items[0] - offset` vs `offset - items[1]` — wrong element AND reversed operands

**Classification: `observation`.**

* Observation byte passed: `situation(BUILT=True, AMB=False, CAPPED=False)` = **513**
  (`0x201`). Law's act: **`SHIP`** — correct for that byte.
* Byte that should have been passed: `situation(BUILT=True, AMB=True, CAPPED=False)`
  = **515** (`0x203`). Law's act on it: **`ADD_STATE`** — refuse, ask for one pinning
  test. Verified by direct call to `fluidfix.engine.decide`, attempt 1.

The law was never consulted on the fact it needed. `loop.py:218` computes AMB from
`set_amb or len(sites) > 1`; neither term can see two greens that arrived in
different candidate sets at one line, so the AMB bit was never measured — exactly the
lane the docstring at `loop.py:204-216` claims to cover.

### S3 — FALSE CONFIDENCE (secondary, same runs)

The accepted-repair report positively asserts the thing that is false. `results.json`
records `"ambiguous": false` on all 12, and `RepairResult.summary()`
(`loop.py:66-71`) — the only thing `fluidfix guard` and `fluidfix repair` print
without `--json` — prints `repaired line 5 ... - old + new` and never mentions that a
second, semantically different program also passed. The information exists: `res.greens`
holds both. It is collected, stored, and not shown.

**Classification: `wording`** for the summary line; the `ambiguous: false` field is
the same `observation` defect as above surfacing in the report.

**Aggravating, from source (not measured — no git repo was created, per the brief):**
`loop.py:226` computes `restored_original` — whether the shipped line equals the
committed HEAD content. `grep -rn restored_original src/` shows it is assigned at
`loop.py:226` and **read nowhere in `src/`**. In a git repo all six wrong ships would
have set it `False` while shipping anyway, and no user-facing summary prints it.
A measured signal that contradicts the ship is discarded.

## 5. What defended

* **`set_amb`, when the two greens share a candidate set.** Control `control_G1/`:
  two genuinely different programs (`matrix[0][1]`, `matrix[1][0]`), one line, a
  suite that cannot separate them — refused, tree byte-identical afterwards, with a
  reason that names the real cause and asks for a pinning test. The mechanism is
  correct; its *coverage* is the hole. It fires on `K=1 vs K=2` inside one act and on
  nothing else.
* **Rollback and journalling.** Across 12 fixtures + 1 control + the guard run, every
  refused/rejected candidate was rolled back byte-exactly; the control's file was
  untouched; no `.fluidfix/inflight.json` was left behind. No S2 anywhere.
* **The engine law itself.** Given the correct byte it rules `ADD_STATE`, and given
  the byte it was handed it rules `SHIP`. Every ruling in this wave was correct. No
  `ruling` finding.
* **Act algebra bounded the attack.** Attempts 5 and 6 failed outright: strictness
  flips cannot rescue literal or min/max defects, because a strictness flip only
  moves behaviour at the equality point. The reachable collision shapes are narrower
  than the vocabulary size suggests — but six of them exist, and all six land.

## 6. Verdict

fluidfix did **not** hold: with two different programs green at ONE line in two
different candidate sets, the AMB bit is never measured, the law is asked
`BUILT`-only, and `fluidfix guard` writes one of them to disk and reports "repaired"
— wrong in 6 of 12 fixtures, and provably blind to which 6.
