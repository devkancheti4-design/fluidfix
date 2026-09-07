# 01-engine-exhaustive — REPORT
(Relayed by the coordinator: the agent's own write of this file was blocked by a
harness rule. The scripts and .out files in this directory are the agent's own
and are rerunnable.)

## 1. Target
Re-derive all 256 engine-law rulings from the formula; compare to the docstring
spec and to what tests/test_engine_fusion.py pins; list every input no test pins.

## 2. Method
All work inside this directory. Nothing outside written; no git state changed;
every run nice -n 15 + ./t300.sh (a `timeout 300` equivalent: this macOS lacks
coreutils timeout, so it prefers gtimeout, else perl alarm(300) surviving exec).
Read: src/fluidfix/engine.py; tests/test_engine_fusion.py (all 242 lines);
tests/test_law_never_ruled_wrong.py; call sites loop.py:217, loop.py:391,
guard.py:491, guard.py:539, guard.py:612, guard.py:618, guard.py:57-110
(summary), guard.py:712-725 (write_refusal), cli.py:474; tests/test_c_adapter.py:368-385.
Ran: exhaustive.py -> exhaustive.out, table.md (three-way re-derivation:
docstring formula / raw vendored LAW / decide(); job-invariance; census; pin
extraction; unpinned list); structure.py -> structure.out (closed form, +4 term);
spec_audit.py -> spec_audit.out (per-bit table vs law; the "never set" claim vs a
balanced-paren parse of every decide(situation(...)) in src/fluidfix/*.py;
per-act entry conditions; cost of unmeasured bits); byte0_actuation.py ->
byte0_actuation.out (fixture0/, the full ruling->message chain on byte 0);
byte_log.py, byte_log_B.py -> byte_log_A.out, byte_log_B.out (every byte the body
hands the law on live fixtures, decide patched in-process only);
pytest test_engine_fusion.py test_law_never_ruled_wrong.py -> pytest_engine.out;
fluidfix selfcheck -> selfcheck.out.
exhaustive.py and structure.py were re-run this session; output byte-identical to
the interrupted run (diff clean; exhaustive.rerun.out, structure.rerun.out).

## 3. Findings

F1. All 256 rulings re-derive identically from three independent sources; the law
is verbatim.
    LAW length=1555 sha256[:16]=48bf50bff36a2cc9  (matches the claim)
    formula (docstring) vs raw LAW, 256 inputs: 256/256 agree
    job-invariance (bits 8-9 in 0..3), 256 inputs: 256/256 invariant
    raw LAW values seen: [0..7]; inputs where raw >= 8 (ACTS[...%8] wraps): 0
The four job values change nothing on any of the 256, and the % 8 in decide() is
dead. Per-input table in table.md.

F2. Closed form: lowest blocking bit, plus 4 on two families. (structure.out)
    closed form vs decide(), 256 inputs: 256/256 agree
    +4 family A (x%16==7, x>=23: BUILT+AMB+UNREAD set, NOTWIN clear, >=1 of
       HIDDEN/CAPPED/REFUTED/SELF): 15 inputs, all rule RAISE_BUDGET
    +4 family B (x%16==8, x>=24: NOTWIN set, BUILT/AMB/UNREAD clear, >=1 of
       HIDDEN/CAPPED/REFUTED/SELF): 15 inputs, all rule AUTHOR_SUCCESSOR
    one added bit turning a non-SHIP ruling into SHIP: 0 pairs []
    SHIP inputs: [0, 1, 128, 129] = ['(none)','BUILT','SELF','BUILT+SELF']
Ruling index = lowbit(bits 1..6) + 4*[x mod 16 in {7,8} and x >= 23], checked on
all 256. Evidence is one-directional: 0 of 1,024 bit-flips move a refusal to SHIP.
Census: SHIP 4, ADD_STATE 113, ADD_MATERIAL 64, RESHAPE 17,
CHANGE_GRANULARITY 16, RAISE_BUDGET 23, HARVEST_COUNTEREXAMPLE 4,
AUTHOR_SUCCESSOR 15.

F3. The per-bit table holds on 7 of 8 bits; SELF alone rules SHIP.
    bit 7 SELF   table says AUTHOR_SUCCESSOR   law rules SHIP   DEVIATES
    AUTHOR_SUCCESSOR is instead reached by 15 bytes, all with NOTWIN set: True
All seven named docstring spec lines (BUILT, BUILT+AMB, AMB, UNREAD, CAPPED,
REFUTED, HIDDEN) hold — exhaustive.out lines 24-31, all OK.

F4. engine.py:27-28's limitation claim is stale for HIDDEN. It says verbatim:
"NOTWIN, HIDDEN and SELF are not yet measured by fluidfix and are never set
(documented limitation, not an omission by accident)."
    NOTWIN   never passed to decide() anywhere in src/
    HIDDEN   SET at loop.py:391 (HIDDEN=True)
    SELF     never passed to decide() anywhere in src/
    bits the docstring calls 'never set' that the body DOES set: ['HIDDEN']
HIDDEN is measured (loop.py:357 gates on _confirm_runs(), default 1), actuated,
and pinned (tests/test_c_adapter.py:378). test_law_never_ruled_wrong.py:43
records this lane as a CLOSED incident.

F5. Only NOTWIN costs anything.
    NOTWIN is REQUIRED by acts ['RESHAPE','AUTHOR_SUCCESSOR'] (32 of 256 bytes)
    SELF   is REQUIRED by acts [] (0 of 256 bytes)
    acts unreachable no matter how those bits combine: ['RESHAPE','AUTHOR_SUCCESSOR']
Sharper than "SELF is not measured": adding SELF alone unlocks ZERO acts.

F6. test_engine_fusion.py pins 6 of 256 by direct assertion; 8 pinned anywhere;
248 unpinned.
    x=1 BUILT / x=3 BUILT+AMB / x=4 UNREAD / x=32 CAPPED / x=64 REFUTED /
    x=96 CAPPED+REFUTED
    bytes pinned anywhere (tests + INCIDENTS + selfcheck + src citations): 8
    pins that disagree with the law: 0
    inputs no test pins: 248/256
    unpinned AND body-constructible: [0, 33, 35] ->
        (none)=SHIP, BUILT+CAPPED=RAISE_BUDGET, BUILT+AMB+CAPPED=ADD_STATE
Byte 33 is reached live (byte_log_B.out): t=13.8 x=33 BUILT+CAPPED -> RAISE_BUDGET.

F7. The body hands the law byte 0 on a real refusal, the law rules SHIP, and the
ruling is discarded. (byte0_actuation.out; fixture `def f(x): return x` vs
`f('a')=='A'` — a line the observer reports nothing for)
    1. bytes handed to the engine law, in order:  x=0 (none) -> law rules SHIP
    2. guard status='refused'  hint=''  attempts=0
    3. user-visible summary():
       REFUSED: fault is outside the taught vocabulary (candidate files tried:
       mod.py). teach it once: docs/TEACHING.md
    5. any ACT NAME from the law present in the user-visible text? NONE
    6. tree untouched: True
Call site guard.py:539:
  if escalate and decide(situation(CAPPED=capped0, REFUTED=acts0)) == "RAISE_BUDGET":
both false -> byte 0 -> SHIP -> equality False -> falls through to a hardcoded
else in summary() (guard.py:101-104).

F8. Suite and selfcheck pass. 16 passed in 266.11s. selfcheck.out: engine law
fingerprint (sha256 48bf50bff36a2cc9, 1555 chars): verbatim; engine law rulings
the guard depends on: 5/5; SELFCHECK PASS — 6 laws re-derived. NOTE the shipped
selfcheck re-derives 5 single-bit engine rulings, not 256.

## 4. Lanes
The derivation reached all 256 inputs and all 8 rulings. Reached with a LIVE body:

| Ruling | Live here? | Evidence / why not |
|---|---|---|
| SHIP | yes, byte 0 | byte0_actuation.out — as a DISCARDED ruling (D1). SHIP-as-repair (byte 1) only in the repo's own test. |
| ADD_STATE | no | byte 3 constructible at loop.py:217, pinned; AMB fixtures are target 04. |
| ADD_MATERIAL | no | byte 4 needs pytest-cov absent AND no candidates (guard.py:491); not constructible without altering the interpreter. |
| RESHAPE | never | requires NOTWIN in all 17 of its bytes; NOTWIN never passed to decide(). Structurally unreachable. |
| CHANGE_GRANULARITY | no | byte 16 reachable (loop.py:391) but needs a flaky suite — target 05. |
| RAISE_BUDGET | yes, byte 33 | byte_log_B.out t=13.8s. |
| HARVEST_COUNTEREXAMPLE | yes, byte 64 | byte_log_B.out t=14.8s, twice. |
| AUTHOR_SUCCESSOR | never | requires NOTWIN in all 15 of its bytes. Measuring SELF would not change this. |

The 248 inputs are unpinned because the body constructs only 10 distinct bytes
across six call sites ([0,1,3,4,16,32,33,35,64,96]) and tests pin 8. The
observation that would make RESHAPE/AUTHOR_SUCCESSOR reachable is a NOTWIN
measurement — "the material exists but not in the form needed". Whether that is
the right meaning of NOTWIN for fluidfix is UNMEASURED — no such fixture built.

## 5. Potential
- NOTWIN is the highest-leverage missing observation. Measured: 32/256 bytes
  (12.5%) and 2/8 acts unreachable, NOTWIN required by every byte of both. SELF
  unlocks 0 acts, measured. Worth in REPAIRS: UNMEASURED.
- Test coverage of the law is 8/256 (3.1%), measured. Body-constructible but
  unpinned: 0, 33, 35. Byte 33 is reached live with no test pinning it. Three
  assertions would close the gap for everything the body can build; the other 245
  are unreachable today, so pinning them documents rather than protects.
- The % 8 in decide() is dead, measured: raw values are exactly 0..7. Worth
  noting so nobody reads it as a working safety net.
- An UNREAD measurement for an empty vocabulary read (D1) converts one hardcoded
  refusal message into a ruling. Frequency on real repos: UNMEASURED.

## 6. Defects

D1 — OBSERVATION. The "vocabulary read nothing" situation is packed as byte 0,
whose ruling is SHIP. The law ruled SHIP on byte 0 at guard.py:539. That ruling
is correct for byte 0 — with no blocker observed the closed form returns index 0.
The defect is upstream: a candidate file was found and searched, the taught
vocabulary produced ZERO acts (attempts=0, REFUTED=acts0=False), and nothing was
truncated (CAPPED=capped0=False). That is the docstring's own definition of
UNREAD — "a needed tool reads nothing" — and the body sets UNREAD for only one
instance of it (missing pytest-cov with no candidates, guard.py:491). A real
blocker was measured as no blocker. NOT a wrong repair: tree untouched, message
accurate. ADD_MATERIAL — UNREAD's ruling — is exactly what the hardcoded message
already advises, which is why this is an observation gap, not a ruling
disagreement. Fix is a measurement, not a branch: set UNREAD=True at guard.py:539
when every searched candidate yielded zero acts, and let the existing
ADD_MATERIAL lane speak. Not implemented (src/ outside write scope).

D2 — WORDING. engine.py:27-28 says HIDDEN is never set; the body sets it. The
docstring is the module's specification, so it understates the implementation —
CHANGE_GRANULARITY is live and the docstring tells a reader it is dead. NOTWIN
and SELF are correctly described. No behavioural consequence.

D3 — WORDING (minor). The BITS[i] <-> ACTS[i] table implies SELF ->
AUTHOR_SUCCESSOR. It holds on 7/8 bits. AUTHOR_SUCCESSOR is gated on NOTWIN and
situation(SELF=True) rules SHIP. Presentation, not ruling.

Not defects: the dead % 8; refusals on bytes 3 and 35; no pin anywhere disagrees
with the law. NO DEFECT FOUND IN ANY RULING: three independent derivations agree
on all 256, evidence is monotone (0 of 1,024 bit-flips turn a refusal into SHIP),
and the law matches its published fingerprint byte for byte.

## 7. Verdict
All 256 engine-law rulings re-derive identically from the docstring formula, the
vendored 1,555-character string and decide(), and no pin in the project disagrees
with any of them; the defects are not in the rulings — one mismeasured
observation (byte 0 handed at guard.py:539 for a situation that is UNREAD) and
two stale specification sentences — while only 8 of 256 inputs are pinned and the
two acts that never fire, RESHAPE and AUTHOR_SUCCESSOR, are both gated on the
single unmeasured bit NOTWIN rather than on SELF.
