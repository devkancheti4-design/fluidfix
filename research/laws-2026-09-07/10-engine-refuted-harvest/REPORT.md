# 10-engine-refuted-harvest

## 1. Target
REFUTED and HARVEST_COUNTEREXAMPLE: is any counterexample harvested today, and what would harvesting have given on the Box2D `contact_solver.c` refusal (1,063 candidates)?

## 2. Method
Read (read-only): `/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/engine.py`, `guard.py` (lines 40-115, 486-624, 695-721), `loop.py` (lines 45-62, 300-415), `coracle.py` (lines 58-96, 214-300, 493-540, 670-771), `cli.py` (lines 247-278, 473), `docs/PAIR_LAW_PROMPT.md`, `src/fluidfix/pair.py`, `tests/test_pair_law.py`.

Scripts written and run in this directory (all with `nice -n 15` and the local `tmo.py` timeout wrapper, one at a time, using `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python`):

| script | output | what it measures |
|---|---|---|
| `refuted_table.py` | `refuted_table.out` | all 256 engine inputs; which rule HARVEST_COUNTEREXAMPLE |
| `harvest_cap_fixture.py` / `_fixture2.py` / `_fixture3.py` | `harvest_cap_100.out`, `harvest_cap_100x4.out`, `harvest_cap3_100x4.out` | Python path: harvest cap, multi-file totals, whether a second run reuses the harvest |
| `harvest_cap_wording.py` | `harvest_cap_wording.out` | candidates actually tried vs harvested vs what the refusal SAYS |
| `box2d_harvest_probe.sh` | `box2d_harvest_probe.out` | private Box2D copy: build green, inject the recorded `contact_solver.c:2032` defect, reproduce the `why` string a harvest entry would carry |
| `box2d_why_entropy.py` | `box2d_why_entropy.out` | 12 wrong candidates in `contact_solver.c` through the real `COracle.check()`; distinct `why` values |
| `c_refuted_fixture.py` | `c_refuted.out` | minimal C project through the real `cguard_once()`: what a C REFUTED refusal harvests and says |
| `analyze_harvest.py` | (helper) | tabulates any `.fluidfix/last_refusal.json` |

Fixtures named by the target did not exist, so minimal ones were built here (`crefuted_*`, `capword_*`, `harvestcap*`), stated as such. Box2D was copied into `./box2d` before any injection; the shared clone was never touched, and `box2d_why_entropy.py` verifies `src/contact_solver.c` is byte-exact after each candidate and at exit.

## 3. Findings

### F1. HARVEST_COUNTEREXAMPLE is a 4-of-256 ruling, and only ONE of the four is reachable.
```
$ .venv/bin/python refuted_table.py            # -> refuted_table.out
inputs ruling HARVEST_COUNTEREXAMPLE: 4 of 256
  x= 64 bits=['REFUTED']
  x= 65 bits=['BUILT', 'REFUTED']
  x=192 bits=['REFUTED', 'SELF']
  x=193 bits=['BUILT', 'REFUTED', 'SELF']
...
REFUTED+AMB     -> ADD_STATE
REFUTED+UNREAD  -> ADD_MATERIAL
REFUTED+NOTWIN  -> AUTHOR_SUCCESSOR
REFUTED+HIDDEN  -> CHANGE_GRANULARITY
REFUTED+CAPPED  -> RAISE_BUDGET
HARVEST without REFUTED: []
```
SELF is never measured (`engine.py:27`), so x=192/193 are unreachable; BUILT+REFUTED is contradictory in the body (a BUILT repair returns `status="repaired"` before any refusal is written). The law harvests only when REFUTED is the *sole* evidence bit — every other bit outranks it. That is the law's design, not a defect: harvesting is the residual move when nothing else is left to ask for.

### F2. The harvest IS actuated — as a write. Every rejection carries the test that killed it.
```
$ .venv/bin/python harvest_cap_wording.py 100   # -> harvest_cap_wording.out
N=100 status=refused seconds=34.9
last_refusal.json rejected_candidates:          64
...
  hint: every generated candidate was rejected by the suite (engine law: REFUTED ->
  HARVEST_COUNTEREXAMPLE) — the refusal report lists each one with the test that killed it
```
Entries look like (from `harvest_cap_100.out`):
`{'at': 'mod.py:1', 'tried': 'K = 998', 'why': 'FAILED test_mod.py::test_f - assert 998 == -1'}`.
Written at `guard.py:707-721` (`write_refusal`), fed from `loop.py:346` and `loop.py:407`. Both the Python guard (`cli.py:130`) and the C guard (`cli.py:274`) call it.

### F3. The harvest is NEVER read back. It is a report, not a memory.
```
$ grep -rn "rejected_candidates" src/
src/fluidfix/guard.py:719:               "rejected_candidates": report.attempts[:200]},
$ grep -rn "last_refusal" src/fluidfix/
src/fluidfix/guard.py:702:        os.remove(...)   # clear_refusal
src/fluidfix/guard.py:711:        path = os.path.join(d, "last_refusal.json")
```
One write, one delete, zero reads anywhere in `src/`. Measured consequence — the same guard run twice on the same unrepaired fixture re-tries every candidate it already refuted:
```
$ .venv/bin/python harvest_cap_fixture3.py 100 4   # -> harvest_cap3_100x4.out
[run1] MEASURED candidates tried (oracle.check calls)=404
[run2] MEASURED candidates tried (oracle.check calls)=404
run2 re-tried the same number of candidates as run1: True (404 vs 404)
run2 persisted exactly the same rejected list as run1: True
```
Zero of 404 suite runs were saved by the harvest of the identical prior run.

### F4. The C path never consults the engine law, so a REFUTED refusal is worded as a vocabulary gap.
```
$ .venv/bin/python c_refuted_fixture.py            # -> c_refuted.out
status=refused  seconds=8.5
attempts (harvested rejections): 2
hint: ''

--- report.summary() (what the user is told) ---
REFUSED: fault is outside the taught vocabulary (candidate files tried: scale.c, scale.h).
teach it once: docs/TEACHING.md (or run: fluidfix kinds) 2 candidate(s) were tried and
rejected — each is logged with the test that failed it in the refusal report.

--- .fluidfix/last_refusal.json ---
hint: 'fault class is outside the taught vocabulary; register() it once and its family becomes free'
   {'at': 'scale.c:3', 'tried': '\treturn x * 2;', 'why': '1 test(s) failed, first: ScaleTest'}
   {'at': 'scale.c:3', 'tried': '\treturn 3; * x', 'why': "scale.c:3:12: error: indirection requires pointer operand ('int' invalid)"}

decide(situation(REFUTED=True)) = HARVEST_COUNTEREXAMPLE
grep -c HARVEST_COUNTEREXAMPLE src/fluidfix/coracle.py: 0
```
The vocabulary *did* fire (two candidates generated at the right line); the suite and the compiler rejected both. That is REFUTED. `guard.py:611-621` sets the correct wording on the Python path; `coracle.cguard_once` (`coracle.py:769-771`) returns its refusal with no `hint` at all, so `summary()` falls through to the vocabulary branch (`guard.py:100-104`). The recorded Box2D `contact_solver.c` refusal ran down exactly this path.

### F5. The harvest cap silently drops rejections, and the refusal counts only what survived the cap.
`loop.py:346/407` keeps at most 64 entries per `RepairResult` and counts the rest in `tried_more`; `guard.py:518/598` sums `tried_log` only and never reads `tried_more`; `guard.py:719` truncates the JSON at 200.
```
$ .venv/bin/python harvest_cap_wording.py 100
candidates ACTUALLY tried (oracle.check calls): 101
GuardReport.attempts (harvest kept):            64
RepairResult.tried_more (rejections dropped):   unavailable (refusal path attaches no RepairResult)
last_refusal.json rejected_candidates:          64
summary() tail: ...64 candidate(s) were tried and rejected — each is logged with the test that failed it
in last_refusal.json keys: ['candidates', 'hint', 'rejected_candidates', 'seconds', 'status']
```
100 candidates were tried; the user is told 64, with no marker that anything was dropped. Multi-file confirmation (`harvest_cap3_100x4.out`): 400 tried, `attempts`=256 (4 files x 64), JSON=200.

### F6. What harvesting would have given on the Box2D `contact_solver.c` refusal.
The 1,063 figure is recorded at `docs/PAIR_LAW_PROMPT.md:30`, `src/fluidfix/pair.py:50` and `tests/test_pair_law.py:60,95`. `contact_solver.c` is one file, hence one `RepairResult`, hence one 64-entry cap:

- **64 of 1,063 rejections would have been kept — 6.0%.** 999 counterexamples (94.0%) would have been discarded with no record that they existed. Arithmetic on F5's measured cap, not an estimate of the search.
- The refusal would have read **"64 candidate(s) were tried and rejected"** and, per F4, would have blamed the taught vocabulary rather than saying every candidate was refuted.
- Each kept entry would carry a **test name only**, not a value. Reproduced end-to-end on a private Box2D copy with the recorded defect injected at `src/contact_solver.c:2032`:
```
$ ./box2d_harvest_probe.sh                     # -> box2d_harvest_probe.out
== pristine run ==   112 tests, "All Box2D tests passed!"
- b2ContactConstraintWide* c = constraints + wideIndex;
+ b2ContactConstraintWide* c = constraints - wideIndex;
defect run rc=1 ... test failed: DeterminismTest
harvest why = '2 test(s) failed, first: MultithreadingTest'
```
- **The `why` barely discriminates.** 12 wrong candidates in `contact_solver.c` through the real `COracle.check()`:
```
$ .venv/bin/python box2d_why_entropy.py 12     # -> box2d_why_entropy.out
baseline green: True
candidates checked: 12
green (accidentally passing): 8
rejections: 4  DISTINCT why values: 2
    3  '2 test(s) failed, first: MultithreadingTest'
    1  'suite red'
total wall time 65.4s, mean per candidate 5.45s
```
3 of 4 rejections harvested byte-identical text; the fourth harvested the literal string `suite red` — the runner printed no parsable test name, so that entry carries no information beyond "not green". The distinct-`why` count over the full 1,063 is **unmeasured**; the measured sample is 2 distinct values over 4 rejections at one site.
- Side observation, outside this target: 8 of the 12 single-token mutations left the Box2D suite green. That is an oracle-strength measurement, not a harvest one, and is not pursued here.

## 4. Lanes
Reached:
- `REFUTED alone -> HARVEST_COUNTEREXAMPLE` (x=64). Reached on the Python path (F2, F5) and on the C path (F4) — on C the ruling is reached by the *situation*, never by the code, which never calls `decide()`.
- The masking lanes around it: REFUTED+CAPPED -> RAISE_BUDGET, REFUTED+AMB -> ADD_STATE, REFUTED+UNREAD -> ADD_MATERIAL, enumerated exhaustively over all 256 inputs (F1) but not exercised in a live run here.

Never reached:
- x=192, x=193 (REFUTED+SELF): SELF is never measured by the body (`engine.py:27`). It would need an observation that fluidfix is repairing its own source — e.g. `oracle.root` resolving inside fluidfix's own package.
- x=65 (BUILT+REFUTED): the body returns `status="repaired"` the moment a candidate is green (`guard.py:598-602`), so BUILT and a refusal never coexist in one report. Reaching it would need a report that carries both a landed repair and a still-refuted sibling file.
- The *consumption* side of HARVEST_COUNTEREXAMPLE has no lane at all: nothing in `src/` reads the harvest back (F3), so the act's second half — using a counterexample — is unbuilt rather than unreached.

## 5. Potential
- **Not re-trying known-refuted candidates.** Measured ceiling on a controlled fixture: a second guard pass re-ran 404 of 404 candidates (F3). Every one of those was already in `last_refusal.json` with the test that killed it, so a read-back would have cut the second pass to 0 candidate suite runs. On the Box2D shape this is worth `1,063 x 3.5s ~ 1 hour` of rebuild-and-run per repeated pass (3.5s/candidate from `pair.py:50`; my own measured mean on `contact_solver.c` was 5.45s/candidate over 12 candidates, `box2d_why_entropy.out`). Whether a *later* pass on a *changed* tree may reuse the negatives is **unmeasured** and is the real design question — a candidate refuted against yesterday's tree is not automatically refuted against today's.
- **Raising or reporting the cap.** Cost of keeping all 1,063 entries instead of 64: at the ~100 bytes/entry the measured Box2D entries occupy, roughly 100 KB of JSON. The *value* of the extra 999 entries is bounded by F6's discrimination result — on the measured sample they would collapse onto 2 distinct `why` strings, so most of the 999 would be near-duplicates. The right first move is cheaper than raising the cap: carry `tried_more` through to the report so the count is honest.
- **A richer `why` on C.** The entry that read `suite red` cost a full build-and-run and stored nothing. What a stronger observation would be worth is **unmeasured**; the observation that would make it possible is the failing *assert frame* (file:line), which `_FRAME` (`coracle.py:60-62`) already parses for file ranking but which `check()` does not put into `why`.

## 6. Defects
1. **WORDING — the C guard's refusal names the wrong cause.** Evidence F4: candidates were generated and every one was refuted, yet `summary()` says "fault is outside the taught vocabulary" and the JSON hint says "register() it once". `coracle.py` contains zero references to the engine law's acts (`grep -c HARVEST_COUNTEREXAMPLE src/fluidfix/coracle.py` -> 0), so `cguard_once`'s final `return GuardReport(...)` (`coracle.py:769-771`) omits the `hint=` that `guard.py:617-621` sets on the identical situation. This is the wording of a correct ruling, not the ruling: `decide(situation(REFUTED=True))` returns HARVEST_COUNTEREXAMPLE on both paths. It is the path the recorded Box2D refusal took. Fix shape: `cguard_once` sets the REFUTED hint exactly as `guard_once` does — a missing consultation of a lane the law already has, not a new decision.
2. **WORDING — the refusal under-reports how many candidates were tried.** Evidence F5: 100 tried, "64 candidate(s) were tried and rejected", no marker. `RepairResult.tried_more` counts the drop (`loop.py:351,412`) but is never summed into `GuardReport` and is unreachable on the refusal path because `GuardReport.result` is None there. Projected onto the recorded Box2D refusal (F6) the report would have said 64 where 1,063 were tried. Again wording/plumbing, not a ruling.
3. **ACTUATION — HARVEST_COUNTEREXAMPLE is half-actuated.** Evidence F3: the harvest is written and never read. "Harvest" as an act implies the crop is used; today only the writing exists. Classified as actuation rather than defect-in-the-ruling: the law ruled HARVEST on a REFUTED situation and that ruling is right; the body implements only the first half of it.
4. No defect found in any **ruling**, and none in the **observation** of REFUTED: on every fixture measured here the bit was set exactly when candidates existed and all were rejected.

## 7. Verdict
The counterexample harvest is written on both the Python and the C path but read by nothing in `src/`, capped at 64 rejections per file so the recorded 1,063-candidate `contact_solver.c` refusal would have kept 6.0% of its counterexamples and reported 64 as the count — and on the C path would have blamed the taught vocabulary instead of naming REFUTED, because `coracle.py` never calls `decide()`; three wording/actuation defects, zero wrong rulings.
