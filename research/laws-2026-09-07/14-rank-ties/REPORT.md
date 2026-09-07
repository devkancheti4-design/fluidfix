# 14-rank-ties — observation bytes where two classes tie; how the body breaks them

## 1. Target
Find the observation bytes where the ranking law (`src/fluidfix/rank.py`) gives two candidate lines
the same priority; determine how the body breaks those ties (with line numbers); decide whether
tie-breaking is a law ruling or a code decision.

## 2. Method
Pure-law analysis plus instrumented runs. Nothing under `src/`, `tests/`, `docs/` or any other
agent's directory was edited; every spy wraps `fluidfix.rank.rank` / `fluidfix.guard.rank_observations`
in the probe process only. This machine has no `timeout(1)` (`which timeout` -> `timeout not found`),
so the brief's 300 s wrapper was substituted with `nice -n 15 perl -e 'alarm 300; exec @ARGV' --`;
runs were serialised, one at a time.

Read (all under `/Users/kanchetidevieswar/neo/fluidfix/`):
- `src/fluidfix/rank.py` (the law and its docstring specification)
- `src/fluidfix/guard.py:340-428` (`rank_observations`: bit measurement + the sort key), `:495-610` (both call sites)
- `src/fluidfix/loop.py:163-260, 320-415` (`repair`, `tried`, `tried_log`)
- `src/fluidfix/observers.py:28-45` (MechanicalObserver), `:145-166` (ClaudeObserver)
- `src/fluidfix/localize.py:155-165` (packet line order)
- `tests/test_rank_law.py`, `tests/test_engine_fusion.py:154-180`

Scripts in this directory (all rerunnable; interpreter
`/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python`):

| script | what it does | output |
|---|---|---|
| `ties_exhaustive.py` | all 256 bytes: tie-class sizes, masking, body-reachable subset | `ties_exhaustive.out` |
| `tie_break_probe.py` | 5 direct probes of `guard.rank_observations` — which key resolves a tie | `tie_break_probe.out` |
| `ties_realcode.py` | tie-class sizes on 16 **real** fluidfix source files, two failing-output shapes | `ties_realcode.out` |
| `guard_tie_log.py` | ONE real `guard_once` run on `fixture_ties/`; logs every byte + suite runs spent | `guard_tie_log.out` |
| `retried_repay.py` | ONE real `guard_once` run forced into escalation; counts re-paid suite runs | `retried_repay.out` |
| `cheap_cost.py` | wall-clock cost of measuring the CHEAP bit that the law cannot read | `cheap_cost.out` |
| — | static greps | `static_greps.out`, `callsite_greps.out` |

An earlier interrupted run of this target produced everything except `ties_realcode.py`; every one
of its outputs was re-executed in this session and reproduced (only `cheap_cost` wall clock differs
run to run, 5.1 ms vs 7.4 ms total; the 19 % share is identical).

## 3. Findings

### F1 — Ties are not an accident of the encoding; they are the law's specification.
`tests/test_rank_law.py:12-22` states the spec directly: priority = index of the **lowest set
evidence bit**, else 7, with RETRIED a veto. Every bit above the lowest set one is discarded.

```
$ nice -n 15 .venv/bin/python ties_exhaustive.py
== 1. all 256 bytes: size of each priority (tie) class ==
  priority 0:  64 bytes tie
  priority 1:  32 bytes tie
  ...
  priority 7: 129 bytes tie
  distinct bytes that tie pairwise: 10923 of 32640 pairs
== 2. the law discards every bit above the lowest set evidence bit ==
  rank(x) == rank(x & -x) for all 1<=x<128: True
  evidence bits set but not read across the 127 evidenced bytes: 321
```

The law is a **coarse priority-class assignment by design** ("it reads the SITUATION, not the
degree", `guard.py:416-421`). 10,923 of 32,640 byte pairs tie — 33.5 %. That is a property of the
authored kernel, not a defect.

### F2 — In the body only THREE priorities are ever produced, so ties are the normal case, not the edge case.
Two mechanical facts collapse the eight lanes to three:
- `observers.py:39-40` appends an `Observation` **only `if kinds:`**, so SIGNALED (bit 3) is `1` on
  every observation the MechanicalObserver ever emits. Bits above it — RECENT(4), CHEAP(5),
  DENSE(6) — are therefore always discarded.
- FAILONLY (bit 1) is documented as not measured (`guard.py:353-355`: "not yet measured —
  documented, not forgotten; the law reads it as 0 until it is"), so priority 1 is unreachable.

```
== 3. bytes the BODY can construct today (guard.rank_observations) ==
  reachable bytes: 64; priorities reachable: [0, 2, 3, 4, 5, 6, 7]
  priority 1 (FAILONLY) reachable: False
== 4. bytes under the MechanicalObserver (SIGNALED always 1) ==
  reachable bytes: 32; priorities reachable: [0, 2, 3]
  RECENT/CHEAP/DENSE never change the priority when SIGNALED=1: True
  concrete ties (same priority, different evidence):
    p=0: FRAME+SIGNALED  ==  FRAME+NAMED+SIGNALED+RECENT+CHEAP+DENSE
    p=2: NAMED+SIGNALED  ==  NAMED+SIGNALED+RECENT+CHEAP+DENSE
    p=3: SIGNALED  ==  SIGNALED+RECENT+CHEAP+DENSE
```

Measured on real code the prediction holds exactly — 16 fluidfix source files, 1,346 observations,
only priorities {0, 2, 3} ever appear:

```
$ nice -n 15 perl -e 'alarm 300; exec @ARGV' -- .venv/bin/python ties_realcode.py
cli.py                 assert    217    2         175  {2: 175, 3: 42}
guard.py               assert    172    2          45  {2: 45, 3: 127}
guard.py               trace     172    0           1  {0: 1, 2: 44, 3: 127}
lanes.py               assert     20    3          20  {3: 20}
== summary ==
  assert: 16 files, 1346 observations, top class size total 416, files whose top class is a SINGLETON: 0/16
    top-class sizes min/median/max: 2/16/175
    distinct priorities produced: [2, 3]
  trace: 16 files, 1346 observations, top class size total 236, files whose top class is a SINGLETON: 9/16
    top-class sizes min/median/max: 1/1/175
    distinct priorities produced: [0, 2, 3]
== how many observations are in a tie (class size > 1) ==
  assert: 1346/1346 observations sit in a class of >1 (100.0%)
  trace:  1337/1346 observations sit in a class of >1 (99.3%)
```

On a pure assertion failure (no traceback line numbers — the commonest Python shape) **100 % of
observations sit in a tie**, and the best class has a median of 16 members. With a real traceback
frame, 9 of 16 files get a singleton at priority 0 and the rest still tie.

### F3 — The body breaks ties with two keys, neither of which is in the law's byte. `guard.py:425-427`.
```python
    order = sorted(range(len(observations)),
                   key=lambda i: (priority(observations[i]),      # the LAW
                                  -_tokens(observations[i]),      # code key 1: NAMED degree
                                  i))                             # code key 2: incoming index
```
`_tokens` (`guard.py:422-423`) is the **degree** of the NAMED bit — the count of shared name tokens,
where the law reads NAMED as 0/1. `i` is the incoming index, which is the packet's line order
(`localize.py:162`, `lo = [l for l in sorted(frames | expanded) ...]` -> ascending line number).
Both are exercised:

```
$ nice -n 15 .venv/bin/python tie_break_probe.py
== A: identical bytes -> incoming index (line order) breaks the tie ==
  line  3 kinds=[0] byte=00101100 -> priority 2  [NAMED+SIGNALED+CHEAP]
  ... (all five identical) ...
  order chosen: [3, 5, 7, 10, 11]
== B: same bytes, list reversed -> the order flips with the index ==
  order chosen: [11, 10, 7, 5, 3]
== C: equal priority, token DEGREE breaks the tie (Odia incident shape) ==
  line  3 ... priority 2      line  7 ... priority 2
  order chosen: [7, 3]
== D: DENSE line 2 vs CHEAP line 10, both SIGNALED -> same priority, index wins ==
  order chosen: [2, 10]
```
Probe B is the decisive one: the same bytes handed over in reverse produce the reverse order. The
final order is therefore **not a function of the observation bytes alone**.

**Is tie-breaking a code decision?** Key 1 (`-_tokens`) is a *deliberate, documented* code decision,
argued in `guard.py:416-421` on the grounds that the law is binary by design and the degree "belongs
here, under it, never over it". Key 2 (`i`, ascending line number) is an **undocumented, unruled
tie-break**: nothing in `rank.py`, `guard.py` or any test states that earlier lines should be tried
first, and no test pins it (`grep -rn "tie\|_tokens\|degree" tests/test_rank_law.py` -> no match;
`test_guard_orders_a_framed_line_first` pins a *priority* difference, not a tie). Key 2 decides
which line is edited first in every one of the 1,346 real-code observations above.

### F4 — What the arbitrary tie costs: 18 of 19 suite runs on a 9-way tie.
`fixture_ties/` is a 15-line module with four `>=` decoys and the defect at line 13, all inside the
failing test's name tokens, no traceback frame. One real `guard_once`:

```
$ nice -n 15 .venv/bin/python guard_tie_log.py
== guard result ==
  status=repaired file=mod.py seconds=5.8
  call 0: rel=mod.py retried kwarg=None n_obs=9
    line  2..15: byte=00101100 priority=2  [NAMED+SIGNALED+CHEAP]   (all nine identical)
    law order:      [2, 3, 4, 6, 8, 10, 13, 14, 15]
    tie classes (priority -> members): {2: 9}
== suite runs spent (rejected candidates) ==
  rejected total: 19 (+0 unlogged)
  rejected on tied-but-wrong lines: 18 on lines ['10', '14', '15', '2', '3', '4', '6', '8']
  rejected on the defect line 13:  1
  repaired: True  reason: engine law: BUILT -> SHIP
```
Nine lines, one tie class, ordered purely by line number. The defect (13) sat 7th of 9; 18 of the
19 suite runs were spent on tied-but-wrong lines. The repair still landed — the tie costs runs, not
correctness.

### F5 — The RETRIED veto is measured but no caller ever supplies it, so it is dead in the body.
`guard.py:394` (`retried = retried or set()`) and `:413` (`retried=ln in retried`) implement the
bit, and probe E shows it works through the API (`byte=10101100 -> priority 7`). But:

```
$ grep -rn "rank_observations" src/ tests/          # callsite_greps.out
src/fluidfix/guard.py:511:        observations = rank_observations(...)
src/fluidfix/guard.py:585:        observations = rank_observations(...)
$ grep -rn "rank_observations([^)]*retried" src/ tests/
  (no match)
```
Neither call site passes `retried=`, so the set is always empty and priority 7 is reachable only by
the all-zero byte — which the MechanicalObserver cannot emit (F2). Meanwhile `loop.py:185` allocates
`tried: set[tuple[int, str]] = set()` **per `repair()` call**, so the escalation pass starts blind.
Measured cost, one real run on a 267-line fixture (130 decoys, defect at line 265), `--budget 90`:

```
$ nice -n 15 perl -e 'alarm 300; exec @ARGV' -- .venv/bin/python retried_repay.py
== guard result ==
  status=refused file=None seconds=60.7 budget=90 defect_line=265
  hint: ... (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) ...
  call 0 at +  1.3s: retried kwarg=None n_obs=110 defect at position 109
  call 1 at + 31.2s: retried kwarg=None n_obs=135 defect at position 133
== suite runs across both passes (report.attempts, capped 64/pass) ==
  logged rejected candidates: 128
  distinct (line, candidate) pairs: 76
  RE-PAID: same (line, candidate) rejected again in a later pass: 52
  lines touched: 27; most-hit: [('mod.py:4', 6), ('mod.py:6', 6), ('mod.py:8', 6)]
```
**52 of 128 logged suite runs (41 %) re-tested a `(line, candidate)` pair the previous pass had
already rejected**, and the run ended in a refusal at 60.7 s. The guard already holds the data:
`guard.py:518` and `:598` do `attempts += result.tried_log`, whose entries carry
`{"at": "mod.py:<lineno>", "tried": ...}` (`loop.py:347-349, 407-410`).

### F6 — CHEAP is paid for and never read.
`guard.py:399-403` calls `acts.candidates()` for up to two kinds per observation to compute CHEAP —
a bit that F2 proves the law can never reach under the MechanicalObserver.
```
$ nice -n 15 .venv/bin/python cheap_cost.py
observations ranked: 265
rank_observations total (best of 5): 5.1 ms
  of which candidates() for CHEAP:   1.0 ms in 398 calls (19%)
```
19 % of ranking wall clock on a bit that is masked in 100 % of cases. Small in absolute terms
(~1 ms per file); reported as a masking proof, not a performance complaint.

## 4. Lanes
Law lanes (`rank.py`, priorities 0..7):
- **Reached in this work:** 0 (FRAME), 2 (NAMED), 3 (SIGNALED) — the only three the body produces
  (F2, confirmed on 1,346 real-code observations and in two live guard runs); 7 reached at the API
  by passing `retried=` explicitly (probe E) and exhaustively over all 256 bytes in `ties_exhaustive.py`.
- **Never reached by the body:** lane **1 (FAILONLY)** — needs line-level coverage of the failing
  *and* passing sets; `guard.py:353-355` says so outright. Lanes **4 (RECENT), 5 (CHEAP), 6 (DENSE)**
  — measured by `guard.py:410-412` but structurally masked, because SIGNALED (bit 3) is `1` on every
  observation the MechanicalObserver emits (`observers.py:39-40`). Lane **7 (RETRIED veto)** —
  implemented at `guard.py:413`, never supplied by either caller.
- Observation that would make them reachable: lane 1 needs per-line coverage from both test sets
  (`coracle.py` already runs gcov for C; the Python path would need `pytest-cov` line data split by
  outcome — `_has_pytest_cov` at `guard.py:432` already probes for it). Lanes 4-6 become reachable
  only if an observer emits an observation with `kinds == []` (SIGNALED=0); `ClaudeObserver`
  (`observers.py:157-166`) could, but it appends exactly **one** `Observation` per packet, so under
  that observer there is nothing to order and ties are moot. Lane 7 needs the caller to pass
  `retried=` — the data already exists in `result.tried_log`.

## 5. Potential
- **RETRIED wired into the escalation call (`guard.py:585`).** Measured on `fixture_repay/`: 52 of
  128 logged suite runs re-paid (F5). Deriving the set from `report.attempts` is a one-expression
  change *in the body*, not in the law. Caveat, measured: `tried_log` is capped at 64 entries per
  `repair()` call (`loop.py:346, 407`) with the overflow counted only as `tried_more`, so a set
  built from it would be **partial** — how much of the 52 it would actually recover on this fixture
  is **unmeasured**. Generalisation beyond this one fixture is **unmeasured**.
- **FAILONLY (lane 1).** Would insert a class strictly between FRAME and NAMED, splitting the median
  16-member top tie class of F2. How many members it would peel off on real code is **unmeasured** —
  the bit is not computed anywhere today, so it cannot be simulated honestly.
- **Ordering inside a tie class.** F4 shows 18 of 19 suite runs going to tied-but-wrong lines on a
  9-way tie; F2 shows a median top-class size of 16 on real files under an assertion failure. What a
  better in-class order would save across a real corpus is **unmeasured** (this target ran no
  real-repo defect injection).
- **CHEAP.** 19 % of a ~5 ms ranking call (F6); worth roughly 1 ms per file. Negligible as time, but
  a measured indicator that three of the law's seven evidence lanes are inert.

## 6. Defects
No wrong *repair outcome* was produced in any run here: `guard_tie_log.py` repaired correctly
(`engine law: BUILT -> SHIP`) and `retried_repay.py` refused honestly
(`engine law: REFUTED -> HARVEST_COUNTEREXAMPLE`). Three gaps, none of them in a ruling:

1. **Actuation** — `guard.py:585` never passes `retried=`, so the law's RETRIED veto lane cannot
   fire. The ruling is correct and available; the body does not consult the lane it already has.
   Evidence: `callsite_greps.out` (no match for `rank_observations(... retried`), and 52 re-paid
   suite runs in `retried_repay.out`.
2. **Observation** — FAILONLY (lane 1) is never measured, and RECENT/CHEAP/DENSE are measured but
   structurally unreadable because SIGNALED is a constant `1` under the only multi-observation
   observer. Evidence: `ties_exhaustive.out` section 4 (`RECENT/CHEAP/DENSE never change the
   priority when SIGNALED=1: True`), `observers.py:39-40`, `ties_realcode.out`
   (`distinct priorities produced: [0, 2, 3]`).
3. **Wording / unruled key** — the third sort key `i` (`guard.py:427`) is an undocumented tie-break
   on ascending line number, pinned by no test, and it decides trial order for 100 % of observations
   under an assertion failure (F2, F3 probe B). The second key `-_tokens` is a code decision too, but
   a documented and argued one (`guard.py:416-421`). Classified as wording rather than ruling: the
   law made no claim about within-class order, so the code is not contradicting it — it is filling a
   silence without saying so.

## 7. Verdict
Ties are the ranking law's specification, not a flaw — but the body collapses to only three of its
eight lanes (100 % of observations on real code tie under a plain assertion failure, median top-class
16) and breaks those ties with two keys of its own, one documented (NAMED degree) and one silent
(ascending line number); the law's RETRIED veto is implemented at `guard.py:413` yet supplied by no
caller, which cost 52 of 128 re-paid suite runs (41 %) on the one fixture measured here.
