# 08-engine-monotonicity

## 1. Target

Property test over all bit-flip pairs of the engine law: can adding one evidence bit ever move a ruling from a refusal to SHIP? Enumerate every such pair and judge whether each is intended.

## 2. Method

Read: `src/fluidfix/engine.py` (the law, `situation()`, `decide()`), `src/fluidfix/loop.py` lines 193-260 and 290-410 (the ruling site `_rule` at line 217 and the HIDDEN block at 357-392), `src/fluidfix/guard.py` lines 480-625 (the four `decide()` call sites: 491, 539, 612, 618), `src/fluidfix/cli.py` 440-520 (selfcheck), `tests/test_engine_fusion.py`, `tests/test_law_never_ruled_wrong.py` 17-53, `tests/test_c_adapter.py` 355-400, `CHANGELOG.md` 20-80.

Wrote and ran (all inside this directory; `timeout(1)` is not installed on this macOS, so the 300 s cap is `perl -e 'alarm 300; exec @ARGV'`, which is equivalent):

- `monotonicity.py` — derives a closed form of the law, checks it against `decide()` on all 256 bytes and all 4 job values, enumerates all 1024 single-bit-add pairs and all 5733 proper supersets of every refusing byte, and prints the body-reachable family at `loop.py:217`. Output: `monotonicity.out`.
- `hidden_dropped.py` — 24-trial fixture (`fixtures/hidden_dropped/run_NN`) measuring whether a HIDDEN observation taken mid-search reaches the byte the SHIP ruling is made on. Output: `hidden_dropped.out`.

Commands:
```
cd research/laws-2026-09-07/08-engine-monotonicity
nice -n 15 perl -e 'alarm 300; exec @ARGV' /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python monotonicity.py
nice -n 15 perl -e 'alarm 300; exec @ARGV' /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python hidden_dropped.py
```
Real repos were not used (the target does not call for them). No file outside this directory was written; no git state was changed.

## 3. Findings

### F1. The law has a closed form; SHIP is ruled exactly when none of AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED is set.

Derivation from `act = (4 & ntzb(x - 7)) + ntzb(x + (x & 128))`, where `ntzb(v)` is the index of the lowest set bit of `v & 254` (0 when none):

- Second term: `x + (x & 128)` carries bit 7 (SELF) out of the byte, so it is the index of the lowest set bit among bits 1..6, i.e. AMB=1, UNREAD=2, NOTWIN=3, HIDDEN=4, CAPPED=5, REFUTED=6 — the same-index act — and 0 when none of them is set. BUILT (bit 0) and SELF (bit 7) never enter this term.
- First term: `4 & ntzb(x - 7)` is 4 iff bits 1..3 of `x - 7` are clear and some bit 4..7 is set, i.e. iff `(x & 15) in {7, 8}` and `(x & 240) != 0`; otherwise 0.

So `act = 4*[(x&15) in {7,8} and (x&240) != 0] + lowest_set_index(x & 0x7E)`, mod 8. SHIP (index 0) iff `(x & 0x7E) == 0`.

Script check (`monotonicity.out`):
```
closed-form vs decide(): 256/256 agree; mismatches=[]
situations ruling SHIP: 4/256 -> (empty), BUILT, SELF, BUILT+SELF
act histogram over 256: SHIP=4, ADD_STATE=113, ADD_MATERIAL=64, RESHAPE=17, CHANGE_GRANULARITY=16, RAISE_BUDGET=23, HARVEST_COUNTEREXAMPLE=4, AUTHOR_SUCCESSOR=15
SHIP <=> (x & 0x7E)==0, i.e. none of AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED set: holds on all 256
```

### F2. Adding one bit never moves a refusal to SHIP: 0 of 1024 pairs. Adding any set of bits never does either: 0 of 5733.

This follows from F1 (a set bit in `x & 0x7E` cannot be cleared by OR-ing more bits in) and was enumerated rather than only argued:
```
single-bit-add pairs (1024): SHIP->SHIP=4, SHIP->refusal=24, refusal->same refusal=700, refusal->different refusal=296
refusal->SHIP pairs (THE QUESTION):
  NONE (0 of 1024)
superset closure from every refusal (5733 proper supersets): 0 reach SHIP
```
The enumeration the target asks for is therefore empty. The property the project states for the ranking and SIGHT laws ("more evidence is never worse", `cli.py` selfcheck R3/mono) holds for the engine law in the form that matters for wrong repairs: more evidence can only withdraw SHIP, never grant it.

### F3. The result does not depend on the job bits.

`situation()` ORs in `2 << 8` (DEBUG job). Feeding the raw 10-bit word to `decide()` for all four job values:
```
job-invariance (bits 8-9 = 0..3) vs job=2: 1024/1024 agree; differ=[]
```

### F4. The full SHIP boundary, with an intent judgment for each pair.

SHIP -> SHIP (4 pairs): adding the bit leaves SHIP in place.
```
  (empty) +BUILT -> BUILT        intended: the documented BUILT -> SHIP
  (empty) +SELF  -> SELF         intent not stated anywhere in fluidfix (see F5)
  BUILT +SELF    -> BUILT+SELF   intent not stated (see F5)
  SELF +BUILT    -> BUILT+SELF   intent not stated (see F5)
```
SHIP -> refusal (24 pairs): from each of the four SHIP bytes, adding any one of the six bits 1..6 withdraws SHIP. From BUILT, five of the six land on the documented ruling (`engine.py` docstring, `test_rulings_fluidfix_depends_on`, `cli.py` selfcheck):
```
  BUILT +AMB -> ADD_STATE                  documented, pinned
  BUILT +UNREAD -> ADD_MATERIAL            documented (as UNREAD alone), pinned
  BUILT +HIDDEN -> CHANGE_GRANULARITY      documented in loop.py:357-392 and test_c_adapter.py:362-379
  BUILT +CAPPED -> RAISE_BUDGET            documented, pinned, and the fused deadline path (loop.py:193-200)
  BUILT +REFUTED -> HARVEST_COUNTEREXAMPLE documented (as REFUTED alone), pinned
  BUILT +NOTWIN -> RESHAPE                 not documented in fluidfix; same-index mapping; NOTWIN is never set
```
The other 18 (from `(empty)`, `SELF`, `BUILT+SELF`) are the same six acts, with one exception: `SELF +NOTWIN -> AUTHOR_SUCCESSOR` (first term fires: low nibble 8, bit 7 set). All 24 are in the conservative direction. Read backwards, these are the only 24 refusals one bit-removal away from SHIP (full list in `monotonicity.out`); every one of them is "the single blocking bit went away", which is the intended meaning of each bit.

Judgment: every pair on the SHIP boundary is either the documented ruling or an undocumented-but-consistent same-index refusal; none is a refusal-to-SHIP move; the only pairs whose intent fluidfix does not state are the three SELF pairs.

### F5. SELF is invisible to the SHIP/refusal boundary; the empty byte rules SHIP; the docstring is silent on both.

From F1: bit 7 is carried out of the second term and only enters the first term (with NOTWIN alone in the low nibble, or with BUILT+AMB+UNREAD). Consequences, all measured in `monotonicity.out`:
- `SELF` alone and `BUILT+SELF` rule SHIP; adding SELF to any byte changes the act in only 2 of the 128 possible additions (`pairs whose act changes, by bit added: ... SELF=2`), both refusal-to-refusal (`BUILT+AMB+UNREAD +SELF -> RAISE_BUDGET`, `NOTWIN +SELF -> AUTHOR_SUCCESSOR`).
- `(empty)` rules SHIP. The body does ask the law the empty byte: `guard.py:539` evaluates `decide(situation(CAPPED=capped0, REFUTED=acts0))` and both are `False` when no packet was truncated, no candidate set was tried and the file list was not cut (`guard.py:485,508,519,538`). The comparison there is `== "RAISE_BUDGET"` only, so the SHIP ruling is never acted on. Outcome unaffected; noted because the docstring specifies nothing for the empty byte or for SELF, and `engine.py` says only that SELF is "not yet measured".

`grep -n "NOTWIN\|SELF" src/fluidfix/*.py | grep -v engine.py` finds only comment/identifier text (`guard.py:229` "ITSELF", `cli.py:570` "SELFCHECK", `loop.py:367` a comment): neither bit is ever set by the body.

### F6. The 296 refusal-to-different-refusal pairs split into two families; neither touches SHIP and neither is constructible by the body today.

```
  [lower-precedence bit added] 169 pairs      e.g. CAPPED [RAISE_BUDGET] +AMB -> [ADD_STATE]
  [first-term(+4) toggled] 127 pairs          e.g. BUILT+AMB+UNREAD [ADD_STATE] +HIDDEN -> [RAISE_BUDGET]
                                                   NOTWIN [RESHAPE] +CAPPED -> [AUTHOR_SUCCESSOR]
                                                   AMB+UNREAD+HIDDEN [ADD_STATE] +BUILT -> [RAISE_BUDGET]
```
The 169 are the precedence order AMB > UNREAD > NOTWIN > HIDDEN > CAPPED > REFUTED (lowest set bit wins), which is target 07's subject. The 127 all require either NOTWIN with no BUILT/AMB/UNREAD, or BUILT+AMB+UNREAD together, plus a bit in 4..7. The body presents UNREAD only by itself (`guard.py:491`) and never sets NOTWIN or SELF (F5), so every one of the 127 is unreachable today; the observation that would make the BUILT+AMB+UNREAD family reachable is carrying UNREAD into the byte at `loop.py:217`, which the body does not do.

### F7. The one body path where a measured bit is absent from the shipping byte: HIDDEN. Measured 9 of 24 searches; all shipped the correct line.

`loop.py:217` rules on `BUILT=True, AMB=..., CAPPED=...` only. `loop.py:357-392` measures HIDDEN per candidate (green once, red on re-check), calls `decide(situation(HIDDEN=True))` at 391, but the ruling reaches only the `why` string and the candidate is set `ok = False` (392); HIDDEN is not carried into the final byte. The law's rulings if it were (`monotonicity.out`):
```
body-reachable family at loop.py:217 (BUILT always true; AMB, CAPPED measured):
  BUILT                  -> SHIP
  BUILT+CAPPED           -> RAISE_BUDGET
  BUILT+AMB              -> ADD_STATE
  BUILT+AMB+CAPPED       -> ADD_STATE
what the same site would rule if HIDDEN were carried in the byte:
  BUILT+HIDDEN                  -> CHANGE_GRANULARITY
  BUILT+HIDDEN+CAPPED           -> CHANGE_GRANULARITY
  BUILT+AMB+HIDDEN              -> ADD_STATE
  BUILT+AMB+HIDDEN+CAPPED       -> ADD_STATE
```
Fixture (`hidden_dropped.py`): one candidate set `[K = 1, K = 2]`, `K = 1` always green, `K = 2` green with p = 0.5 per run, `FLUIDFIX_CONFIRM` unset (default 1). Output (`hidden_dropped.out`):
```
tally (status, HIDDEN observed in tried_log?, shipped line):
    2  ('refused', 'no HIDDEN', '-')
    9  ('repaired', 'HIDDEN observed', 'K = 1')
   13  ('repaired', 'no HIDDEN', 'K = 1')
one HIDDEN `why` as logged (the ruling reaches only this string):
  green on one run, RED on re-check — the suite does not hold still here, so a single run cannot judge this candidate (engine law: HIDDEN -> CHANGE_GRANULARITY). last failure: FAILED test_mod.py::test_f - AssertionError: flake
```
In 9 of 24 searches the body observed HIDDEN on one candidate and then ruled SHIP on a byte reading BUILT alone (`reason='engine law: BUILT -> SHIP'`). All 22 ships were `K = 1`, the correct line; the 2 refusals were AMB (both candidates green twice). No wrong repair occurred in 24 trials.

## 4. Lanes

By the law (exhaustive, F1): all 8 acts reached; their sizes are in the histogram in F1.

By the body, at the shipping site `loop.py:217`: SHIP, ADD_STATE, RAISE_BUDGET reached (the four-byte family in F7); CHANGE_GRANULARITY reached only as a per-candidate message at `loop.py:391` (9 of 24 trials in F7), never as the byte's ruling.

Never reached by the body, and why:
- ADD_MATERIAL: reachable only at `guard.py:491` (no candidate files and no pytest-cov); not exercised here.
- HARVEST_COUNTEREXAMPLE: reachable at `guard.py:612/618`; not exercised here.
- RESHAPE: needs NOTWIN, never set (F5).
- AUTHOR_SUCCESSOR: needs NOTWIN alone in the low nibble plus one of HIDDEN/CAPPED/REFUTED/SELF; NOTWIN never set.
- The RAISE_BUDGET-via-first-term family (BUILT+AMB+UNREAD+bit 4..7): needs UNREAD in the same byte as BUILT; the body never assembles that (F6).

## 5. Potential

- The monotonicity guarantee (F2) is worth exactly this: any newly measured bit among AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED, wired into the byte at `loop.py:217`, can only withdraw SHIP, never grant it. Wiring NOTWIN, UNREAD or HIDDEN into that byte is therefore safe with respect to wrong repairs by construction; what it costs in withheld correct repairs is the only question.
- SELF is the exception (F5): measuring SELF would not act as a brake on shipping at all (0 of 4 SHIP bytes change when SELF is added). If SELF is meant to be a refusal condition, the law as authored cannot express it on its own; that is for target 09 to design. Unmeasured: what SELF would be worth, because no observation exists.
- Carrying HIDDEN per-search into the byte at `loop.py:217` (F7): on this fixture it would have withheld 9 of 22 correct repairs (41%) and prevented 0 wrong ones. Unmeasured: the same number on a suite where the surviving green is itself the flaky candidate (target 05 measures false-accept under `FLUIDFIX_CONFIRM`).
- The 127 first-term pairs (F6) are worth nothing today: unreachable. They become reachable only if UNREAD or NOTWIN is carried into the shipping byte, and their rulings (RAISE_BUDGET, AUTHOR_SUCCESSOR) would then need actuation that does not exist at `loop.py:217` (which actuates only SHIP and the two refusal messages).

## 6. Defects

None found in the ruling: no byte and no bit-addition lets the law grant SHIP on more evidence (F2), and the 24 withdrawals of SHIP are each the intended meaning of the added bit (F4).

Observation-scope note, not classified as a defect: F7 shows the body measures HIDDEN per candidate and drops it from the shipping byte. This is consistent with the project's own definition (`tests/test_law_never_ruled_wrong.py:41-44` and `test_c_adapter.py:373-379`: BUILT means "this candidate passed its own check"; HIDDEN means that candidate's fine records disagreed), so the byte `BUILT` for the surviving, re-confirmed candidate is a correct measurement under that definition. It would be an observation defect only under a per-search reading of HIDDEN ("the suite does not hold still here", which is the wording of the body's own message at `loop.py:393-396`). The wording and the measurement scope disagree; the outcome did not (22 of 22 ships correct). Unmeasured: whether the per-candidate scope ever ships a wrong line.

Wording note: `guard.py:539` asks the law about the empty byte and receives SHIP (F5); nothing is shipped because only `== "RAISE_BUDGET"` is tested. Not a wrong outcome.

## 7. Verdict

Exhaustively, no single-bit addition (0 of 1024) and no multi-bit addition (0 of 5733) moves an engine-law refusal to SHIP, because SHIP is ruled exactly when none of AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED is set; SELF alone never withdraws SHIP, and the body's only measured-but-uncarried bit (HIDDEN, 9 of 24 searches) shipped the correct line every time.
