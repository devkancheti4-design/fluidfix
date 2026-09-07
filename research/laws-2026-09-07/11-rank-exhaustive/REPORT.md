# 11-rank-exhaustive

## 1. Target
All 256 inputs of the ranking law (`src/fluidfix/rank.py`) against the docstring spec; prove the RETRIED veto holds on every input; list the inputs no test pins.

## 2. Method
Read, in full: `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/rank.py`, `/Users/kanchetidevieswar/neo/fluidfix/tests/test_rank_law.py`, `rank_observations` and both of its call sites in `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py` (lines 340-428, 511, 585), and the `repair()` search in `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/loop.py` (lines 163-431).

Scripts, all in this directory, all runnable with `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python`. `timeout.sh` is a perl `alarm` shim because GNU `timeout` is absent on this Mac; every guard run below was `nice -n 15 ./timeout.sh 300 ...`, one at a time.

| script | output | what it does |
|---|---|---|
| `exhaustive.py` | `exhaustive.out` | 256 inputs vs an independently written spec; veto algebra; monotonicity; distribution |
| `pincensus.py` | `pincensus.out` | **measured** pin census: mutate `rank(x)` per input, run every test in `tests/test_rank_law.py` |
| `reach.py` | `reach.out` | which of the 256 inputs the body can construct today (static) |
| `logbytes.py` | `logbytes.out` | logs every observation byte the body hands the law on three Python fixtures |
| `veto_potential.py` | `veto_potential.out` | pre-existing (interrupted run): shows the escalation pass re-trying rejected candidates |
| `veto_measured.py` | `veto_measured.out` | A/B: supply RETRIED at the escalation call from data the body already holds |
| `veto_deadline.py` | `veto_deadline.out`, `veto_sweep.out` | same A/B under a tight escalation budget (`ESC_BUDGET=5,8,12`) |

Nothing outside this directory was written; `src/`, `tests/` and `docs/` were read only. `pincensus.py` imports `tests/test_rank_law.py` read-only and calls its test functions in-process.

## 3. Findings

### 1. All 256 inputs match the docstring spec.
Spec written from the docstring alone ("priority 0..7, lower is examined first"; bits 0..6 are the evidence lanes in order; "no evidence, or vetoed, both land on 7") = index of the lowest set evidence bit, else 7.

```
$ nice -n 15 .venv/bin/python exhaustive.py
A. all 256 inputs vs docstring spec (lowest set evidence bit; 7 if none/veto)
  [ok] 256/256 match, mismatches=[]
  [ok] tests/test_rank_law.py::_spec agrees with this script's spec on 256
```
Independently confirmed by the shipped self-check:
```
$ nice -n 15 ./timeout.sh 280 .venv/bin/fluidfix selfcheck
ranking law vs specification, all 256:       256/256
ranking law veto dominance / monotonicity:   both hold
```

### 2. The RETRIED veto holds on every input, and it is folded into each lane rather than applied afterwards.
```
B. RETRIED veto (bit 7)
  [ok] rank(x | 128) == 7 for all 256 x
  [ok] rank(x) == 7 for exactly the 128 vetoed + input 0 = 129 inputs
  [ok] EV_k(x) == (x & 2^k) * (1 - RETRIED) for every x, every k (7*256 checks)
  [ok] _SITUATION(x) == 128 + (x & 0x7F) * (1 - RETRIED) for every x
  [ok] _EMIT(m) == lowest set bit of m for m in 1..255
  [ok] vetoed inputs all have _SITUATION == 128 (same as no-evidence input 0)
```
The identity `EV_k(x) == (x & 2^k) * (1 - RETRIED)` is the algebraic proof: every one of the seven evidence lanes is independently zeroed by bit 7, so there is no ordering of lanes in which the veto could be outvoted. Monotonicity also holds in both directions (448 add-pairs, 448 remove-pairs, 128 veto-pairs), and `rank(x) == rank(lowest evidence bit of x)` — bits above the lowest set one are ignored entirely.

### 3. Rank 7 conflates "no evidence" with "vetoed"; class sizes are exactly halving.
```
D. rank distribution over all 256 inputs (tie-class sizes)
   rank 0 (    FRAME):  64 inputs
   rank 1 ( FAILONLY):  32 inputs
   ...
   rank 6 (    DENSE):   1 inputs
   rank 7 (no-evidence/RETRIED): 129 inputs
  [ok] class sizes are 64,32,16,8,4,2,1,129
```
A vetoed line and a line with no evidence at all produce the identical internal state (`_SITUATION == 128`). Both go last; the body cannot tell from the ruling which it was. That is the law's design (its docstring says so), not a defect — noted because any future report wording that says "this line was vetoed" cannot be derived from the ruling alone.

### 4. Inputs no test pins: **zero** — and every input is pinned redundantly. This corrects a hand-read census.
`exhaustive.py` section E was written by reading the test file by eye and hard-coding the answer; it suggested ranks 1..6 had no literal pin. That is not a measurement. `pincensus.py` measures it: for each input x, replace `rank(x)` with each of the seven wrong values in turn and run all five tests.
```
$ nice -n 15 ./timeout.sh 300 .venv/bin/python pincensus.py
baseline (no mutation): all tests green

PINNED   : 256/256 inputs
UNPINNED : 0/256 inputs -> []

inputs caught by each test:
   test_all_256_situations_match_the_specification    catches 256   sole pin for   0
   test_guard_orders_a_framed_line_first              catches   2   sole pin for   0
   test_monotone_in_evidence                          catches 127   sole pin for   0
   test_the_orderings_fluidfix_depends_on             catches   4   sole pin for   0
   test_veto_dominates_every_other_bit                catches 128   sole pin for   0

if test_all_256_situations_match_the_specification() were deleted, 256/256
inputs would still be pinned by another test
   rulings that would lose EVERY pin: []
```
I have marked section E of `exhaustive.py` as superseded in the script itself so a human rerunning it is not misled.

### 5. The body never supplies RETRIED. The veto lane is plumbed end-to-end and dead.
`rank_observations` takes `retried: set | None = None` (guard.py:342), defaults it (`retried = retried or set()`, guard.py:394) and passes it to the law (`retried=ln in retried`, guard.py:413). No caller ever supplies it:
```
$ grep -rn "retried" src/ tests/ | grep -v "^src/fluidfix/rank.py"
src/fluidfix/guard.py:342:                      retried: set | None = None) -> list:
src/fluidfix/guard.py:394:    retried = retried or set()
src/fluidfix/guard.py:413:            retried=ln in retried,
tests/test_rank_law.py:50:    assert rank(observe_bits(frame=True, retried=True)) == 7
```
Both production call sites omit it:
```
$ nice -n 15 .venv/bin/python reach.py
2. call sites of rank_observations(...) and whether they pass retried=:
   guard.py:511  retried= passed: False
   guard.py:585  retried= passed: False
```
FAILONLY is likewise never measured — `rank_observations`' own docstring says so ("needs line-level coverage of both sets and is not yet measured — documented, not forgotten"). With bits FAILONLY and RETRIED forced to 0:
```
4. constructible inputs given the bits the body can set
   forced-zero bits: ['FAILONLY', 'RETRIED']
   constructible inputs: 64/256
   reachable rulings: [0, 2, 3, 4, 5, 6, 7]
   unreachable rulings: [1]
```

### 6. Only the Python guard path consults the ranking law at all.
```
$ grep -n "rank" src/fluidfix/javaoracle.py | head
(no output)
$ nice -n 15 .venv/bin/python reach.py
3. does the C path (coracle.py) consult the ranking law?
   'rank_observations' in coracle.py: False
   'from .rank' in loop.py         : False
```
The C path (`coracle.py`) and the Java path (`javaoracle.py`) both accumulate an `attempts` list of rejected candidates (coracle.py:761, javaoracle.py:214) but neither orders its candidate lines by the law.

### 7. In practice the body produces three distinct bytes and two of the eight rulings.
```
$ nice -n 15 ./timeout.sh 280 .venv/bin/python logbytes.py
== count_above (assertion only, no frame): status=repaired file=mod.py rank() calls=3
   byte  40 = SIGNALED+CHEAP                   -> rank 3   x3
== join2 (raising fault, traceback frames mod.py): status=repaired file=mod.py rank() calls=2
   byte  40 = SIGNALED+CHEAP                   -> rank 3   x1
   byte  41 = FRAME+SIGNALED+CHEAP             -> rank 0   x1
== both (novel class -> refusal): status=refused file=None rank() calls=0
Bits ever set across all three fixtures: ['FRAME', 'SIGNALED', 'CHEAP']
```
The larger fixture in `veto_potential.py` adds one more byte, 104 (`SIGNALED+CHEAP+DENSE`, also rank 3). Across every run in this report the observed bytes were {40, 41, 104} and the observed rulings were {0, 3}. NAMED and RECENT were never set on any fixture I ran; whether they fire on real repositories is **unmeasured** here (that is target 15's question).

### 8. Supplying the veto reorders correctly but saves **zero** suite runs on a completed search. This corrects the projection left by the interrupted run.
`veto_potential.out` ends with a projection: "escalation suite runs would be about 3". I measured it instead. `veto_measured.py` runs the same fixture twice, changing exactly one thing: on the escalation call, `retried` is set to the line numbers already rejected in pass 0, rebuilt from `result.tried_log` (whose entries carry `"at" = f"{defect_file}:{obs.lineno}"`, loop.py:331) — precisely the data `guard_once` already holds in its local `attempts` list at guard.py:585, accumulated at guard.py:518.
```
$ nice -n 15 ./timeout.sh 300 .venv/bin/python veto_measured.py
=== A  baseline (ships today: RETRIED never supplied) ===
  repair call 1 (escalation): suite_runs=22 repaired=True at=119 6.5s
    order=[2, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119]
    defect line position in order: 10 of 11
=== B  veto supplied at the escalation call from tried_log ===
  repair call 1 (escalation): suite_runs=22 repaired=True at=119 8.1s
    order=[119, 2, 110, 111, 112, 113, 114, 115, 116, 117, 118]
    defect line position in order: 0 of 11
escalation-pass suite runs   A=22   B=22
escalation suite runs saved by the veto: 0 (0% of the escalation pass)
```
The veto did exactly what the law says — the defect line moved from last to first — and the cost was identical. The reason is in `loop.py:244-263`: `repair()` deliberately collects greens across the **whole** observation list and asks the engine law once at the end, because AMB ("one input carries two outputs") cannot be observed from a single candidate set. The only early exits are `amb_proven` and the deadline. **So in a search that runs to completion, the ranking law's order decides WHICH green ships (`greens[0]`), never how many suite runs it costs.** The projection of ~3 runs assumed an early exit on first green that the body does not perform, by design.

### 9. Where the veto does pay: a deadline-limited escalation, measured.
Same A/B with a tight escalation budget (`escalate_budget`, so `file_share = budget/2` reaches `repair()` as a deadline).
```
$ for b in 5 8 12; do ESC_BUDGET=$b nice -n 15 ./timeout.sh 280 .venv/bin/python veto_deadline.py; done
############ ESC_BUDGET=5 ############
A  repair call 1 (escalation): runs=10 repaired=False at=None
     defect line position in order: 10 of 11
     reason: wall-clock deadline reached mid-search — remaining observations untried
B  repair call 1 (escalation): runs=5 repaired=False at=None
     defect line position in order: 0 of 11
     reason: a candidate passes, but the search was cut short before it could be shown unique — shippin
############ ESC_BUDGET=8 ############
A  runs=11 ... reason: wall-clock deadline reached mid-search — remaining kinds untried
B  runs=10 ... reason: a candidate passes, but the search was cut short before it could be shown unique
############ ESC_BUDGET=12 ############
A  runs=21 ... reason: a candidate passes, but the search was cut short ...
B  runs=20 ... reason: a candidate passes, but the search was cut short ...
```
At budgets 5 and 8 the two arms refuse for **different reasons**. Baseline spends its whole deadline re-testing candidates it already rejected in pass 0 and finds nothing: the engine law is never given BUILT, and the user is told the fault is outside the vocabulary. With the veto, the untried defect line is examined first, the green is found (in 5 suite runs at budget 5, against the baseline's 10 that found nothing), and the engine law rules BUILT+CAPPED -> RAISE_BUDGET — "raise the budget and re-run", which is true and actionable. At budget 12 both arms find it and the difference disappears.

Note the veto can never turn a capped refusal into a repair on this fixture: SHIP requires `_rule(capped=False)`, which is only reached after the complete observation list, and that costs the same 22 runs in either order.

## 4. Lanes

Reached by this work, at the law level (`exhaustive.py`, `pincensus.py`): **all 8 rulings and all 256 inputs**, each verified against the spec and each shown to be pinned by the test suite.

Reached by the body:

| ruling | lane | reached in the body? |
|---|---|---|
| 0 | FRAME | yes — byte 41 on the `join2` fixture |
| 1 | FAILONLY | **never** — the bit is not measured anywhere (guard.py docstring, lines 353-355). Needs line-level coverage of the failing and the passing tests, which `coracle.py`'s gcov tier has for C but nothing collects per-line for Python today. |
| 2 | NAMED | measurable (guard.py:365-380) but never fired on any fixture I ran |
| 3 | SIGNALED | yes — bytes 40 and 104, the commonest ruling observed |
| 4 | RECENT | measurable (`_recent_lines`, needs `root` and `rel`, both passed) but never fired here |
| 5 | CHEAP | measured and set (part of bytes 40/41/104) but never the *lowest* set bit, so never the ruling |
| 6 | DENSE | measured and set (byte 104) but never the lowest set bit, so never the ruling |
| 7 | no-evidence / **RETRIED veto** | reached only as "no evidence". **Never once as the veto**, in any run, because no caller supplies `retried=` |

Never reached and why: ruling 1 (FAILONLY unmeasured); ruling 7-as-veto (RETRIED unmeasured). The observation that would make the veto reachable already exists — `guard_once`'s local `attempts` list at guard.py:585 — and I supplied it from outside `src/` in findings 8 and 9 to show the lane works.

## 5. Potential

- **RETRIED veto, completed search: worth 0 suite runs.** Measured, finding 8: A=22, B=22. This is the number the interrupted run projected as ~3; the projection was wrong.
- **RETRIED veto, deadline-limited escalation: worth the difference between a false refusal and a true one.** Measured, finding 9: at `escalate_budget=5`, baseline spent 10 suite runs and reported "fault is outside this vocabulary"; with the veto, 5 suite runs found the green and the engine law ruled BUILT+CAPPED -> RAISE_BUDGET. The repair existed in both cases. One line of code at guard.py:585 (`retried={int(a["at"].rsplit(":", 1)[1]) for a in attempts ...}`) makes the lane live.
- **How often real runs are budget-limited, and therefore how often that difference is worth having: unmeasured.** This report used one synthetic fixture. Targets 36/37/40 hold the real-repo evidence.
- **FAILONLY (ruling 1): unmeasured.** No fixture can reach it today. Its worth would be the fraction of candidate lines executed only by failing tests; I did not measure that number and will not estimate it.
- **NAMED and RECENT: unmeasured on real code.** Both are implemented and both stayed 0 on all four fixtures I ran.
- **The C and Java paths: entire law unused.** `coracle.py` and `javaoracle.py` order candidate lines without consulting the ranking law at all (finding 6). What that costs is unmeasured here.

## 6. Defects

Classified per the standing principle. **No wrong ruling found: the law is correct on all 256 inputs (findings 1, 2), and every ruling is pinned by a test (finding 4).**

1. **Observation — RETRIED is never measured.** The bit is plumbed from `rank_observations`' signature all the way into `observe_bits` (guard.py:342, 394, 413) and no production caller supplies it (finding 5). The consequence is measured in finding 9: a budget-limited escalation pass re-tests candidates it already rejected and reports "fault is outside this vocabulary" when the repair was one untried line away. The data needed is already in scope at the call site. This is a mismeasured bit, not a missing rule — the law's veto lane is correct and waiting.
2. **Observation — FAILONLY is never measured.** Acknowledged in the body's own docstring (guard.py:353-355). Ruling 1 is unreachable in consequence (finding 5).
3. **Actuation gap, worth stating precisely — the body consults the ranking law only on the Python path.** `coracle.py` (C) and `javaoracle.py` (Java) never call `rank_observations` (finding 6), so on those paths the law rules on nothing.
4. **Not a defect, recorded for accuracy — `rank()` does not mask its input to 8 bits.** `rank(-128)` returns 10, outside the documented range 0..7 (`exhaustive.out` section F). Unreachable in practice: `situation()` and `observe_bits()` can only produce 0..255, and the body calls the law only through `observe_bits`. Wording-level at most.
5. **Defect in prior research in this directory, now corrected.** `veto_potential.py`'s closing line projects "escalation suite runs would be about 3"; measured, the answer is 22 (finding 8). `exhaustive.py` section E's pin census was hand-read, not measured; measured, its conclusion changes (finding 4). Both scripts are kept and both are now annotated as superseded so the numbers are not re-cited as measurements.

## 7. Verdict
The ranking law is correct and completely pinned — 256/256 against its docstring spec, the RETRIED veto proven dominant on every input both exhaustively and algebraically, and zero inputs unpinned by `tests/test_rank_law.py` — but the body measures only six of its eight bits, so ruling 1 is unreachable and the veto lane has never once fired in production; supplying RETRIED from data `guard_once` already holds saves no suite runs in a completed search (measured 22 vs 22) yet, under a tight escalation budget, converts a false "fault is outside this vocabulary" refusal into the true BUILT+CAPPED -> RAISE_BUDGET ruling with the repair found in half the suite runs.
