# 04-engine-amb-adversarial — REPORT

## 1. Target
Build programs where two green candidates are one program spelled twice (`units >= 10` vs `units > 9`) versus two genuinely different programs; test whether the body's AMB measurement (`set_amb`, distinct `sites` in `src/fluidfix/loop.py`) classifies each correctly; hunt for a misclassification.

## 2. Method
Read (no edits): `src/fluidfix/engine.py` (law, docstring), `src/fluidfix/loop.py` (the measurement: `sites` at :203, `AMB=set_amb or len(sites) > 1` at :218, `green_at_set_start` at :304, `set_amb = True` at :404, `amb_proven` at :416), `src/fluidfix/acts.py` (appliers, `candidates()`), `src/fluidfix/lanes.py` (`EMIT` = lowest live bit, so kinds run in ascending kind number), `src/fluidfix/observers.py` (MechanicalObserver reports every kind whose regex matches the line), `src/fluidfix/guard.py:340-437,439-530` (`rank_observations` reorders lines, never truncates kinds; `guard_once` calls `repair`), `src/fluidfix/coracle.py:621,759` (C adapter uses the same `KINDS` and the same `repair()`), `tests/test_engine_fusion.py`, `CHANGELOG.md:24-42,541-544` (the spec wording for AMB).

Spec as written (CHANGELOG.md:34-39): *"AMB is true in two measured shapes: two greens inside one candidate set … or greens at two different lines … Two spellings of one program at one site (`units >= 10` vs `units > 9`) are NOT ambiguity and are still shipped."* engine.py:17: *"AMB two DIFFERENT candidates both pass the suite"*.

Scripts written, all in this directory (rerunnable):
- `amb_fixtures.py` — 8 fixtures (mod.py + weak test_mod.py each, materialised under `runs/`). Each runs (a) `repair()` directly with the MechanicalObserver's kinds for the named lines and (b) `guard_once(oracle, MechanicalObserver(), escalate=False)` end-to-end, with a wrapper around `fluidfix.loop.decide` logging every situation byte the body sends the law (no src edit), then a hidden pinning test against whatever shipped. Output: `run1.log`, `run2-F4c.log`, `results.json`.
- `distinguish.py` — report-only observation prototype: probes the two green programs of each fixture with 2000 shared random int inputs and counts disagreements. Output: `distinguish.log`, `distinguish.json`.
- `multikind_census.py` — read-only count of source lines carrying >=2 kind signals (exposure to the shape found). Output: `census.log`.
- `with_timeout.sh` — `timeout(1)` substitute (this macOS host has no `timeout`/`gtimeout` binary; `perl alarm` with the same semantics).

Commands (each run once, sequentially, under `nice -n 15` and a 300 s alarm):
```
nice -n 15 ./with_timeout.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python amb_fixtures.py        # run1.log
nice -n 15 ./with_timeout.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python amb_fixtures.py F4c    # run2-F4c.log
nice -n 15 ./with_timeout.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python distinguish.py         # distinguish.log
nice -n 15 ./with_timeout.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python multikind_census.py \
    /Users/kanchetidevieswar/neo/fluidfix/src/fluidfix <scratchpad>/box2d/src <scratchpad>/cglm/include    # census.log
```
The law's rulings on the bytes involved (`.venv/bin/python -c` over `engine.decide/situation`):
```
{'BUILT': 1}                             byte=0x201 -> SHIP
{'BUILT': 1, 'AMB': 1}                   byte=0x203 -> ADD_STATE
{'BUILT': 1, 'CAPPED': 1}                byte=0x221 -> RAISE_BUDGET
{'BUILT': 1, 'AMB': 1, 'CAPPED': 1}      byte=0x223 -> ADD_STATE
```

## 3. Findings

Summary table (`run1.log` + `run2-F4c.log`, last block):
```
fixture                                          spec       direct     guard      pin(direct/guard)
F1-spelled-twice-one-site                        SHIP       SHIP       SHIP       PASS/PASS
F2-two-programs-one-set                          ADD_STATE  ADD_STATE  ADD_STATE  n/a (refused)/n/a (refused)
F3-two-programs-two-sites                        ADD_STATE  ADD_STATE  ADD_STATE  n/a (refused)/n/a (refused)
F4-two-programs-one-site-two-acts                ADD_STATE  SHIP       SHIP       FAIL/FAIL
F4b-two-programs-one-site-two-acts-swapped-roles ADD_STATE  SHIP       SHIP       PASS/PASS
F4c-F4-plus-one-pinning-test                     SHIP       SHIP       SHIP       PASS/PASS
F5-one-program-twice-in-one-set                  SHIP       ADD_STATE  ADD_STATE  n/a (refused)/n/a (refused)
F6-one-program-two-sites                         ADD_STATE  ADD_STATE  ADD_STATE  n/a (refused)/n/a (refused)
```
"spec" is the ruling the CHANGELOG wording implies for the situation as a human reads it; "direct"/"guard" are what the body measured and the law then ruled; "pin" is a hidden test of the intended program against the shipped file.

**F-1. The two-spellings case is classified correctly (SHIP).** `if units > 10:` (correct `>=`); kind 0 yields `units >= 10`, kind 1 yields `units > 9`, both green, at one site from two acts. `set_amb`=False, `sites`=1 → byte 0x201 → SHIP; shipped `units >= 10`; pin PASS. Excerpt (`run1.log`):
```
F1-spelled-twice-one-site
  [guard] ruling=SHIP matches_spec=True pin=PASS suite_runs=4
    greens (2): ['if units >= 10:', 'if units > 9:']
    shipped: 'if units >= 10:' at line 2
    law consulted with: ['0x201=BUILT->SHIP']
```

**F-2. Two different programs inside one candidate set are classified correctly (ADD_STATE).** `return a - b - c` with test `net(1,2,2)==1`; kind 3's set holds `a + b - c` and `a - b + c`, both green → `set_amb`=True → 0x203 → refuse. Excerpt:
```
F2-two-programs-one-set
  [guard] ruling=ADD_STATE matches_spec=True ... suite_runs=4
    greens (2): ['return a + b - c', 'return a - b + c']
    law consulted with: ['0x203=BUILT+AMB->ADD_STATE']
    reason: AMBIGUOUS: 2 candidates at 1 different lines (2) all pass the suite ...
```

**F-3. Two different programs at two sites (the Unity cancel shape) are classified correctly (ADD_STATE).** `g: return x + 2` (defect) / `f: return g(x) + 1`; test `f(1)==3` is greened by `x + 1` at line 2 and by `g(x)` at line 4 → `sites`=2 → 0x203 → refuse. Excerpt: `greens (2): ['return x + 1', 'return g(x)']`, `reason: AMBIGUOUS: 2 candidates at 2 different lines (2, 4) ...`.

**F-4. MISCLASSIFICATION FOUND: two DIFFERENT programs at ONE site from TWO acts measure AMB=False and the wrong one ships.** `return base - delta` (intended `base + delta`), weak test `apply_delta(0, 5) == 5`. Kind 2 (swap operands; lowest kind bit, so it runs first) yields `return delta - base` — green; kind 3 (flip additive) yields `return base + delta` — green; kind 11's `delta - base` is deduplicated by `tried`. Two greens, `set_amb`=False (different candidate sets), `sites`={2}. The body asked the law with 0x201 (BUILT only); the law ruled SHIP; `greens[0]` = the kind-2 candidate was written. Both the direct call and the full guard path (`status=repaired`) did this. The hidden pinning test `apply_delta(10, 5) == 15` FAILS on the shipped file (it returns -5). Excerpt (`run1.log`):
```
F4-two-programs-one-site-two-acts
  [direct] ruling=SHIP matches_spec=False pin=FAIL suite_runs=3
    observations: [(2, [2, 3, 11])]
    greens (2): ['return delta - base', 'return base + delta']
    shipped: 'return delta - base' at line 2
    law consulted with: ['0x201=BUILT->SHIP']
  [guard] ruling=SHIP matches_spec=False pin=FAIL suite_runs=3
    guard status: repaired file=mod.py
```
On-disk evidence (`diff` of the guard run dir against the fixture source):
```
2c2
<     return base - delta
---
>     return delta - base
```
The two greens are proven different programs by `distinguish.py`: `974/2000` random inputs disagree, witness `apply_delta(-10, -5): ('ok', 5) vs ('ok', -15)` (`distinguish.log`).

**F-5. Which of the two greens ships is decided by kind numbering, not by evidence.** F4b: identical line and test, intended program `delta - base` instead. Same measurement (0x201 → SHIP), same shipped text, now pin PASS. Between F4 and F4b nothing observable to the body changed; the shipped program is `greens[0]`, i.e. the lowest kind number's candidate (`EMIT(m) = m & -m`, lanes.py:20). Excerpt: `F4b ... [guard] ruling=SHIP matches_spec=False pin=PASS ... shipped: 'return delta - base'`.

**F-6. The one pinning test ADD_STATE would have asked for resolves F4 in 3 suite runs.** F4c adds `assert apply_delta(10, 5) == 15` to the suite; kind 2's candidate goes red, kind 3's is the lone green → 0x201 → SHIP `return base + delta`, pin PASS (`run2-F4c.log`: `greens (1): ['return base + delta']`, `suite_runs=3`). The body never asked for that test because it never measured AMB.

**F-7. MISCLASSIFICATION FOUND (mirror image): one program spelled twice INSIDE one candidate set measures AMB=True and a repairable defect is refused.** `return (n + 1) * (n + 1) // 2` (intended `n * (n + 1) // 2`, tests `tri(1)==1, tri(3)==6, tri(4)==10`). Kind 1's single set yields `(n) * (n + 1) // 2` then `(n + 1) * (n) // 2`; both green (commutative product) → `set_amb`=True → 0x203 → ADD_STATE, tree untouched. `distinguish.py`: `0/2000` disagreements. This is the shape the spec exempts ("two spellings of one program at one site … NOT ambiguity"), but the exemption is only realised for spellings that come from *different* acts. Excerpt (`run1.log`):
```
F5-one-program-twice-in-one-set
  [guard] ruling=ADD_STATE matches_spec=False ... suite_runs=3
    greens (2): ['return (n) * (n + 1) // 2', 'return (n + 1) * (n) // 2']
    law consulted with: ['0x203=BUILT+AMB->ADD_STATE']
    reason: AMBIGUOUS: 2 candidates at 1 different lines (2) all pass the suite — ... one may CANCEL the fault ...
```

**F-8. One program at two sites refuses, by the spec's sites rule.** F6: `LIMIT = 10` / `return units > LIMIT`; kind 0 at line 3 (`>=`) and kind 1 at line 1 (`LIMIT = 9`) both green; `sites`=2 → 0x203 → refuse; `distinguish.py`: `0/2000` disagreements on every function. CHANGELOG defines greens at two lines as AMB ("two contradictory claims about where the fault is"), so this is by design; the module-level constant does differ between the two greens (observable if `LIMIT` were imported elsewhere), so "one program" is only extensionally true here.

**F-9. The differential probe is an observation that separates the two shapes; the body's proxy does not.** Against the spec's "different program" reading: probe agrees on 6/7 fixtures (all but F6, where the sites rule is deliberately about *where*), body today 4/7 (`distinguish.log`, last lines).

**F-10. Exposure census (`census.log`).** Lines whose signal fires >=2 shipped kinds — i.e. lines where two different acts are tried at one site, the precondition for F-4:
```
/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix
  code lines 3590, >=1 kind signal 1194, >=2 kind signals 345 (28.9% of signal lines)
  top kind pairs: (1,3)x140, (0,1)x137, (0,10)x111, (1,10)x69, (3,11)x54, (1,11)x52, (0,3)x37, (2,3)x25
.../scratchpad/box2d/src
  code lines 27697, >=1 kind signal 17537, >=2 kind signals 7012 (40.0% of signal lines)
  top kind pairs: (0,1)x5989, (0,10)x1161, (1,3)x1099, ...
.../scratchpad/cglm/include
  code lines 19808, >=1 kind signal 10812, >=2 kind signals 1564 (14.5% of signal lines)
  top kind pairs: (1,3)x1134, (3,11)x517, (1,11)x510, ...
```
Caveat, measured: kind 0's signal `[<>]=?` fires on C's `->` and kind 1's on digits in identifiers — `'b2Body* b = shape->body;' -> [0, 1]` — so the Box2D figure is an upper bound inflated by C idiom. These counts are the precondition (two acts at one site), not the event (two greens); how often two acts both green on a real suite is **unmeasured**. The C adapter reuses `KINDS` and `repair()` (coracle.py:621, :759), so the F-4 shape is reachable from `cguard` as well — **unmeasured** on the C clones.

## 4. Lanes
Engine-law bytes the body sent to `decide` in this work (logged by the wrapper): **0x201 BUILT → SHIP** (F1, F4, F4b, F4c) and **0x203 BUILT+AMB → ADD_STATE** (F2, F3, F5, F6). Both via `_rule(capped=False)` (loop.py:424). Both rulings match the engine docstring for the byte given.

Within the AMB measurement, the two shapes the body can set were both reached: `set_amb` (F2, F5) and `len(sites) > 1` (F3, F6). The third shape — two different programs from two candidate sets at one site (F4) — has **no bit** in the body: it is measured as 0x201.

Never reached here: **0x221 BUILT+CAPPED → RAISE_BUDGET** (needs a deadline expiring with a green already found; no deadline was passed). **0x223 BUILT+AMB+CAPPED**: by reading loop.py:415-419, whenever AMB is measured true `amb_proven` breaks both loops straight to `_rule(capped=False)` before any deadline check at :269/:285 can run, so this byte appears unreachable from `repair()` today (reading only, not exercised). **0x210 HIDDEN** (no flaky suite here), UNREAD/REFUTED/NOTWIN/SELF — outside this target.

## 5. Potential
- Measuring AMB as "different programs" rather than "different set / different line" would have turned F4 from a shipped wrong repair (pin FAIL) into an ADD_STATE refusal, and F5 from a refusal into a SHIP; on these fixtures the probe observation matched the spec reading on 6/7 vs the body's 4/7 (F-9). Cost of the probe on the fixtures: 2000 in-process calls, zero suite runs; cost and feasibility on real repos (non-integer signatures, side effects, C) — **unmeasured**.
- ADD_STATE's actuation (ask for one pinning test) resolved F4 in 3 suite runs once the test existed (F-6); today the ask is never made in the F4 shape because the bit reads False.
- Reach of the F4 shape: 28.9% (fluidfix src), 14.5% (cglm), <=40.0% (Box2D, inflated) of signal lines carry >=2 kind signals (F-10). Fraction of those where a real weak suite greens two acts: **unmeasured**.
- A cheaper partial observation, no probing: "greens from >=2 acts at one site" is already known to the body (`res.acts_tried`, `greens`) and would at least name the F4 shape as distinct from F1 in the report; whether it should read as AMB is a question the probe answers and the act-pair count does not (F1 and F4 are both "2 acts, 1 site").

## 6. Defects
**D-1 (observation) — AMB under-measured: two different programs, two acts, one site read as BUILT only.** Evidence F-4, F-5, F-9. Law ruled SHIP on byte 0x201; the situation as the spec defines it ("two DIFFERENT candidates both pass") was 0x203, on which the same law rules ADD_STATE (Method table). Measurement site: loop.py:218 `AMB=set_amb or len(sites) > 1` with `set_amb` only settable inside one set (:304, :400-404). Consequence measured: `status=repaired`, wrong program on disk, hidden pin FAIL. Not a ruling defect: the law was never given AMB.

**D-2 (observation) — AMB over-measured: two spellings of one program inside one candidate set read as AMB.** Evidence F-7 (0/2000 disagreements). Law ruled ADD_STATE on 0x203; per the spec exemption the situation was 0x201 → SHIP. Measurement site: loop.py:400-404. Consequence: a safe refusal of a repairable single-token off-by-one; tree untouched. Wording follow-on: the refusal text says "one may CANCEL the fault" of two programs that are equal on every probed input — hedged by "may", so not counted as a separate wording defect.

**D-3 (code order, not a ruling) — which green ships under D-1 is `greens[0]`, i.e. the lowest kind number (F-5).** Harmless when the two greens are one program (F1), decisive when they are not (F4 vs F4b). It only matters because of D-1; with AMB measured, nothing ships.

No ruling defect found: on every byte the body actually sent, the law's act matched engine.py's docstring.

## 7. Verdict
The body's AMB proxy (`set_amb or sites>1`) measures *where* two greens came from, not *whether they are the same program*, so it ships one of two different programs when they come from two acts at one site (F4: wrong repair on disk, pin FAIL) and refuses one program spelled twice when both spellings sit in one candidate set (F5); the law ruled correctly on every byte it was given.
