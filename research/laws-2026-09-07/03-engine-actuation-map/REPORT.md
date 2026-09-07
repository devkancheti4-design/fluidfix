# 03-engine-actuation-map — REPORT
(Relayed by the coordinator: the agent's own write of this file was blocked by a
harness rule. Scripts and .out evidence in this directory are the agent's own.)

## 1. Target
For each of the engine law's 8 ACTS: actuated in acts.py/loop.py, partially, or
not at all — table with line numbers.

## 2. Method
Full line-numbered read of engine.py (spec = docstring 16-28), acts.py, loop.py
(sites 217, 391), guard.py (sites 491, 539, 612, 618), cli.py:455-500 (site 474).
Scripts rerunnable via run_bounded.sh (nice -n 15 + perl alarm 300; this Mac has
no timeout/gtimeout): actuation_map.py (mechanical: every decide() site, every
act-name occurrence split comparison/string/comment), enumerate_rulings.py (256
bytes; re-run this session, diff clean vs the interrupted run), ruling_swap_probe.py
(runs a fixture twice, second time with decide() monkeypatched to a different act,
and diffs behaviour — the only way to separate a ruling that DRIVES behaviour from
one that is merely PRINTED), defect_byte.py. probe_capped.out was the empty
interrupted fixture; re-ran to completion, 293.4s. No writes outside the agent
directory; no git state changed.

## 3. Findings

Finding 1 — the table. BEHAVIOURAL = a == "ACT" comparison gates a branch that
changes what the body does; WORDING = the ruling reaches the user only as text;
NONE = the name is absent outside engine.py's ACTS list.

| ACT | Status | Ruled at | Actuated at | Evidence |
|---|---|---|---|---|
| SHIP | BEHAVIOURAL | loop.py:217, guard.py:539, cli.py:474 | loop.py:221 `if ruling == "SHIP"` -> _write() at loop.py:223 | probe_ship.out |
| ADD_STATE | WORDING | loop.py:217, cli.py:474 | never compared; loop.py:237 interpolation only | probe_amb.out |
| ADD_MATERIAL | WORDING | guard.py:491, cli.py:474 | guard.py:491 gates only `hint =` (492-496) | probe_unread.out |
| RESHAPE | NONE | no site can return it | — | actuation_map.out |
| CHANGE_GRANULARITY | WORDING | loop.py:391 | loop.py:392 `ok = False` unconditional; 396 interpolation | probe_hidden.out |
| RAISE_BUDGET | BEHAVIOURAL | guard.py:539, loop.py:217, cli.py:474 | guard.py:539 gates the whole escalation pass (540-616) | probe_capped.out |
| HARVEST_COUNTEREXAMPLE | WORDING | guard.py:539/612/618, cli.py:474 | 612/618 gate only `hint`; harvest at loop.py:407-410 unconditional | probe_refuted.out |
| AUTHOR_SUCCESSOR | NONE | no site can return it | — | actuation_map.out |

2 of 8 change behaviour, 4 are wording, 2 absent.

Finding 2 — acts.py actuates NONE of the 8; the docstring's "actuation table" is
a name collision.
    engine ACTS names occurring in acts.py: NONE
    acts.py defines its own ACTS dict of 9 kind->applier entries, keyed by ROUTER
    act codes 0..15 — a different namespace from the engine law's 8 process acts.
acts.py:302-314 is {5: _flip_strictness, 6: _reduce_literal, ...}. The only SHIP
hit is SHIPPED_KINDS (117, 339). Real actuation lives in guard.py (4 of 7 sites)
and loop.py.

Finding 3 — RAISE_BUDGET genuinely behavioural, end to end. Defect at line 403 of
an 800-line file, outside the round-1 sample:
    == capped: REAL law ==
      layout: bug at line 403, packet truncated=True, bug sampled=False
      [real] status='repaired' reason='engine law: BUILT -> SHIP
             (engine law: CAPPED -> RAISE_BUDGET, depth-first)'
    == capped: SWAPPED law {'RAISE_BUDGET': 'HARVEST_COUNTEREXAMPLE'} ==
      [swap] status='refused' attempts=64 result=None
Same fixture, one ruling swapped: repair becomes refusal.

Finding 4 — the four WORDING acts, each confirmed by swap. ADD_MATERIAL: both
runs candidates=[], no material added in either. CHANGE_GRANULARITY: `why`
differs, repaired=False both, `ok = False` set BEFORE the ruling is compared.
HARVEST_COUNTEREXAMPLE: rejected_candidates=1 in both; only the hint differs.
ADD_STATE: never compared — loop.py:230 `if set_amb or len(sites) > 1` is the CODE
re-testing the facts it fed the law at 218. The refusal is correct but it is the
body's decision, not the law's.

Finding 5 (HEADLINE) — a wrong outcome: the BUILT+CAPPED handoff.
loop.py:193-243 exists so a green under a truncated search reports RAISE_BUDGET
rather than being discarded (loop.py:199 says so). It works. guard_once throws it
away:
    repair() call 0: repaired=False ambiguous=False greens=['K = 1'] acts_tried=[6,9,10]
    repair() call 0: reason='a candidate passes, but the search was cut short ...
                     (engine law: BUILT+CAPPED -> RAISE_BUDGET)'
    [guard] hint='every generated candidate was rejected by the suite
                  (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE) ...'
    'candidate passes' in guard hint: False        mod.py line 1 now: 'K = 0'
One candidate passed the suite, and the report says every one was rejected.
Static cause:
    485: capped0 = acts0 = False
    508: capped0 = capped0 or packet.truncated
    519: acts0   = acts0 or bool(result.acts_tried)
    538: capped0 = capped0 or len(all_files) > len(candidates)
    === does guard.py ever read .greens? ===  NO occurrence of 'greens' in guard.py
Two bits mismeasured at guard.py:539.
  REFUTED: engine.py:24-25 defines it as "candidates were generated AND the suite
  rejected every one"; guard.py:519 measures only the first half, and
  result.greens — the datum supplying the second — is never read.
  CAPPED: guard.py:508/538 fold in packet and file-list truncation but NOT the
  wall-clock cap repair() already measured.
Byte arithmetic:
    loop.py:217 ruled:  situation(BUILT=1, AMB=0, CAPPED=1) -> RAISE_BUDGET
    guard.py:539 built: situation(CAPPED=0, REFUTED=1) -> HARVEST_COUNTEREXAMPLE
                        => gate FALSE, pass stops
    actually is:        situation(CAPPED=1, REFUTED=0) -> RAISE_BUDGET
                        => gate TRUE, pass retries
    the ruling was never wrong. The byte was.
guard.py:520-529 branches on .repaired and .ambiguous only; the third outcome
_rule produces — green-but-capped — has no branch. Not covered by
tests/test_law_never_ruled_wrong.py:35-37, which pins only single-bit CAPPED=True.

Finding 6 — four comments claim actuations that consult no ruling: loop.py:307
("# the engine law's CHANGE_GRANULARITY act, actuated:" above the SpanEdit branch
— a candidate type chosen by a taught applier; nearest ruling is 84 lines away and
wording-only), tests/test_span_edits.py:2 repeating it, and loop.py:58 /
guard.py:50 for HARVEST_COUNTEREXAMPLE above unconditional tried_log.

## 4. Lanes
Reached: SHIP, ADD_STATE, ADD_MATERIAL, CHANGE_GRANULARITY, RAISE_BUDGET,
HARVEST_COUNTEREXAMPLE — all six with live fixtures.
Never reached: RESHAPE and AUTHOR_SUCCESSOR — UNREACHABLE, not merely unactuated.
Both require NOTWIN; no call site sets NOTWIN, SELF, or (outside loop.py:391)
HIDDEN. RESHAPE owns 17 of 256 bytes, AUTHOR_SUCCESSOR 15, and all 32 have NOTWIN
set. The observation that would reach them: NOTWIN is "the thing built is not the
thing wanted" — one unused datum already exists, RepairResult.restored_original
(loop.py:62-64), recording whether a repair equals git-HEAD at that line; a green
differing from a known-good HEAD is a NOTWIN observation. Whether that is a good
bit is UNMEASURED.

## 5. Potential
Finding 5 is the one with a measured number available: the escalation pass
guard.py:539 gates is the same pass that turned refusal into repair in
probe_capped.out, and in builtcapped the correct fix was already in hand as a
green and dropped. Measured: 1 of 1 constructed cases loses a passing green. Rate
on real repos UNMEASURED. ADD_MATERIAL names an action never taken (prints
"install pytest-cov" instead of widening the file set) — value UNMEASURED
(target 43). ADD_STATE only prints the request for a pinning test — UNMEASURED
(target 41). RESHAPE/AUTHOR_SUCCESSOR: 32 of 256 bytes (12.5%) of ruling space
addressable only through a bit no site sets — worth UNMEASURED. Wording-only acts
are not free: Finding 5 shows one overwriting a behavioural RAISE_BUDGET's report.

## 6. Defects
1. OBSERVATION — guard.py:519: acts0 fed as REFUTED measures only "candidates
   generated", not engine.py:24-25's "and the suite rejected every one".
   Evidence: probe_builtcapped.out, defect_byte.out, grep (no 'greens' in guard.py).
2. OBSERVATION — guard.py:508/538: capped0 omits the wall-clock cap repair() measured.
3. WORDING — guard.py:617-621: with a green in hand the hint states "every
   generated candidate was rejected by the suite", which is false. Independently
   wrong: guard could report the green regardless of ruling.
4. WORDING — loop.py:307, loop.py:58, guard.py:50, tests/test_span_edits.py:2.
5. WORDING — engine.py docstring names acts.py as the actuation table; it holds
   zero of the 8 acts.

NO DEFECT FOUND IN ANY RULING. Every act returned was correct for the byte given;
in Finding 5 the byte was wrong.

## 7. Verdict
Two of the engine law's eight acts (SHIP, RAISE_BUDGET) change what the body does,
four are wording only, RESHAPE and AUTHOR_SUCCESSOR are unreachable because no
call site ever sets NOTWIN — and guard_once discards repair()'s BUILT+CAPPED ->
RAISE_BUDGET ruling because it measures REFUTED as "candidates were generated"
rather than "the suite rejected every one", dropping a suite-passing green and
reporting the false claim that every candidate was rejected.
