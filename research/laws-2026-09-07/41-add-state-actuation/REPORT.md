# 41-add-state-actuation — generating a pinning test from two green candidates
(Relayed by the coordinator: the agent's own write was blocked by a harness rule.
All scripts, fixtures and JSON results are on disk beside this file and rerunnable.)

## 1. Target
ADD_STATE = "ask for one pinning test". Prototype generating a differential test
from two green candidates on an AMB fixture, outside src/; does it disambiguate?

## 2. Method
Read engine.py, loop.py (_rule 193-243; search 264-431), guard.py:525, cli.py:472.
Corpus: the 12 ambiguous fixtures from the red team's 07-compensating-one-site
fixtures.py, copied unmodified (their directory was not written to).
Files written here: tmo (perl-alarm timeout wrapper; no coreutils timeout on this
host), difftest.py (THE PROTOTYPE), run_pin.py (measurement over the 12 fixtures),
limits.py (6 hand-built shapes probing failure), l4_repeat.py / l4_sweep.py
(flaky-witness rate vs the stability filter), runs/ and limits_runs/ (throwaway
repos with the pin tests actually emitted).
Every run nice -n 15 ./tmo <s> ..., one at a time. No src/ edit, no git state change.

THE GENERATION METHOD. Input is exactly what loop.py holds when it asks the law at
line 217: greens as (crepr, content, old_repr, at). NO GROUND TRUTH USED.
 1. Target function — every function some candidate edits, then the functions the
    repo's tests call most; first that separates wins.
 2. Seeds — argument tuples harvested as AST literals from the repo's own tests
    (the only in-domain input source fluidfix has).
 3. Pool — each seed mutated one argument at a time (ints +-1/+-2/0/negate/double,
    floats +-0.5/+-1.0, sequences reversed/swapped/dropped/elementwise +-1,
    strings), PLUS midpoints between the values the suite itself uses per
    position. Cap 400.
 4. Evaluate — each variant runs the pool in its own subprocess, each input
    REPEATS times under SIGALRM; inputs whose own runs disagree are !UNSTABLE,
    inputs that raise are skipped. ZERO SUITE RUNS.
 5. Witness — first input where the candidates' values differ.
 6. Emit a pytest file: the call, one COMMENTED assertion per candidate with that
    candidate's value. The user uncomments one. FLUIDFIX DOES NOT PICK.

## 3. Findings

F1 — ADD_STATE is wording only; the AMB OBSERVATION, not the ruling, is the defect.
    grep -rn "ADD_STATE" src/  -> engine.py:17,38 ; cli.py:472 ;
                                  loop.py:257 (comment) ; guard.py:525 (comment)
    grep -rn 'ruling ==' src/fluidfix/*.py -> loop.py:221: if ruling == "SHIP":
ADD_STATE is never compared, only interpolated into the refusal string at
loop.py:237. The refusal branches key off set_amb or len(sites)>1 and
result.ambiguous, NOT off the ruling. The law is correct on both bytes:
    BUILT=1 AMB=0 CAPPED=0 -> byte 513 (0x201) -> SHIP
    BUILT=1 AMB=1 CAPPED=0 -> byte 515 (0x203) -> ADD_STATE

F2 (HEADLINE) — the prototype separated 12 of 12 ambiguous fixtures, NO GROUND TRUTH.
    fixture                                    witness                sep  before   after
    A1_index_vs_strict  (pristine index)       alarm([3, 7], 3)      True  WRONG   CORRECT
    A2_index_vs_strict  (pristine strict)      alarm([3, 7], 3)      True  CORRECT CORRECT
    B1_threshold_vs_strict (literal)           surcharge(20.5)       True  WRONG   CORRECT
    B2_threshold_vs_strict (strict)            surcharge(20.5)       True  CORRECT CORRECT
    C1_slice_vs_strict  (slice)                over_budget([4,4], 7) True  WRONG   CORRECT
    C2_slice_vs_strict  (strict)               over_budget([4,4], 7) True  CORRECT CORRECT
    D1_minmax_vs_strict (max)                  passes(4, 8, 5)       True  WRONG   CORRECT
    D2_minmax_vs_strict (min_ge)               passes(4, 8, 5)       True  CORRECT CORRECT
    E1_index_vs_additive (index)               total([9, 5], 2)      True  CORRECT CORRECT
    E2_index_vs_additive (minus)               total([9, 5], 2)      True  WRONG   CORRECT
    F1_index_vs_reversal (index)               adjust([2, 7], 4)     True  CORRECT CORRECT
    F2_index_vs_reversal (reversed)            adjust([2, 7], 4)     True  WRONG   CORRECT
    ambiguous fixtures (>=2 greens): 12
    pinning test generated AND separates: 12/12
    correct program on disk BEFORE the pin:  6/12
    correct program on disk AFTER the pin:  12/12
"separates" is a GROUND-TRUTH-FREE check: pin the test to candidate i, run the
repo's suite with candidate j on the line, for every (i,j); it separates iff green
exactly when i == j. All 12 matrices came back [[True,False],[False,True]].
"after" is end to end: the pin is filled with the pristine answer — THE ONLY USE OF
GROUND TRUTH, standing in for the user answering — the defect is put back, and
unmodified `fluidfix repair` re-runs. All 12 then report exactly one green and
"ambiguous": false. after_suite_runs: [4]*12.
ON THE CORPUS THAT PRODUCED THE PROJECT'S WORST RECORDED OUTCOME, WRONG REPAIRS GO
6/12 -> 0/12.

F3 — the emitted artefact (generated, not hand-written):
    """Pinning test proposed by fluidfix.
    The engine law ruled BUILT+AMB -> ADD_STATE at gate.py:5:
    2 DIFFERENT programs all pass this suite, so the suite cannot say which one
    you meant. They disagree here:
        A:  return readings[1] >= limit     alarm([3, 7], 3) -> True
        B:  return readings[0] > limit      alarm([3, 7], 3) -> False
    """
    from gate import alarm
    def test_fluidfix_pin_alarm():
        # assert alarm([3, 7], 3) == True    # candidate A
        # assert alarm([3, 7], 3) == False   # candidate B

F4 — generation costs ZERO suite runs and 0.10 s.
    seconds: 0.10 | pool: 69 | suite runs used: 0 | python subprocesses: 2
    Pool sizes on the corpus: 21-75 inputs from 3-4 harvested seeds.

F5 — the same mechanism MEASURES the AMB bit, and correctly declines the spellings
case. loop.py:213-216 warns `units >= 10` and `units > 9` must NOT be called
ambiguous. Handed exactly that pair (both verified green):
    L1_spelling_only  expect=no-separate  separated=False  as_expected=True
    no stable, exception-free input of 21 separates the candidates
A WITNESS THEREFORE *IS* THE AMB BIT: present -> two programs -> AMB=1 ->
ADD_STATE; absent -> one program spelled twice -> AMB=0 -> SHIP. That is a
measurement of the bit the law asks for, not a proxy for where the greens came from.

F6 — the two-site compensating shape is separated by pinning the EDITED function.
L6 is the shape loop.py:208-212 was written for: `project` has a sign flip;
breaking `add` cancels it. Both green, at lines 5 and 9. Targeting entry point
`project` finds nothing (the two programs agree there by construction), so it falls
through to `add`:
    L6_two_site_compensating  separated=True  add([1,2],[1,2])
      targets tried: ['project', 'add']
      A: return add(v, [k, k])             -> [2, 4]
      B: return [a[0]-b[0], a[1]-b[1]]     -> [0, 0]

F7 — a 2-run stability filter emits FLAKY pins; 5 runs does not.
    REPEATS=2   witnesses emitted on a nondeterministic pair: 11/20
    REPEATS=3   ...                                            1/20
    REPEATS=5   ...                                            0/20
    REPEATS=10  ...                                            0/20
difftest.REPEATS is now 5. Same phenomenon loop.py:357-397 handles for the suite
via FLUIDFIX_CONFIRM / the HIDDEN lane; a pin generator needs its own copy of that
discipline.

F8 — WHERE IT FAILS.
    L1_spelling_only         expect=no-separate  separated=False  OK
    L2_distant_literal       expect=separate     separated=True   OK   fee(105.0)
    L3_c_source              expect=separate     separated=False  FAIL
    L4_nondeterministic      expect=no-separate  separated=False  OK
    L5_object_argument       expect=separate     separated=False  FAIL
    L6_two_site_compensating expect=separate     separated=True   OK
    cases: 6   generator did the right thing: 4
 - L3, C SOURCE — TOTAL FAILURE, AND THE IMPORTANT ONE. ast.parse raises, no target
   is found, targets_tried: [], message "non-Python source parses to nothing".
   BOX2D AND CGLM ARE C; THIS METHOD AS BUILT REACHES NONE OF IT.
 - L5, object arguments — RECOVERABLE. The suite calls area(Box(2,2)); the args are
   not AST literals, so no seed is harvested and the type-blind fallback raises
   AttributeError on every call; the generator refuses to treat an exception as a
   pin. area(Box(2,3)) would separate w*h from w+h at once — the gap is seed
   CONSTRUCTION (replaying constructor calls the tests already contain).
 - L2, distant literal — a failure the agent FIXED and measured. `w > 20` vs
   `w > 120` with a suite mentioning only 5.0, 10.0, 200.0: local mutations reach
   nothing in (20, 120], so the first pool found no witness. Adding midpoints of
   the suite's own per-argument values recovers it with fee(105.0). THE POOL IS
   ONLY AS WIDE AS THE SUITE'S OWN NUMBERS, and nothing bounds how far a wrong
   literal sits from them.
 - THIN MARGINS EVEN ON SUCCESSES. The B pair (`>= 21` vs `> 20`) had exactly ONE
   separating input in a 21-input pool — the single -0.5 float mutation. A pool one
   mutation narrower would have failed B SILENTLY.

F9 — scoreboard of every distinct AMB pair measured (11 distinct pairs):
    separable by a single value                       9   separated 8/9
    not separable by any single value (spellings,
      distributional)                                 2   correctly refused 2/2
    non-Python source                                 1   0/1, and cannot

## 4. Lanes
Reached: BUILT (513 -> SHIP) and BUILT+AMB (515 -> ADD_STATE), by direct call and
through 24 real `fluidfix repair` runs. Never reached: UNREAD, NOTWIN, HIDDEN,
CAPPED, REFUTED, SELF.
The ADD_STATE lane is rule-reachable today ONLY THROUGH A PROXY: loop.py:218 sets
AMB from set_amb or len(sites)>1, so it fires only when two greens land inside one
candidate set or at different lines. Two greens from two different candidate sets
at ONE line — the whole corpus in F2 — never reach it. The observation that would
make it reachable there is exactly a differential witness (F5). Beyond the lane,
ADD_STATE has NO ACTUATION AT ALL; the lane the USER never reaches is "here is the
test to add".

## 5. Potential
- MEASURED: on the 12-fixture corpus, wrong repairs go 6/12 -> 0/12 at 0 extra
  suite runs and 0.10 s per ambiguous site. The corpus is 12 HAND-BUILT fixtures,
  not a sample of real defects; the 6/12 is a property of those fixtures, NOT A
  BASE RATE.
- MEASURED: 8/9 separation on single-value-separable pairs, 2/2 correct refusals.
- UNMEASURED: everything on a real repo — not run on Box2D, cglm, or tests/. The
  frequency of one-line AMB in real defect corpora is unmeasured, so the fraction
  of real repairs this would change is unmeasured.
- UNMEASURED: whether replaying constructor calls fixes L5.
- For C, the differential IDEA survives but the MACHINERY does not: separating two
  C candidates means compiling and running both, which is coracle.py's job, not
  ast's. Whether that is cheap is unmeasured.

## 6. Defects
D1 OBSERVATION (confirmed, independently reproduced). loop.py:218 measures AMB as
   set_amb or len(sites)>1. Neither term can see two greens that arrived in
   different candidate sets at one line. The law is handed byte 513, correctly
   rules SHIP, and one of two DIFFERENT programs ships, chosen by kind number.
D2 ACTUATION (new here). ADD_STATE is a ruling with NO ACTUATION: it appears only
   inside an f-string at loop.py:237 and is never compared. The user is told to
   "add one pinning test" and is given no test, no witness input, and no statement
   of how the candidates differ — although loop.py holds every green's full file
   content at that moment and the difference computes in 0.10 s with zero suite
   runs. A refusal that names the missing evidence while WITHHOLDING EVIDENCE IT
   ALREADY HAS is an unbuilt actuation.
D3 WORDING (minor). The AMB refusal at loop.py:233-237 reports only len(greens) and
   line numbers; in the one-line case it reads "2 candidates at 1 different lines".
NONE OF THE THREE IS A RULING DEFECT.

## 7. Verdict
ADD_STATE's missing actuation is buildable and cheap: a differential test generated
from the greens the loop already holds separated 12/12 ambiguous fixtures with zero
suite runs and 0.10 s each, turning 6 wrong repairs into 0, and the same witness is
a direct measurement of the AMB bit loop.py:218 currently proxies — but the method
as built is Python-only and reaches none of fluidfix's C corpus.
