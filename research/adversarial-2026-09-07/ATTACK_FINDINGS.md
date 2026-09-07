# Adversarial results (coordinator log; full evidence in each NN-*/ATTACK.md)

## 07-compensating-one-site  *** S1 — WRONG REPAIR SHIPPED ***
FLUIDFIX DID NOT HOLD. Two different programs green at ONE line in TWO DIFFERENT candidate sets defeat the AMB proxy entirely: set_amb only fires WITHIN a single act's set, and `sites` collapses to one, so AMB is never measured at all.
  byte passed: 513 (BUILT)      -> law rules SHIP, CORRECTLY
  byte owed:   515 (BUILT+AMB)  -> ADD_STATE
`fluidfix guard .` wrote `readings[1] >= limit` over a pristine `readings[0] > limit`, exit 0.
Over 12 fixtures (6 matched pairs, identical defect and suite per pair): 12/12 shipped, 6 WRONG. Output is BYTE-IDENTICAL within each pair, so the choice is provably blind to correctness — it is a coin flip, not a judgement.
Secondary S3 (wording): the summary hides the second green.
Control (both greens inside ONE set) correctly refused — the existing protection works only in that one shape.
CLASSIFICATION: observation. The law ruled correctly on the byte it was given.

## 01-oracle-gaming-c  *** TWO S1 — WRONG REPAIRS SHIPPED, C PATH ***
FLUIDFIX DID NOT HOLD. Both classified observation; no ruling defect.
  byte delivered: situation(BUILT=True, AMB=False, CAPPED=False) = 513 -> SHIP
  byte owed:      situation(BUILT=True, UNREAD=True)             = 517 -> ADD_MATERIAL
Run A — the harness directory named `unittest/` ESCAPES the three-name directory regex, and the harness's own main.c:29 frame nominates it as candidate #1. fluidfix wrote `for (i = 0; i > ntests; i++)`, so the suite now RUNS ZERO TESTS and exits 0. A green suite that tests nothing.
Run C — a root-level check.c printing TAP: the output cross-examination missed `not ok 2 - GeomPerimTest`, so it shipped `failures = failures;` while the suite still prints "assertion failed".
Control (harness in test/) repaired the real defect byte-exactly — the defence works only for the directory names it knows.

## 08-capped-ship  *** S1 — WRONG REPAIR SHIPPED ***
FLUIDFIX DID NOT HOLD. Classification observation.
A truncated observation packet (signal filter OR stride sample — two independent routes) sets capped0=True at guard.py:508, but repair() derives CAPPED only from WALL-CLOCK, so loop.py:217 was handed:
  byte delivered: 513 (BUILT)         -> SHIP
  byte measured:  545 (BUILT+CAPPED)  -> RAISE_BUDGET
The guard wrote a COMPENSATING repair at pkg/geom.py:15, reported "repaired", exit 0. The true defect at line 10 is untouched and headroom(0,1,5) now returns -1 instead of 5.
With full sight the law refuses: BUILT+AMB -> ADD_STATE, with both greens.

## 02-oracle-gaming-python  *** TWO S1 — WRONG REPAIRS SHIPPED, PYTHON PATH ***
FLUIDFIX DID NOT HOLD. Both classified observation.
The oracle-protection filter guard._is_test_path WHITELISTS FOUR FILENAME SPELLINGS. 12 OF 17 real-world oracle layouts ESCAPE IT — ledger/testing.py, test/helpers.py, and the numpy.testing / pandas._testing shapes among them.
Because the assertion executes INSIDE a shared helper, that helper is the DEEPEST TRACEBACK FRAME and becomes candidate #1, often the only one. So the guard edited the helper green (exact=True->False; STRICT=True->False) and NEVER OPENED THE DEFECT FILE.
  byte delivered: 0x0201 -> SHIP
  byte owed:      0x0203 -> ADD_STATE   (cross-file AMB is structurally unmeasurable today)
Control with the same helper in conftest.py produced the CORRECT repair — again, the defence works only for the spellings it knows.
_still_reports_failures held against a FORGED EXIT STATUS but is BLIND TO `skipped`.
A re-run after the "repair" reported `suite green` on a fresh defect.

## 03-weak-assert  *** S1 WITH A MEASURED RATE — THE HEADLINE NUMBER ***
fluidfix HELD on rollback, refusal honesty, and both AMB terms it actually measures. It did NOT hold on green IDENTITY.
Over 65 in-vocabulary defects injected into two weak-suite repos:
    32 turned the suite red
    26 repairs accepted
     4 were A DIFFERENT PROGRAM
    = 12.5% of detected defects, 15.4% of ACCEPTED REPAIRS
It reported "engine law: BUILT -> SHIP" on 10 of 26 while HOLDING A SECOND, DIFFERENT PASSING PROGRAM IT NEVER PRINTED.
  byte passed:    0x201 (BUILT)      -> SHIP
  byte supported: 0x203 (BUILT+AMB)  -> ADD_STATE
3-second reproduction: ./repro_s1.sh
CLASSIFICATION: observation.
NOTE for any public claim: this is the rate ON DELIBERATELY WEAK SUITES. It is not the rate on a well-tested repo, and must never be quoted as one. But it IS the honest answer to "what happens if my tests are loose", which is most game code.

## 05-flaky-adversarial  *** S1 + A STRUCTURAL LIMIT ***
fluidfix did NOT hold against a FAILURE-ARMED leniency window. PERIODIC flakes do NOT beat it (0/35 — the three red baseline probes stop them), so the HIDDEN lane is real; it is the shape that matters.
S1: `fluidfix guard` wrote `return b - a` for `return a - b` and reported "repaired" — on a defect with NO CORRECT REPAIR IN ITS VOCABULARY.
  byte passed: situation(BUILT=True, AMB=False, CAPPED=False) = 0x201 -> SHIP, correct for that byte.
  BUILT was set from FOUR RUNS THAT ALL SKIPPED THE ONLY DISCRIMINATING TEST.
Untuned rate: 6/36 via repair(), 4/15 via guard.
THE STRUCTURAL RESULT: FLUIDFIX_CONFIRM=k is beaten by ANY WINDOW >= 2(k+1) — a clean staircase measured across k=0..3. Re-confirmation is therefore not a defence that can be won by raising k; an adversarial (or merely unlucky) flake shape scales with it. This bounds the whole confirmation approach and argues for the law's actual ruling, CHANGE_GRANULARITY, rather than more repetitions at the same granularity.
Also S3: refusals that DO catch the flake still headline "fault is outside the taught vocabulary".
CLASSIFICATION: observation.

## 04-tautological-test  *** S1, WITH A CLEAN BOUNDARY AND A FREE FIX ***
fluidfix HELD against a FULLY tautological suite: a green tree is never searched ("suite green — nothing to do"), `assert False` refused honestly, and all refusals left trees byte-identical.
It did NOT hold against a PARTLY tautological one. With ONE honest failing test plus ONE HOLLOW PINNING TEST, all five tautology flavours (swallow, never-calls, dead branch, empty parametrize, assert True) shipped `BONUS = 8` -> `BONUS = 7`: an edit to CORRECT code that leaves the real defect intact and NEWLY BREAKS payslip.
  byte: 0x201 (BUILT only) -> SHIP, a correct ruling.
  The honest arm, same code, refuses via REFUTED.
Mechanism: hollow tests DELETE REJECTIONS, so AMB can never fire — the suite cannot distinguish candidates, and the absence of disagreement reads as agreement.
FREE FIX SIGNAL the agent identified: count DISTINCT KILLING TESTS (1 vs 2). Cheap, already available.
CLASSIFICATION: observation.

## 09-spelling-vs-program  *** S1 + S4 + THE REMEDY, MEASURED ***
THE DEFINITIVE STATEMENT OF THE AMB DEFECT: fluidfix's ambiguity bit measures WHICH ACT PRODUCED A GREEN, not WHAT THE GREEN COMPUTES. A 2x2 of matched fixtures shows the proxy deciding on the COLUMN while the truth is the ROW — and it is wrong in BOTH off-diagonal cells.
S1: `fluidfix guard` shipped `return tax - subtotal` for `return subtotal + tax`.
  byte 513 -> SHIP ; correct byte 515 -> ADD_STATE.
  THE RIGHT REPAIR WAS FOUND IN THE SAME RUN AND DISCARDED BY THE TIE-BREAK.
S4 (the opposite error): a CORRECT repair refused FOR BEING CORRECT TWICE — 515 -> ADD_STATE where the honest byte 513 -> SHIP. So the proxy both ships wrong programs and refuses right ones.
S3: every ambiguity refusal headlined "outside the taught vocabulary".
THE REMEDY, MEASURED: a DIFFERENTIAL PROBE over the greens fluidfix ALREADY HOLDS separates all four cells in 0.1 ms — roughly 2,000x cheaper than a single suite run. The information needed to fix the largest wrong-repair class is already in memory and costs essentially nothing to use.
The law was right on every byte it was given.

## 06-compensating-two-site  *** S1 — CROSS-FILE AMBIGUITY IS STRUCTURALLY INVISIBLE ***
fluidfix did NOT hold. Its AMB defence is SCOPED TO ONE FILE, but the property it protects belongs to the PROGRAM.
`sites` in loop._rule holds LINE NUMBERS WITHIN A SINGLE defect_file, and cguard_once RETURNS AT THE FIRST FILE THAT REPAIRS — so a green in a second file is never compared to the first. Cross-file ambiguity cannot be measured at all, by construction.
On a C fixture the guard shipped `+ 25` -> `+ 24` in src/rate.c, leaving the real defect (`units * 8`, spec 7) in src/fee.c.
  byte measured: 513 {BUILT}       -> SHIP
  true byte:     515 {BUILT, AMB}  -> ADD_STATE
5/5 runs; ALL FIVE BILLING VALUES WRONG. Moving both sites into ONE file makes it refuse 5/5 — the defence exists and simply cannot see across the file boundary.
CLASSIFICATION: observation.

--- AMB DEFECT, ALL THREE DIMENSIONS NOW MEASURED ---
  two greens inside ONE candidate set        -> DETECTED, refuses correctly (control, agents 07/03)
  two greens at DIFFERENT LINES, same file   -> detected via len(sites)>1
  two greens at ONE LINE from different acts -> BLIND (agent 07: 12/12 shipped, 6 wrong)
  two greens in DIFFERENT FILES              -> BLIND by construction (agent 06: 5/5 wrong)
Remedy for all of them is the same and was measured by agent 09: a differential probe over the greens already held, 0.1 ms, ~2,000x cheaper than one suite run.

## 11-rollback-kill  *** S2 — CORRUPTION, UNRECOVERABLE ***
fluidfix did NOT hold on integrity. Classification actuation.
A SIGKILL mid-candidate under `fluidfix repair` leaves fluidfix's OWN BROKEN CANDIDATE on disk (n = -1), with the journal correctly holding the original. BUT `fluidfix repair` and `fluidfix jguard` NEVER CALL recover_inflight — only guard/cguard do. So the natural user response, running `repair` again, reads the leftover as the user's source, begin_inflight re-journals THAT as "original", and its finally-restore plus end_inflight DELETE THE TRUE RECOVERY POINT. The repo is left as a broken variant the user never had, unrecoverable even through the sanctioned recover_inflight. Reproduced end to end (exp2, exp3).
Separately: _write is NON-ATOMIC. A kill during the write left mod.py at ZERO BYTES (exp4).
HELD: guard/cguard startup recovery, and byte-exact content plus file-mode fidelity of recover_inflight.

## 13-stale-and-symlink  *** S2 x2 — INCLUDING A CONTAINMENT ESCAPE ***
HELD on line endings, permissions, hardlinks and rollback integrity. Did NOT hold on containment or the SpanEdit writer.
S2 (observation) — CONTAINMENT ESCAPE: a symlink INSIDE the repo root is written STRAIGHT THROUGH to a file OUTSIDE the root, and reported under the in-root name. guard.py:137 checks containment with normpath, NOT realpath; loop.py:75 follows the link. recover_inflight repeats the escape. fluidfix can therefore modify files outside the repository it was pointed at, while reporting an in-repo path.
S2 (actuation) — a taught 2-line SpanEdit on a CRLF file ships with N-1 CRs dropped (loop.py:320). Law byte 0x201 -> SHIP was correct.
S4+S3: a UTF-8 BOM makes the correct repair be rejected as "does not compile"; one future-dated file pins stale_binary() True unfixably.

## 17-estimate-honesty  *** S3 — THE COMMERCIALLY DAMAGING ONE ***
The REPAIR PATH HELD: no S1, no S2, and every guard refusal was honest. `fluidfix estimate` did NOT.
estimate is the FIRST command a prospective customer runs, and it overpromises:
    promised : "1.4s-7s, up to 80 runs" — and calls it "the realistic number"
    actual   : 34.74s and 139 pytest runs
    of those 139, 118 are COVERAGE runs whose existence estimate's own closing line DENIES
    fluidfix then reports the run to the user as "9 suite runs"
So three numbers disagree: what was promised, what happened, and what was reported.
Also: estimate REFUSES a C repo that cguard then repairs in 9.15s.
Also: after following its own `fluidfix init` advice, it sells a repair-time number for a SMOKE SUITE WHERE NO REPAIR CAN EVER LAND.
CLASSIFICATION: observation. The engine law is never consulted in cmd_estimate, so no ruling was possible.
Repro: reproduce.sh

## 19-class-collision  *** S1 — THE OUTCOME IS DECIDED BY A REGISTRATION INTEGER ***
fluidfix does NOT hold on class collision. Two taught classes greening ONE LINE from TWO candidate sets escape BOTH AMB disjuncts at loop.py:218.
  byte handed to the law: 0x0201 (BUILT, AMB=0) -> SHIP, and greens[0] is written.
WHICH of the two CONTRADICTORY programs lands is decided by THE INTEGER TYPED IN register(). Swapping kind 4 and kind 5 ships THE OTHER PROGRAM from identical evidence, an identical byte, and an identical acts_tried list.
Merging the same two repairs into ONE class refuses correctly (0x0203 -> ADD_STATE). So IDENTICAL greens LISTS GIVE OPPOSITE OUTCOMES depending only on how the classes happen to be registered.
S3: the report prints "ambiguous": false beside a TWO-ENTRY greens list; the guard reports nothing.
CLASSIFICATION: observation.

## 18-teaching-poison  *** S1 x2 — NOTHING VALIDATES A TEACHER ***
HELD on healthy repos and against all corruption attempts. The TEACHING PATH did not hold: nothing validates a teacher.
S1a — a taught kind-4 class OUTRANKS fluidfix's own correct shipped kind-11 repair. Two different green programs at one site, set_amb=False, sites={2} -> byte 0b00000001 (BUILT) -> SHIP greens[0]. On the true byte BUILT+AMB the law rules ADD_STATE.
S1b — SpanEdit's anchor check is CONTAINMENT, NOT PROXIMITY, so a taught SpanEdit(1, len(file)) flipped an UNCOVERED COMPLIANCE FLAG 13 LINES FROM THE DEFECT, and reported it as "repaired line 1" (S3, wording).
HELD: green-suite precondition, clobber warning, coverage localisation, byte-exact rollback.
Rerun: ./reproduce.sh

## 12-concurrent-guards  *** S2 x3 — USER DATA DELETED ***
The rollback is sound for ONE process with NO concurrent writer, and holds absolutely there (single-run journal invariant held 8/8). But fluidfix CLAIMS EXCLUSIVE REPO OWNERSHIP WITHOUT TAKING A LOCK.
F1 (actuation) — A USER EDIT MADE MID-SEARCH IS DELETED by the stale-snapshot rollback, and the report claims a clean repair. Byte 513 BUILT=True -> SHIP; the law was correct, the body rewrote the WHOLE FILE from its t=0 snapshot.
F2 (observation) — a STALE JOURNAL OVERWRITES THE USER'S OWN HAND-FIX and deletes their new function, ON A GREEN REPO. The record carries no owner, hash or age, and the write happens BEFORE decide() is ever called.
F3 (observation) — guard B DELETES guard A's journal, stranding a red mutation with no way back.
*** IMPLICATION FOR THE PRODUCT: the unattended interval mode (`--interval`) is exactly the configuration where a developer edits while a guard runs. F1 and F2 are therefore not corner cases for that mode; they are the normal case. ***

## 10-rank-veto-abuse  *** S4 DENIAL — AND TWO DEFENCES HELD ***
HELD against corruption and against wrong-repair: BUILT+CAPPED -> RAISE_BUDGET blocked EVERY S1 path attempted here, and rollback left both trees byte-identical. Did NOT hold against denial.
S4 (observation): rank.py's RETRIED veto is never measured — guard.py:511 and 585 never pass retried=. Escalation RE-RAN 64 OF 64 logged candidates that pass 0 had already rejected (new = 0). So `fluidfix guard --budget 60` REFUSED a shipped-vocabulary defect after 40.9s, when the same tree repairs in 22.2s unbudgeted. The budget was spent entirely on repeating known failures.
  byte passed for an already-rejected line: 0b01101100 -> law returns priority 2
  correct byte:                             0b11101100 -> priority 7 (veto)
S3: the refusal blames the vocabulary and never mentions the clock.

## 14-hang-and-resource  *** S3 — A SECOND PUBLISHED CONTRACT CONTRADICTED ***
HELD on correctness: no wrong repair, no repo corruption, no bad ruling. The CHANGELOG contract "a hanging candidate is killed, not orphaned" does NOT hold.
A real `fluidfix guard` run printed "repaired line 5 in 9 suite runs"; ONE SECOND LATER the user's own suite was 3 errors, because a hang manufactured by fluidfix's OWN _flip_augmented act leaked an ORPHAN (ppid 1) still holding a port.
  byte: situation(BUILT=True)=513 -> SHIP, correctly. The law has NO BIT for process lifetime.
ROOT CAUSES:
  oracle.py:157 and javaoracle.py:53 have NO GROUP KILL AT ALL — the Python and Java paths have no hang protection whatsoever. The process-group kill exists only on the C path.
  coracle.py:200 derives the pgid from an ALREADY-REAPED pid, so killpg SILENTLY DEGRADES TO A NO-OP.
  No rlimits anywhere.
Fork-bomb, memory and CPU escalations were described but deliberately NOT RUN (shared machine).
CLASSIFICATION: actuation.

## 16-refusal-honesty  *** S3 — 7 OF 20 REFUSALS STATE A CAUSE THE RUN CONTRADICTS ***
DECISIONS HELD: no S1, no S2, no ruling defect. REFUSAL REPORTING did not: 7 of 20 collected refusals (35%) state a cause the run contradicts.
A pass HOLDING a suite-passing candidate reports either "every generated candidate was rejected by the suite" (Python, --budget 30) or "fault is outside the taught vocabulary" (C, --budget 15), while loop.repair() returned greens=["r = b - a"] / ["int r = a + b;"] AND the honest BUILT+CAPPED reason.
  byte handed to the law:  situation(REFUTED=True)   = 0x0240 -> HARVEST_COUNTEREXAMPLE
  byte the run supports:   situation(BUILT, CAPPED)  = 0x0221 -> RAISE_BUDGET
Also: clock-limited refusals blamed on the vocabulary; a C "no traceback frame" claim printed alongside two frames that were found AND used; a rejection count reported as 64 when the true count was 124 (the harvest cap leaking into a user-facing number).
This is the FOURTH independent confirmation of the headline defect, and the first to quantify how often a user is actively misled: better than one refusal in three.

## 15-byte-exact-audit  *** S1 FROM A REGEX, AND THE BYTE-EXACT CLAIM SCOPED ***
HELD AT THE FILE LEVEL, BROKE AT THE LINE LEVEL. 15 of 18 accepted repairs were byte-exact.
File-level byte fidelity survived 20/20: CRLF, CR-only, BOM, missing final newline, tabs, non-ASCII, and 0o755 mode all preserved.
S1 (observation) — a REGEX BUG. _swap_return_operands (acts.py:188) ends in `(.*)$`, so on a COMMENTED line it moves the comment across the operator:
    return a - b  # signed difference     ->     return a  # signed difference - b
fluidfix reported "repaired". delta(9,2) now returns 9 instead of 7. The result is syntactically valid, passes the suite, and is wrong.
Two different green programs sat at one site in different candidate sets, so AMB was measured False: byte 513 -> SHIP; correct byte 515 -> ADD_STATE. (Same root cause as agents 07, 09, 19.)
Also: trailing whitespace destroyed on two repairs — and on fixture 11 the BYTE-EXACT GREEN WAS IN HAND and the other one shipped (S3). A UTF-8 BOM refused as "rejected by the suite" when NO SUITE RAN (S3/S4). A latin-1 source crashes build_packet UNCAUGHT (S4).

--- COORDINATOR NOTE ON THE PUBLIC "BYTE-EXACT" CLAIMS ---
Checked the live games page against agent 15's audit. The site does NOT claim byte-exactness universally. Every instance is attached to a SPECIFIC measured repair (Box2D b2Cross, cglm, the C# library, the hard-mode contact solver) or to the rollback ("byte-exact rollback held across 192 rejected candidates"). Agent 15 measured file-level byte fidelity surviving 20/20 including CRLF, CR-only, BOM, missing final newline, tabs, non-ASCII and 0o755 mode, and the rollback held. So THOSE CLAIMS STAND AS WRITTEN and should not be softened.
What agent 15 found is a CODE DEFECT, not a false claim: acts.py:188's `(.*)$` corrupts commented lines, and trailing whitespace is destroyed on some repairs (15 of 18 byte-exact on its own corpus). Fix the regex; leave the site copy alone.

## 20-end-to-end-hostile  *** S2 — IT COMMITS FILES YOU DID NOT ASK IT TO ***
HELD ON THE DECISION: no S1, no corrupted source, no test file touched, and the engine law ruled correctly on every byte.
S2 CORRUPTION (actuation): `guard --commit` runs `git commit -m msg` WITH NO PATHSPEC (guard.py:690). It sweeps the user's UNRELATED STAGED WORK and a PRIVATE SCRATCH FILE into a commit titled "fluidfix: restore billing.py:2 ... accepted by the project's own suite". Law byte 0x01 -> SHIP was correct; THE BODY COMMITTED MORE THAN SHIP ASKED FOR.
S3 x2: every budget-exhausted C refusal claims "nothing pointed at a file" AND ADVISES AGAINST the bigger budget the law had just ruled for, discarding the byte-exact green it found. And a repair into a gitignored generated source reports "nothing to commit" at exit 0.

=== ADVERSARIAL WAVE COMPLETE: 20 of 20 ===
