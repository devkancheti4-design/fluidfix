# 07-engine-precedence — REPORT

## 1. Target
When several engine-law bits are set (BUILT+AMB+CAPPED, BUILT+HIDDEN+AMB, ...), which act wins and why, algebraically from `act = (4 & ntzb(x-7)) + ntzb(x + (x&128))`; does that precedence match the intended one in the docstring?

## 2. Method
Read: `src/fluidfix/engine.py` (law, BITS, ACTS, `situation()`, `decide()`), `src/fluidfix/loop.py` lines 163-300 and 340-440 (the `_rule()` closure and both `decide()` call sites), `src/fluidfix/guard.py` lines 439-630 (four `decide()` call sites), `src/fluidfix/localize.py` 130-181 (packet filter, spread sample, `truncated`), `src/fluidfix/observers.py` (MechanicalObserver), `src/fluidfix/cli.py` 464-476 (selfcheck engine section), `tests/test_engine_fusion.py`, `CHANGELOG.md` 22-72 and 530-562, `docs/PROOF.md` engine sections.

Ran (all from this directory, all read-only against `src/`):
- `precedence.py` -> `precedence.out`: exhaustive 256-byte analysis; algebraic model; precedence ladder; all 28 pairs; all 21 BUILT-triples; body-constructible bytes; documented-intent check; citation-audit coverage.
- `.venv/bin/fluidfix selfcheck` -> `selfcheck.out`.
- `packet_capped_fixture.py` -> `packet_capped_fixture.out`: one real `guard_once` run on a fixture built here (`fixture-packet-capped/`).
- `packet_capped_counterfactual.py` -> `packet_capped_counterfactual.out`: one real `repair()` run with full sight on the same broken fixture (`fixture-packet-capped-full/`).

Note: macOS has no `timeout`/`gtimeout`; `timeout.sh` (perl `alarm`, same contract) is the substitute. Every run used `nice -n 15 ./timeout.sh 300 ...`, one at a time. No fixture the target names exists; the two fixtures above were built here.

## 3. Findings

### F1. The formula decomposes exactly into "lowest set evidence bit wins" plus one borrow correction — verified on 256/256.
`x = obs | 512`. Second term `ntzb((x + (x&128)) & 254)`: adding `x&128` clears SELF (bit 7, carry into bit 8, masked away), so it is the index of the lowest set bit among AMB(1) UNREAD(2) NOTWIN(3) HIDDEN(4) CAPPED(5) REFUTED(6), or 0 if none. BUILT (bit 0) is masked by `& 254`. First term `4 & ntzb((x-7) & 254)`: subtracting 7 borrows through the low three bits; it is 4 only when the lowest set bit of `x-7` lands at index 4..7, which happens in exactly two shapes (see F3). Ruling = `(T1 + T2) mod 8`.
```
$ nice -n 15 ./timeout.sh 300 .venv/bin/python precedence.py   (PART 2)
  model == decide on 256/256 bytes; mismatches: []
  (4 & ntz(x-7)) + ntz(x+(x&128)) mod 8 == decide on 256/256; mismatches: []
  job-invariance (bits 8-9 = 0..3): 0/256 bytes differ
```

### F2. Precedence order: AMB > UNREAD > NOTWIN > HIDDEN > CAPPED > REFUTED; BUILT and SELF never win against any of those six.
The ladder "ruling of the highest-precedence set bit, SHIP if none" predicts 226/256; every one of the 30 exceptions is one of the two borrow families in F3. SHIP is ruled on exactly four bytes: `(none)`, `BUILT`, `SELF`, `BUILT+SELF`. Any bit of AMB..REFUTED vetoes SHIP (126 of the 128 BUILT bytes are not SHIP; the two that are have only SELF beside BUILT).
```
(PART 3)
  ladder predicts decide on 226/256; exceptions: 30
  bytes ruling SHIP: ['(none)', 'BUILT', 'SELF', 'BUILT+SELF']
  BUILT set but ruling != SHIP: 126/128 (every one has some bit of AMB..REFUTED set: True)
(PART 4, excerpt)
  BUILT+AMB          -> ADD_STATE               wins: AMB
  BUILT+CAPPED       -> RAISE_BUDGET            wins: CAPPED
  BUILT+HIDDEN       -> CHANGE_GRANULARITY      wins: HIDDEN
  AMB+CAPPED         -> ADD_STATE               wins: AMB
  HIDDEN+CAPPED      -> CHANGE_GRANULARITY      wins: HIDDEN
  CAPPED+REFUTED     -> RAISE_BUDGET            wins: CAPPED
(PART 5, the target's named cases)
  BUILT+AMB+CAPPED             -> ADD_STATE               wins: AMB
  BUILT+AMB+HIDDEN             -> ADD_STATE               wins: AMB
```
Ruling census (PART 1): SHIP 4, ADD_STATE 113, ADD_MATERIAL 64, RESHAPE 17, CHANGE_GRANULARITY 16, RAISE_BUDGET 23, HARVEST_COUNTEREXAMPLE 4, AUTHOR_SUCCESSOR 15.

### F3. The 30 exceptions are two algebraic families where NEITHER set bit's own ruling wins.
- Family A (15 bytes): BUILT=AMB=UNREAD=0, NOTWIN=1, plus any of HIDDEN/CAPPED/REFUTED/SELF -> AUTHOR_SUCCESSOR (ladder would say RESHAPE). Borrow: `x-7` with low three bits zero gives `(hi-1)<<3 | 1`; with NOTWIN set, `hi-1` is even, so the lowest set bit sits at index 4..7 -> T1=4, T2=3, 4+3=7.
- Family B (15 bytes): BUILT=AMB=UNREAD=1, NOTWIN=0, plus any of HIDDEN/CAPPED/REFUTED/SELF -> RAISE_BUDGET (ladder would say ADD_STATE). No borrow: `x-7` clears bits 0..2, NOTWIN clear, so lowest set bit is at 4..7 -> T1=4, T2=1, 4+1=5.
```
(PART 3, excerpt)
  family A (...): 15
    NOTWIN+CAPPED                                 ladder=RESHAPE    law=AUTHOR_SUCCESSOR
  family B (...): 15
    BUILT+AMB+UNREAD+CAPPED                       ladder=ADD_STATE  law=RAISE_BUDGET
  exceptions outside A/B: []
```
Family B is the only place in 256 where AMB is set and the ruling is not ADD_STATE. It needs UNREAD together with BUILT+AMB, which the body cannot construct today (F5).

### F4. Every ruling the docstring, tests, loop.py comments and CHANGELOG state as intended agrees with the law: 9/9.
```
(PART 7)
  BUILT+AMB          intended ADD_STATE      law ADD_STATE      OK
  BUILT+CAPPED       intended RAISE_BUDGET   law RAISE_BUDGET   OK
  BUILT+AMB+CAPPED   intended ADD_STATE      law ADD_STATE      OK
  CAPPED+REFUTED     intended RAISE_BUDGET   law RAISE_BUDGET   OK
  ... 9/9 intended rulings match the law
$ nice -n 15 ./timeout.sh 300 .venv/bin/fluidfix selfcheck
engine law fingerprint (sha256 48bf50bff36a2cc9, 1555 chars): verbatim
engine law rulings the guard depends on:      5/5
```
The docstring never states a precedence explicitly; it states single-bit rulings plus BUILT+AMB. The precedence it implies (refuse/escalate over ship; budget over harvest) is what the formula does.

### F5. The body constructs 10 of 256 bytes; precedence is exercised on exactly four multi-bit bytes, all on the ladder, none in the exception families.
From the six call sites: loop.py:217 `situation(BUILT=True, AMB=..., CAPPED=capped)`; loop.py:391 `HIDDEN`; guard.py:491 `UNREAD`; guard.py:539 `situation(CAPPED=capped0, REFUTED=acts0)`; guard.py:612/618 `REFUTED`.
```
(PART 6)
  distinct constructible bytes: 10/256
  multi-bit constructible bytes (precedence actually exercised):
    ['BUILT+AMB', 'BUILT+CAPPED', 'BUILT+AMB+CAPPED', 'CAPPED+REFUTED']
```

### F6. CAPPED is measured by the guard but not delivered to the BUILT byte: a green found under a truncated packet ships as `BUILT -> SHIP`. Measured: a compensating repair shipped, real defect left in place.
guard.py:508 sets `capped0 = capped0 or packet.truncated`, then guard.py:519 returns `repaired` on the first-pass result; `repair()` (loop.py:163-166) has no parameter for packet truncation, so `_rule()` at loop.py:217 can only carry deadline-CAPPED (`_rule(capped=True)` at 272/291), never packet-CAPPED. The law's precedence CAPPED > BUILT (F2) is therefore unreachable for the packet-line cap the docstring names as CAPPED's first example.
```
$ nice -n 15 ./timeout.sh 300 .venv/bin/python packet_capped_fixture.py
fillers=800 truncated=True sampled=110 compensator@5 in sample=True bug@809 in sample=False
law on the byte the guard HOLDS  BUILT+CAPPED -> RAISE_BUDGET
law on the byte loop.py:217 ASKS BUILT        -> SHIP
guard_once status = repaired
  suite_runs   = 3
  old_line     = '    return grade(v - 0, limit)'
  new_line     = '    return grade(v - -1, limit)'
  reason       = engine law: BUILT -> SHIP
real bug still there = True   (line 809: '    if v > limit:')
compensator shipped  = True   (line 5: '    return grade(v - -1, limit)')
suite green now      = True
```
Counterfactual with full sight (what the RAISE_BUDGET lane's depth-first escalation delivers):
```
$ nice -n 15 ./timeout.sh 300 .venv/bin/python packet_capped_counterfactual.py
full packet: truncated=False lines=807
repaired   = False
ambiguous  = True
suite_runs = 4
greens     = ['    return grade(v - -1, limit)', '    if v >= limit:']
reason     = AMBIGUOUS: 2 candidates at 2 different lines (5, 809) ... (engine law: BUILT+AMB -> ADD_STATE, never guess)
tree untouched = True
```
The fixture is contrived (`v - 0`), 1 run each; it is an existence proof, not a rate. Rate on real repos: unmeasured.

### F7. The fusion-integrity test audits none of loop.py's four multi-bit citations.
`test_every_cited_ruling_in_the_source_is_a_real_ruling` matches `-> ([A-Z_]+)`; loop.py cites `-> {ruling}` (f-string), so the four precedence-bearing citations are unaudited. They cannot print a wrong ACT (the placeholder is the real ruling), but the BITS they name are free text: loop.py:237 says `BUILT+AMB` when the byte asked may be BUILT+AMB+CAPPED (same ruling today, F4).
```
(PART 8, excerpt)
  guard.py:525  'BUILT+AMB -> ADD_STATE'     AUDITED
  loop.py:237   'BUILT+AMB -> {ruling}'      NOT audited (f-string placeholder)
  loop.py:242   'BUILT+CAPPED -> {ruling}'   NOT audited (f-string placeholder)
```

## 4. Lanes
Reached by my work (arithmetic): all 256 bytes, all 8 acts.
Reached by the body today (F5): SHIP (BUILT), ADD_STATE (BUILT+AMB, BUILT+AMB+CAPPED), ADD_MATERIAL (UNREAD), CHANGE_GRANULARITY (HIDDEN), RAISE_BUDGET (BUILT+CAPPED via deadline only; CAPPED; CAPPED+REFUTED), HARVEST_COUNTEREXAMPLE (REFUTED), plus SHIP on the empty byte at guard.py:539 (used only as "not RAISE_BUDGET"; nothing is shipped there).
Never reached by the body: RESHAPE (needs NOTWIN, unmeasured); AUTHOR_SUCCESSOR (family A: NOTWIN plus a high bit, unmeasured); family B RAISE_BUDGET-over-AMB (needs UNREAD folded into the BUILT byte; UNREAD is measured only before the search at guard.py:491 and never passed to `_rule`); every multi-bit byte containing HIDDEN (loop.py:391 asks HIDDEN alone, so HIDDEN>CAPPED and AMB>HIDDEN precedence are never consulted); BUILT+REFUTED, BUILT+UNREAD; BUILT+packet-CAPPED (F6: measured, not delivered).
Precedence that the body consults today reduces to three relations: AMB > BUILT, CAPPED(deadline) > BUILT, CAPPED > REFUTED.

## 5. Potential
- Delivering packet-CAPPED into the loop.py:217 byte (an observation channel, e.g. a `capped` argument to `repair()` set from `packet.truncated`): on the fixture it converts one wrong SHIP into RAISE_BUDGET -> full sight -> BUILT+AMB -> ADD_STATE refusal (F6, 3 vs 4 suite runs). Cost: any green found under a truncated packet would escalate before shipping — number of such greens on real repos: unmeasured. Whether the Unity ProjectOnPlane incident (CHANGELOG 2026-09-04) had a truncated packet: unmeasured.
- Family B (BUILT+AMB+UNREAD+high bit -> RAISE_BUDGET) and family A (-> AUTHOR_SUCCESSOR): worth: unmeasured; both need bits the body never sets together (UNREAD in-search; NOTWIN at all). Reachable only with an in-search UNREAD observation or a NOTWIN measurement.
- HIDDEN precedence (HIDDEN over CAPPED/REFUTED, AMB over HIDDEN): today HIDDEN is actuated per candidate as "not green", which is equivalent to the multi-bit rulings for every byte the body could form there (AMB+HIDDEN -> ADD_STATE would need the flaky green to count as green, which the body already refuses). Worth of asking the multi-bit byte: unmeasured, expected nil by the ladder.

## 6. Defects
One found, classified **observation**, with evidence in F6. The bit CAPPED is measured (guard.py:508, `packet.truncated=True`) and held by the guard, but the byte asked at loop.py:217 is `BUILT` alone because `repair()` has no channel for it. The law ruled SHIP on the byte it was given (correct for that byte); on the byte the body actually held, BUILT+CAPPED, it rules RAISE_BUDGET, and the escalation lane that ruling actuates (guard.py:539-611, depth-first full sight) produced the honest AMB refusal in the counterfactual. Fix belongs to observation delivery, not to the ruling and not to a new branch.
Wording (minor, no wrong outcome today): loop.py:237 names `BUILT+AMB` for a byte that can be BUILT+AMB+CAPPED (same ruling), and the four loop.py citations sit outside the fusion-integrity audit (F7).
Ruling defects: none found (F1, F4).

## 7. Verdict
The law's precedence is exactly "lowest set bit among AMB<UNREAD<NOTWIN<HIDDEN<CAPPED<REFUTED wins, BUILT/SELF never win" on 226/256 bytes plus two 15-byte borrow families (NOTWIN+high -> AUTHOR_SUCCESSOR; BUILT+AMB+UNREAD+high -> RAISE_BUDGET); it matches every documented intent (9/9) and the body exercises only four multi-bit bytes, all on the ladder — but packet-CAPPED is measured at guard.py:508 and never delivered to the BUILT byte, and one built fixture measured that gap shipping a compensating repair (`BUILT -> SHIP`) where the held byte BUILT+CAPPED rules RAISE_BUDGET and full sight refuses as BUILT+AMB.
