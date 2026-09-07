# Verdicts as they land (coordinator log; full evidence in each NN-*/REPORT.md)

## 08-engine-monotonicity
Exhaustively, no single-bit addition (0 of 1024) and no multi-bit addition (0 of 5733) moves an engine-law refusal to SHIP. Closed form verified 256/256: SHIP iff (x & 0x7E) == 0, i.e. none of AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED set; more evidence can only withdraw SHIP. HIDDEN was measured-but-uncarried in 9 of 24 searches and the shipped line was correct each time.

## 16-sight-exhaustive
Python port == authored C == spec on all 256 inputs; R1/R2 hold by gate algebra (gate 0 on all 224 pointing inputs, -1 on the 32 others); UBIQUITOUS is exactly +1 on the 16 non-pointing lower bytes, no order inversion. No ruling defect. BUT: the body asks SIGHT only on the Python no-frames path; guard.py:146-150 returns before the law whenever a traceback names an in-repo source file, and coracle.py/javaoracle.py never import it, so the law rules nothing on Box2D/cglm. The body cannot construct the 64 FAILONLY+UBIQUITOUS inputs and misdescribes its own tie-break.

## 07-engine-precedence
Precedence is exactly "lowest set bit among AMB<UNREAD<NOTWIN<HIDDEN<CAPPED<REFUTED wins; BUILT/SELF never win" on 226/256 bytes plus two 15-byte borrow families (NOTWIN+high -> AUTHOR_SUCCESSOR; BUILT+AMB+UNREAD+high -> RAISE_BUDGET); matches all 9 documented intents; the body exercises only four multi-bit bytes, all on the ladder.
DEFECT (observation): packet-CAPPED is measured at guard.py:508 but never delivered to the BUILT byte at loop.py:217 (repair() has no channel). A built fixture measured this shipping a compensating repair as BUILT -> SHIP with the real defect left in place; the held byte BUILT+CAPPED rules RAISE_BUDGET, and full sight refuses as BUILT+AMB.

## 04-engine-amb-adversarial
The body's AMB proxy (set_amb or sites>1) measures WHERE two greens came from, not WHETHER THEY ARE THE SAME PROGRAM. Two failure directions, law correct on every byte it was given:
 - F4 / D-1 (observation defect): `return base - delta` with weak test apply_delta(0,5)==5 -> kind 2 greens `delta - base`, kind 3 greens `base + delta`; set_amb=False, sites=1 -> byte 0x201 -> SHIP the wrong program (wrong repair on disk, pin FAIL). The same law rules ADD_STATE on 0x203 (loop.py:218).
 - F5: one program spelled twice inside one candidate set is refused as AMB.
Note: this contradicts the 0.14.0 comment "two spellings at one site are not AMB" as implemented: the proxy is site/set based, not program-equality based.

## 14-rank-ties
Ties are the ranking law's specification, not a flaw. But the body collapses to only 3 of the law's 8 lanes: 100% of observations on real fluidfix source tie under a plain assertion failure, median top-class 16. The body breaks those ties with two keys of its own — NAMED degree (guard.py:422-427, documented) and ascending line number (silent).
DEFECT (actuation): the RETRIED veto is implemented at guard.py:413 but neither call site (guard.py:511, 585) ever passes retried=, so the lane is DEAD. Measured on fixture_repay: 52 of 128 logged suite runs (41%) re-tested a (line, candidate) pair a previous pass had already rejected. The data needed is already in result.tried_log.

## 18-sight-bits-audit
All eight SIGHT bits fire somewhere, but three are mismeasured by the body: FRAMED, TOUCHED, SCARCE. Every ruling on the bytes actually handed to the law was correct.
DEFECT (observation): guard.py:146 returns the traceback list BEFORE consulting the law, so FRAMED-as-specified is unreachable (sight() calls: 0 on fixture f7_realframe). What does reach the law is `basename(rel) in framed_files` — an UNFILTERED BASENAME SET. Fixture pair f5/f5b differs only by renaming a decoy pkg/decoder.py -> pkg/dcodr.py: byte 193 (priority 0, opened 2nd) vs byte 192 (priority 6, opened last), on a collision with the stdlib json/decoder.py. Every FRAMED-carrying byte is priority 0, so a basename collision with any stdlib module in a traceback promotes an unrelated file to first place.

## 09-engine-self-lane
SELF means "the job is the worker". It changes the ruling on exactly 2 of 128 bytes (135, 136), NEITHER constructible by fluidfix today. OR-ing SELF into all 11 observation bytes the body can build changes 0 rulings. SELF is live only with NOTWIN (measured nowhere in src/) or a BUILT+AMB+UNREAD call site that does not exist. The lane has never fired and has never ruled wrong. NEGATIVE RESULT WORTH KEEPING: building a SELF observation would change nothing — do not spend effort there.
Also: BUILT+SELF -> SHIP, so SELF is NOT a brake; replacing guard.py's _is_test_path filter with it would be a regression.
DEFECT (wording): engine.py:27 says HIDDEN is unmeasured; it IS measured, at loop.py:391.

## 21-pair-exhaustive
PAIR law exact on all 256 vs the authored spec, the C kernel, AND an independent algebraic re-derivation; R1-R5 and the five incidents clean; 2/256 reach PAIR. Cost numbers reproduce (1,063 single-edit candidates -> 564,453 pairs -> 22.87 days at 3.5s).
EXPOSURE: 108 of 256 rulings are pinned ONLY by a case table transcribed three times from ONE author (docs/laws/pair.c:spec, tests/test_pair_law.py:spec, cli.py:_pspec). The whole CAPPED act (64 bytes), WIDEN (4) and TEACH (5) have no independent pin. Self-consistency, not an independent oracle for intent.
PAIR sits ONE unmeasured bit from a refusal: x=57 refuses, +PARTIAL alone -> PAIR. PARTIAL has never been measured.
DEFECTS (wording x3): pair.py:77-79 claims selfcheck verifies R4/R5/the incidents — it verifies spec/R1/R2/R3 and the reach count only. pair.c:27 "whatever else is true" is too strong (x=133 -> CAPPED). PAIR_LAW_PROMPT incident 4's "the ONLY situation" is wrong: 2 bytes rank PAIR and one has TAUGHT clear.

## 02-engine-lane-reach
The body constructs 9 of 256 engine situations and obtains 6 of 8 acts. RESHAPE and AUTHOR_SUCCESSOR are blocked by exactly ONE unmeasured, repo-undefined bit: NOTWIN. All 32 situations ruling either act have NOTWIN set. SELF would add no act at all. UNREAD confirmed reachable. A 7th call site found at cli.py:474.
DEFECTS: two wording, zero wrong rulings. engine.py:27 says HIDDEN is never set; loop.py:391 has set it since 0.13.0.

## 19-sight-vs-coverage  *** SEVERE OBSERVATION DEFECT ***
On cglm the gcov tier is a 10.7s constant that changes the defect file's rank in 1 of 13 injections, and is unavailable as shipped. SIGHT is never called on the C path at all; replicated there it collapses to constant priority 2 from two mismeasured observations. What actually finds the file is a 9ms name-affinity prefix in find_candidate_files_c (10/13 top-1) — not coverage, not the law.
F5/F6: LITERAL, SIGHT's only POINTING bit that fires on C, is harvested from the ABSOLUTE CHECKOUT PATH that cglm's ASSERT prints via __FILE__. The digits 07/09/19/2026 came from the agent's own directory name; "07" matched a "2013/07" URL comment in exactly vec2.h and ivec2.h, promoting those two WRONG files to priority 0 in 13/13 runs. The directory you check out into can decide which file fluidfix looks at first.

## 10-engine-refuted-harvest
The counterexample harvest is WRITTEN on both the Python and C paths but READ BY NOTHING in src/, and capped at 64 rejections per file. The recorded 1,063-candidate contact_solver.c refusal would have kept 6.0% of its counterexamples and reported 64 as the count.
DEFECT: on the C path the refusal blames the taught vocabulary instead of naming REFUTED, because coracle.py never calls decide() (grep -c HARVEST_COUNTEREXAMPLE src/fluidfix/coracle.py = 0). Measured through the real cguard_once() on a minimal C project: candidates generated, all refuted, refusal reads "fault is outside the taught vocabulary" with an empty hint. That is the exact path the Box2D refusal took.

## 20-sight-misdirection
SIGHT ranks the decoy first on the pure-assertion misdirection (defect file 6th of 6). On the traceback misdirection SIGHT is never consulted at all: guard.py:131-150 returns traceback-named files before sight is imported ("SIGHT consulted for 0 file(s)"), and the frame branch EXCLUDES the defect file from the candidate list entirely — turning an available 6-suite-run repair into a refusal. Offering the omitted file repairs in 6 runs / 5.3s. sight_r1_check.py proves widening cannot demote the framed file (0 of 128x128 inversions). Both body defects (one actuation, one observation); no ruling wrong.

## 13-rank-vs-recurrence
Ordering fault classes by measured recurrence would save ZERO suite runs as shipped, and on the 50 reachable Box2D/cglm defects recurrence order is measurably WORSE than the shipped order (163 vs 154 candidate positions; oracle bound 145). Recurrence is a ninth bit rank.py lacks, not one it mismeasures.
DEFECT (observation): loop.py:283 converts obs.kinds to a BITMASK — all 720 permutations of a 6-kind line yield one mask (3087), and five permutations run end-to-end give identical acts_tried/suite_runs. Class ORDER is unrepresentable, so acts.py:60's documented "most specific first" ordering is measured and then discarded. Also: rank priority 1 is unreachable because FAILONLY is never set.

## 01-engine-exhaustive
All 256 rulings re-derive identically from the docstring formula, the raw vendored 1555-char LAW (sha256 48bf50bf...) and decide(). Closed form: lowbit(bits 1..6) + 4*[x mod 16 in {7,8} and x>=23]. 0 of 1,024 bit-flips move a refusal to SHIP. Only 8 of 256 inputs are pinned by anything (3.1%); body-constructible but unpinned: 0, 33, 35. The shipped selfcheck re-derives 5 single-bit engine rulings, not 256.
F5: SELF unlocks ZERO acts. NOTWIN gates 32/256 bytes and BOTH dead acts (RESHAPE, AUTHOR_SUCCESSOR). NOTWIN is the highest-leverage missing observation.
DEFECT (observation, D1): when a candidate file is searched and the taught vocabulary yields ZERO acts, the body packs byte 0 (no blocker) at guard.py:539. The law rules SHIP, the equality test fails, and the result falls through to a HARDCODED refusal message; no act name reaches the user. That situation is the docstring's own definition of UNREAD, whose ruling ADD_MATERIAL is exactly what the hardcoded text already advises. Fix is a measurement, not a branch.
DEFECTS (wording): engine.py:27 stale on HIDDEN; the BITS[i]<->ACTS[i] table implies SELF -> AUTHOR_SUCCESSOR but SELF rules SHIP.

## 03-engine-actuation-map  *** HEADLINE DEFECT ***
Of the engine law's 8 acts: only SHIP and RAISE_BUDGET change behaviour. ADD_STATE, ADD_MATERIAL, CHANGE_GRANULARITY and HARVEST_COUNTEREXAMPLE are WORDING ONLY — proven by a ruling-swap probe (run the fixture twice, second time with decide() monkeypatched; behaviour identical). RESHAPE and AUTHOR_SUCCESSOR are absent. acts.py actuates ZERO of the 8: its ACTS dict is router act codes 0..15, a different namespace — the engine docstring naming it the actuation table is a name collision.
DEFECT (observation, headline): guard_once DISCARDS repair()'s BUILT+CAPPED -> RAISE_BUDGET ruling. guard.py:519 measures REFUTED as "candidates were generated", but engine.py:24-25 defines it as "candidates were generated AND the suite rejected every one"; result.greens is never read (no occurrence of 'greens' in guard.py). guard.py:508/538 also omit the wall-clock cap. Measured: greens=['K = 1'] in hand, yet the user is told "every generated candidate was rejected by the suite", and the file is left unrepaired.
    ruled at loop.py:217 : BUILT+CAPPED            -> RAISE_BUDGET
    built at guard.py:539: CAPPED=0, REFUTED=1     -> HARVEST_COUNTEREXAMPLE (gate FALSE, pass stops)
    actually is          : CAPPED=1, REFUTED=0     -> RAISE_BUDGET            (gate TRUE, pass retries)
    "the ruling was never wrong. The byte was."
guard.py:520-529 branches on .repaired and .ambiguous only; the third outcome _rule produces, green-but-capped, has NO branch. Not covered by test_law_never_ruled_wrong.py:35-37.

## 11-rank-exhaustive
Ranking law correct and COMPLETELY pinned: 256/256 vs its docstring spec, RETRIED veto proven dominant on every input both exhaustively and algebraically, zero inputs unpinned. But the body measures only 6 of 8 bits, so ruling 1 is unreachable and the veto has never fired in production.
Correcting a projection from the interrupted run: supplying RETRIED from data guard_once already holds (attempts, guard.py:585) saves ZERO suite runs on a completed search (22 vs 22) because repair() never stops at the first green by design (loop.py:244-263). BUT under a tight escalation budget it converts a FALSE "fault is outside this vocabulary" refusal into the true BUILT+CAPPED -> RAISE_BUDGET, finding the repair in 5 runs where baseline spent 10 and found nothing.

## 12-rank-winning-class
The ranking law ranks LINES only and does that well on this corpus: winner first in 23/27 fixtures, priority 0 correct 12/12. The body pins SIGNALED to a constant, masking three lanes down to two live ones.
F2: exact attribution of every pre-winner suite run gives 25 wasted = 5 line + 20 class + 0 candidate (two independent methods agree, zero unmatched). So 20 of 25 wasted runs are spent choosing among CLASSES on the already-correct line — a dimension NO LAW RULES TODAY. Class order comes from loop.py:297 EMIT over kind ids, i.e. dictionary registration order, not evidence.

## 15-rank-bits-audit
Only 3 of the ranking law's 8 bits can decide anything on the one path that consults it: FRAME and NAMED are measured but Python-only, SIGNALED is a constant, FAILONLY and RETRIED are hardcoded zero, RECENT/CHEAP/DENSE sit above a bit that always fires first. The law is exact (256/256 by selfcheck); every gap is a missing observation or actuation.
F6/D3: cguard_once (coracle.py:758) and jguard_once (javaoracle.py:211) never call rank_observations — the ranking law is UNREACHED on Box2D and cglm entirely. (Second law confirmed absent on the C path, after SIGHT.)
F5: the escalation pass re-tries 18/18 (100%) of pass 0's rejected candidates, 19 suite runs each; wiring the dead retried= veto moves 6 of 10 escalation runs behind the fresh lines.

## 22-pair-observation-design  *** ACTIONABLE ***
All eight PAIR observations except CANCELING are computable from data the body ALREADY HOLDS — six at ZERO extra suite runs. Adding that one measurement takes the law from 5 of 8 acts reachable to 8 of 8. CANCELING (the R3 veto) is undefined before a pair is tried.
F3/F2: the failing COUNT and the failing NODE SET sit in the very string Oracle.check() already parses AND DISCARDS — it compiles _SUMMARY_FAIL but keeps only the first FAILED line. Without them PARTIAL/DISJOINT/COUPLED are unmeasurable, which makes PARTITION, PAIR and WIDEN algebraically unreachable. Measured bytes: 56/SINGLE, 1/TEACH, 55/PARTITION, 51/WIDEN.
DEFECT 1: failing_output()'s -x seeds --lf with a single test, so DISJOINT is unobservable on a cold repo.

## 06-engine-capped-budget  *** THIRD INDEPENDENT CONFIRMATION OF THE HEADLINE ***
BUILT+CAPPED -> RAISE_BUDGET is correct on every one of the 256 bytes and was reached LIVE at budgets 300 and 325. But the repair it protects is thrown away by EVERY caller. Defect 3 / F5 (msg_demo.out): the law rules BUILT+CAPPED (0x21) -> RAISE_BUDGET while holding a TWICE-CONFIRMED green (`if v >= limit:`); every caller reads only .repaired/.ambiguous, so the user is told "fault is outside the taught vocabulary."
Also: the 325/350 threshold is set NOT by --budget but by the undocumented file_share/2 cap at guard.py:591-592. Four actuation/observation defects, three wording, zero wrong rulings.

## 23-pair-two-bug-fixture
On a genuine two-bug fixture the PAIR law rules PARTITION on the measured byte 23 (EXHAUSTED|PARTIAL|DISJOINT|CHEAP), and that linear path converts the guard's refusal into a GREEN SUITE in one extra 2.7s pass. Every defect is in the body, not the ruling.
F3/F2: the guard NEVER OPENS THE SECOND FAULT FILE. failing_output() uses -x, so build_packet(inventory.py) returns anchor_lines=[] and zero candidates there. It then refuses with "fault is outside the taught vocabulary" while its own harvest log holds `return subtotal + tax` rejected by tests/test_inventory.py::test_needs_reorder — BOTH fixes were in vocabulary. Cross-site sweep: 80 pairs, 1 green, 0 CANCELING.
NOTE this is the same -x truncation agent 22 flagged as making DISJOINT unobservable on a cold repo.

## 05-engine-hidden-flaky  *** CONTRADICTS A PUBLISHED CHANGELOG CLAIM ***
CHANGELOG 0.13.0 states the HIDDEN wiring took the flaky false-accept rate "to 0 of 49 and 0 of 46". This agent measured, over 300 runs on a CODE-CORRELATED flaky suite: 52% -> 7% at CONFIRM=1 and 4% at CONFIRM=2. NOT zero. And on a CODE-INDEPENDENT flaky suite (90 runs) it cut CORRECT repairs from 50% to 3.3%. The published "0 of 49 and 0 of 46" was measured on an easier flake shape and must not be stated as the general result.
DEFECT (actuation, F4): the law rules CHANGE_GRANULARITY correctly and the body NEVER ACTUATES IT — it rejects the candidate instead. loop.py:391 is the only site setting HIDDEN, and it is discarded PER CANDIDATE; no search-ending situation() accepts it. So situation(REFUTED=True) yields HARVEST_COUNTEREXAMPLE where REFUTED+HIDDEN would rule CHANGE_GRANULARITY. One bit of plumbing, not a decision.
Prior 150-run batch validated (0 label/disk mismatches); fixture_b and replications new.

## 24-pair-canceling-fixture
The compensating-repair shape reproduces in Python and the CANCELING veto holds as authored (byte 121 -> REFUSE). But the bit also fires on an HONEST two-edit repair, does NOT fire on the Unity incident it was authored from, and cannot be measured without actually running pairs. PARTIAL/DISJOINT are not observable from the packet the body builds today.
F4: fixture E_only_canceling has exactly one jointly-green pair; it corrupts Vec3.__add__ globally, is invisible to the suite, and being UNIQUELY green would get decide(BUILT=1,AMB=0) = SHIP. The veto is the only protection there.

## 17-sight-real-files  *** MOST ACTIONABLE NUMBER OF THE RUN ***
20 single-token defects in 20 Box2D files, 83 injections total. The C body ranks the true file top-1 3/20, top-3 7/20, median 10. The SIGHT law is NEVER CONSULTED on the C path.
Controlled decomposition over 16 defects (control_tiebreak.out), each variable held fixed offline:
    BODY as shipped                        median 13
    sight() + law tiebreak (-n_fail)       median  4
    sight() + BODY tiebreak (+n_fail)      median 18
    NO sight(), BODY key only              median 20
    NO sight(), law tiebreak (-n_fail)     median  3.5   <- deleting the law changes NOTHING
    NAMED bit only + law tiebreak          median  3     <- best order measured
The entire measured gap comes from ONE code-decided sort key, coracle.py:735:
    extra.sort(key=lambda r: (-_spec(r), len(fail_cov[r]), r))
Flipping len(fail_cov[r]) from ascending to descending moves the true file from median rank 20 to 3.5 and top-3 from 4/16 to 8/16 — a measured saving of ~16.5 candidate files per defect, each costing a compile. End-to-end repair-rate effect UNMEASURED (no repairs were run).
Only 2 of 8 SIGHT bits carry information here; all three tier-1 POINTING lanes (FRAMED, LITERAL, and UBIQUITOUS on a true file) fire 0/16. FRAMED is structurally 0 in C: the assert fires in the test file.
Also: 10 of 30 injected files NEVER turned the suite red despite every site being on an EXECUTED line — assertion coverage, not line coverage. hull.c survived 7 injections.
CAVEATS the agent stated: one repo, one commit, 8 of 16 controls share a failing test pair so they are not independent; "prefer more executed lines" may reflect Box2D's shape and is unmeasured elsewhere.

## 34-body-decision-census  *** THE CENTRAL NUMBER OF THE WHOLE WAVE ***
Of 120 outcome-choosing decisions across loop.py, guard.py, acts.py, oracle.py and coracle.py:
    92 (77%) are CODE-DECIDED
    exactly ONE — loop.py:221 — is steered by a ruling alone
Of the body's SIX decide() calls: THREE are tautologies on a literal byte, ONE is decorative. That leaves TWO LIVE CONSULTATIONS of the engine law in the entire system.
And one of those two (guard.py:539) is fed a REFUTED bit that a live run shows reading True WHILE A CANDIDATE IS PASSING THE SUITE.
Top finding (No. 4), independently re-confirming the headline: guard.py:519 measures REFUTED as bool(acts_tried) — "candidates were generated" — where engine.py:24 requires "AND the suite rejected every one". A live repair() run returned acts_tried=[8] and greens=['    return a + b'] SIMULTANEOUSLY, after the law had already ruled BUILT+CAPPED -> RAISE_BUDGET. Feeding that byte to guard.py:539 yields HARVEST_COUNTEREXAMPLE, so escalation is skipped and the user is told every candidate was rejected. Compounding it: capped0 is never fed the first-pass deadline that did the capping, and GuardReport CARRIES NO greens FIELD, so the passing candidate is structurally unreachable by the caller.
All four coordinator-supplied examples verified. TWO REFINEMENTS TO EARLIER LOGS:
 - loop.py:230 agrees with the law on 4 of 4 constructible bytes TODAY, so it is a DUPLICATED PREDICATE and a desync hazard, not a live divergence. (Softens agent 03's Finding 4.)
 - the coracle.py:735 win (median 20 -> 3.5) comes from the TIEBREAK DIRECTION, not from the absence of sight(), which is worth only -0.5 places. (Sharpens agent 17.)
Full 120-row table in CENSUS.txt beside the report.

*** WHAT THIS MEANS FOR THE PUBLIC CLAIM ***
"The law rules; the body only measures and actuates" is TRUE OF THE LAWS and NOT YET TRUE OF THE SYSTEM. The six kernels are exact, exhaustively verified, and have never ruled wrongly on any byte in 25 reports and 17 attacks. But they are consulted twice in a pipeline that makes 120 outcome decisions. The gap between the architecture and the implementation is the honest subject of the next release, and it must not be described as if it were already closed.
## 35-magic-number-census  *** CONNECTS THE LAB ATTACK TO THE REAL REPOS ***
Every outcome-changing constant in the body is a threshold or name list standing in for a law bit the body measures APPROXIMATELY:
    22 feed a law bit
    16 gate an outcome with NO OWNING BIT AT ALL
    13 are fixed NAME LISTS
    NONE is pinned by a test
Two are wrong today; both observation/actuation, neither a ruling.
F2 (TOP) — this is the finding that makes the oracle-gaming attack real rather than synthetic. On the ACTUAL repos, the files escaping the test-path filter at guard.py:111-115 are THE RUNNERS: Box2D test/main.c (1 of 18) and cglm test/runner.c (4 of 42). And box2d/test/main.c:121 is `return 1;` — THE EXACT SHAPE OF THE RECORDED C-ADAPTER INCIDENT — which kind 1 decrements to `return 0;`. The only thing standing behind it is coracle.check()'s exit-code cross-examination. So the original oracle-gaming shape remains reachable on real Box2D today, guarded by a single defence.
F3 — guard.py:591-592's starvation cap is INERT past the escalation halfway point.

## 49-hotspots-remeasure  *** A SALES NUMBER THAT REPRODUCES BUT IS NOT USABLE ***
The arithmetic REPRODUCES: 57 files (not 58) and the "18%" exactly; the one-file gap is a knife-edge threshold (rank 57 clears 60% by 0.6 of a touch out of 2029) plus six commits of history drift, so 58 was NOT a fabrication.
BUT THE CLAIM IS NOT USABLE AS STATED. 54 of the 57 files DO NOT EXIST — deleted in Box2D's v2-to-v3 rewrite. 92.9% of the counted defect mass (1,885 of 2,029 touches) is in deleted files. You cannot write a test for a file that is gone.
The number that survives on files that exist today is 16 FILES (34% of the 47 extant files that ever broke, 21% of the 75-file engine).
Cause: an inconsistency INSIDE ONE COMMAND. rank_hotspots drops files not on disk (so the ranked table shows 25 real files) while coverage_to_reach does NOT filter (so the headline underneath is computed over 322 paths of which 275 are gone). Fixing it costs ONE LINE and yields 5.3x more actionable targets.
Also: 11.8% of counted defect mass is vendored GLFW, HelloWorld and Contributions that _SKIP misses — and Box2D/glfw/config.h is rank 58, the very file the threshold would add next.
THREE RECORDED VALUES OF THIS ONE MEASUREMENT DISAGREE: hotspots.py:15-21 says 61 files / 201 / 30%; CHANGELOG.md:122-129 says 58 files and "~30% of files"; README.md:154-155 says 58 files and "not 60% of the engine". The tool prints 18%, never 30%. The docstring's 207/201/61 does not reproduce under any of five fix-detection regexes. And 57 files is 76% of the 75-file engine, so README's framing is wrong in both directions.

## 41-add-state-actuation  *** THE REMEDY, BUILT AND MEASURED ***
A differential test generated from the greens loop.py ALREADY HOLDS separated 12 of 12 ambiguous fixtures, using NO GROUND TRUTH, at ZERO extra suite runs and 0.10 s each. On the exact corpus that produced the project's worst recorded outcome, wrong repairs went 6/12 -> 0/12.
It is not a proxy — it is A DIRECT MEASUREMENT OF THE AMB BIT. Handed the `units >= 10` vs `units > 9` pair the code comments warn about, it correctly finds NO witness and declines to call it ambiguous. Witness present = two programs = AMB=1 = ADD_STATE. Witness absent = one program spelled twice = AMB=0 = SHIP.
It also separates the two-site Unity compensating shape, by falling through from the entry point to the edited helper.
The artefact it emits is a pytest file with ONE COMMENTED ASSERTION PER CANDIDATE. The user uncomments one. FLUIDFIX DOES NOT PICK — which is exactly what ADD_STATE means.
LIMITS, stated by the agent:
 - C SOURCE IS A TOTAL FAILURE. ast.parse raises; targets_tried is empty. Box2D and cglm are C, so this method as built reaches NONE of the C corpus. The idea survives for C but the machinery must be coracle's, not ast's, and its cost is unmeasured.
 - Object arguments fail today because seeds are harvested as AST literals; replaying the constructor calls the tests already contain would likely fix it. Unmeasured.
 - The mutation pool is ONLY AS WIDE AS THE SUITE'S OWN NUMBERS. A wrong literal far from any value the tests mention is unreachable; the agent hit this, fixed it with per-argument midpoints, and says nothing bounds the distance in general.
 - MARGINS ARE THIN. One pair had exactly ONE separating input in a 21-input pool. A slightly narrower pool would have failed it SILENTLY.
 - A 2-run stability filter emits FLAKY pins (11/20 on a nondeterministic pair); 5 runs gives 0/20. The generator needs its own copy of the HIDDEN discipline.
 - The 6/12 is a property of 12 hand-built fixtures and IS NOT A BASE RATE. Nothing here was run on a real repo.

## 43-add-material-actuation  *** SECOND REMEDY, ALSO MEASURED ***
ADD_MATERIAL is wording-only and STRUCTURALLY UNREACHABLE when the traceback names an assertion helper, because guard.py:489 gates UNREAD on `not candidates` — and a helper IS a candidate.
F3+F4: on fixture B the body SHIPPED A WRONG REPAIR — it inverted the shared helper's `assert got >= want` to `<=`, suite green, defect untouched. decide(situation(BUILT=1, UNREAD=1)) is ADD_MATERIAL: THE LAW WOULD HAVE REFUSED.
THE REMEDY, MEASURED: measure UNREAD from the traceback (0 suite runs) and actuate it via the body's OWN SIGHT tier-2 ranking (2 suite runs). Result on 5 misdirection fixtures:
    defect file at rank 1 : 5 of 5
    refusals turned into correct repairs : 3
    wrong ships prevented : 1 (measured)
This is the fix for the red team's Python oracle-gaming S1, where the assertion lives in a shared helper that becomes candidate #1 and gets edited green while the defect file is never opened.

--- TWO PROVEN REMEDIES, BOTH CHEAP, BOTH FIXING MEASURED S1s ---
  ADD_STATE   differential probe over greens already held : 12/12 separated, 6 wrong -> 0, 0 suite runs, 0.10s  (Python only; C unsolved)
  ADD_MATERIAL widen when the material is a helper        : 5/5 rank 1, 3 refusals -> repairs, 1 wrong ship prevented, 2 suite runs
Both work by MEASURING A BIT THE LAW ALREADY HAS rather than adding a decision.

## 45-harvest-counterexample  *** THIRD REMEDY — AND IT REFUTES A PREMISE THE COORDINATOR SUPPLIED ***
COORDINATOR ERROR, CORRECTED BY THE AGENT: my brief told this agent that keeping rejected candidates as negatives is "a pure speed win with no correctness risk". THAT IS FALSE AS STATED. The agent tested the premise instead of accepting it and found (F4, safety_naive.out) that a memo keyed on (site, candidate) ALONE REFUSED A CANDIDATE THAT WAS GREEN. The premise holds ONLY for the TREE-SCOPED form, where negatives are keyed on a fingerprint of the tree they were rejected against. Any future work here must carry that key.
MEASURED WIN (tree-scoped form):
    a repeated refusal's candidates removed : 18 of 18 (100%)
    the escalation pass's candidates removed: 16 of 19 (84.2%)
    pytest invocations                      : 44 -> 28
    wall clock                              : 14.6s -> 9.3s
    the repair still lands BYTE-IDENTICAL
And 79% of the win needs only a READ-BACK of the last_refusal.json that fluidfix ALREADY WRITES.
This is the remedy for the measured waste: the escalation pass re-testing 100% of the previous pass's rejections, which agent 10 showed burning an entire budget into a false refusal.

## 33-incident-audit  *** THE CAPSTONE — AND IT CORRECTS THE COORDINATOR ***
THE CENTRAL CLAIM SURVIVES, VERIFIED MECHANICALLY: 29 of 29 byte->ruling pairs asserted anywhere this session re-derive EXACTLY from the shipped law (0 mismatches), and not one of ~30 new defects lives in a ruling. The agent also REPRODUCED the headline wrong repair from scratch, independently.
THE TEST THAT GUARDS THE CLAIM DOES NOT SURVIVE. tests/test_law_never_ruled_wrong.py:
  - carries 6 incidents against 63 now on record (33 historical + 30 this session)
  - test_no_defect_has_ever_lived_in_the_ruling asserts a HAND-WRITTEN column contains no "RULING". It is a SELF-DECLARATION, NOT A DETECTOR. Nothing in the build can put RULING there.
  - test_the_audit_carries_real_incidents is `assert len(real) >= 5` with 6 present, so UNDER-RECORDING CAN NEVER FAIL THE BUILD. The list could omit 50 incidents and stay green.
  - it would not have caught A SINGLE ONE of the ten wrong repairs the red team shipped.
  - it already degrades silently: 0.14.0's own CHANGELOG records three incidents never added to the file that release introduced.
CORRECTION TO MY OWN LOG (F8): ATTACK_FINDINGS.md carried 8 agents when 13 ATTACK.md files existed. TEN agents shipped a wrong repair or corrupted tree, not eight. Seven more had not yet written up. My log was a lower bound and I should have said so.
CORRECTION TO AGENT 21's CLAIM: the pair.py:77-79 wording defect is CONTESTED, not confirmed. Read as a JOINT claim over selfcheck AND the pytest file, the docstring is accurate; it overstates only selfcheck alone. Do not "fix" it as if it were plainly false.
ONE MEASUREMENT CLOSES SEVEN OF THE TEN SHIPPED WRONG REPAIRS: AMB measured on program identity rather than provenance. On the agent's own reproduction, greens had length 2 at ruling time, so the corrected byte 515 rules ADD_STATE — a refusal instead of a wrong repair, at zero extra suite runs.
ONE PARAMETER CLOSES TWO MORE: repair() has no capped= channel, so a capped0 already measured at guard.py:508 never reaches the byte.

## 50-zero-token-ledger  *** THE TRUTH AUDIT OF THE SALES MATERIAL ***
VERDICT: every number backed by a shipped artifact REPRODUCES; every number that CARRIES THE SALES PITCH does not.
REPRODUCED EXACTLY: the 33-bug benchmark (26/27 byte-exact v2, 17/27 v1, 33/33 localisation, 6/6 OOV refused) from docs/data/arm_a_full_results.json; ALL FOUR SCALE tables including 14/18 = 78%, median 187.8s, and every replay wall clock; all six historical test counts (55/59/67/69/108/122, exact); all six law kernels via selfcheck (router 4096/4096, the rest 256/256, sha256 48bf50bf... 1555 chars verbatim, PAIR 2/256); sight.c compiled: 0 wrong on 256, R1/R2/R3 0 violations, 1.24 ns vs the published 1.22; estimate's 12.2-61s band re-derived from cli.py:390,396.
*** F10 — THE FLAGSHIP CLAIM HAS NO ARTIFACT ANYWHERE. *** "795 tokens over 3 suite runs vs 0 tokens over 126" (CHANGELOG 0.14.0 and the entire games-page head-to-head panel: 795, 3, 126, 125 rejections, 54s CPU, 33 sites). grep -rn "795" excluding .git/.venv/research returns ONE HIT — THE CLAIM ITSELF. The trial repo scratchpad/headtohead (toolz clone, one commit) has an EMPTY .fluidfix/ (ls -la -> total 0). The only other occurrence CONSUMES 795 as an input constant. NOTHING ON THIS MACHINE DERIVES IT.
F6 — the hotspots number exists in THREE MUTUALLY INCONSISTENT PUBLISHED FORMS. Worst: src/fluidfix/hotspots.py's OWN DOCSTRING claims 207 bug fixes / 201 files / 61; rerunning THE CODE IN THE SAME FILE gives 576 and 322 — a factor of 2.8, far outside commit drift. The docstring's numbers cannot have come from the code that ships. CHANGELOG 0.12.0 prints 18%-denominator counts then asserts "~30% of files", contradicting itself.
F9 — the falsified "0 of 49 and 0 of 46" IS STILL LIVE on origin/master AND origin/gh-pages, because both of the coordinator's corrections are UNPUSHED. No raw log exists anywhere for 7-of-50, 4-of-45, 0-of-49, 0-of-46.
F7 — "82-agent fresh-eyes fleet (24 + 24 + 18 + 14)". That sums to 80.
F8 — "Java took 223 lines, C took ~450" mixes conventions: 223 is javaoracle.py TOTAL; coracle.py at v0.11.0 is 658 total / 476 code-only. Like-for-like is 223 vs 658. Understates the C adapter ~30%. Repeated 4x.
F12 — README and games.html say selfcheck re-derives FIVE laws. It prints SIX.
F11 — "nine incidents — observation (4) actuation (1) wording (1) ruling (0)" accounts for SIX. Three are clean cases.
The agent also listed EVERY number it could not reproduce, by category — external fluid-router citations, the whole head-to-head, the flaky series, and every C/C++/C#/game-repo run (no logs ship for ANY of them: Box2D 46 runs/82.8s, cglm 100 runs/326.7s, contact_solver 428 runs/1479s, C# 14 runs/20.8s, and the rest).

## 47-reshape-actuation  *** A WELL-ARGUED NEGATIVE ***
RESHAPE is undefined by the engine docstring and actuated nowhere (1 occurrence in src/: the ACTS table). Its 17 bytes all require NOTWIN with AMB and UNREAD clear.
READING NOTWIN AS RepairResult.restored_original IS UNSOUND. F5: restored_original measures BYTE-EQUALITY WITH GIT HEAD, so it INVERTS on committed defects — which is fluidfix's normal case, and is pinned by the project's own tests/test_guard.py:77. Measured on 5 real repair() runs: CORRECT repairs read NOTWIN in 2 of 5 scenarios.
The prototyped reshape RESCUED 1 WRONG REPAIR AND DESTROYED 1 CORRECT ONE, +2 suite runs, 4/5 correct before and after. Net zero.
F4: AMB OUTRANKS NOTWIN, so any multi-green NOTWIN can never reach RESHAPE anyway.
CONCLUSION: do not build this on restored_original. The suggestion in agent 01/03's reports is refuted.

## 48-estimate-potential
Reach: 32 of 47 roots (68%) get a number, 15 (32%) refuse; on repos the agent constructed rather than fixtures fluidfix authored, only 4 of 16. Eleven of the fifteen refusals are ONE cause (pytest exit 5, nothing collected). estimate refused HONESTLY in 15 of 15 cases where nothing was timed.
F4 (DEFECT, observation): it prints a CONFIDENT BAND for a suite in which ZERO TESTS EXECUTED. repos/03 is a src/-layout package not pip-installed — THE STATE EVERY REPO IS IN THE MOMENT YOU CLONE IT, which is exactly when a prospective customer runs estimate. pytest exits 2 with "1 error in 0.09s", collection interrupted; the summary scan accepts it because it matches " error", so the "no test results" guard never fires. The 0.33s measured is THE COST OF FAILING TO IMPORT. This defeats the stated contract in CHANGELOG 0.9.2: "It will not print a number when the suite did not actually execute."
F6: `2 * suite_timeout // 60` floors to 0 for any timeout under 30, so the refusal argues the cost is prohibitive with the sentence "even a 2-run repair costs over 0 minutes".
F7: `secs` is the WHOLE PROCESS wall time (interpreter + pytest startup included), then a further +0.5s startup is added on top and the label implies it was not included. On a fast suite the double count is the majority of the projected number.
F5: the timeout refusal advises "pass test paths after the root" — NO SUBCOMMAND ACCEPTS THAT. Oracle.extra_args exists and no CLI path ever populates it.
F3/F10: C and Java repos are refused with a pytest diagnosis whose three "common causes" are all wrong, and never told to try cguard/jguard. A test-free repo is never told about `fluidfix init`, while an all-skipped suite IS told to run it, wrongly.
Measured potential: coracle's own machinery already gives ~0.9-1.1s per candidate warm on the C fixture, so estimate could print a 1.8-11s band today instead of refusing.

## 26-router-exhaustive
The fluid-router law is EXACT on all 4,096 inputs; identity, bijection, composition, renumbering and high-bit independence all hold. F1/A1 = WORKED_EXAMPLE (0,5) at acts.py:53; Fq = the observer kind.
F5 (DEFECT, observation): the body consults it on EVERY candidate set but ONLY at the frozen family route(0, 5, kind) — 16 of 4,096 inputs — and its ruling prunes 0 OF 5,232 CANDIDATES over a 7,872-line corpus, because obs.kinds is computed from the same regexes the appliers already self-guard on. Routing saves 0.0000% of suite runs under the shipped observer. A PRECISE ONE-KIND OBSERVATION WOULD MAKE THE IDENTICAL RULING WORTH 27.6% (1,446 of 5,232).
Fifth law confirmed exact and fifth law confirmed under-consulted.

## 27-lanes-exhaustive  *** SIXTH LAW EXACT; VERIFICATION WINDOW IS THE WRONG WINDOW ***
EMIT/ADVANCE/HALT are EXACT on all 65,536 masks the body can construct — 0 wrong on the full 16-bit domain, not just the 256 the docstring checks. No ruling defect.
F2 (TOP): THE VERIFIED WINDOW AND THE CONSTRUCTIBLE WINDOW OVERLAP IN 16 MASKS. The shipped dictionary's kinds are [0,1,2,3,8,9,10,11,12], so the reachable set is 512 masks — and every mask containing any of kinds 8-12 is >= 256. Of the 512 the body can build, 16 (3.1%) fall inside the verified 0..255 window and 496 (96.9%) fall outside it. Conversely 240 of the 256 verified states need bits 4-7, the unregistered user slots, so they are unreachable.
Not hypothetical: replaying the observer's own regexes over Box2D gives 42 distinct masks, 27 of them outside the verified window, covering 8.7% of signalled lines; over fluidfix's own src/, 26.7%.
The law is right on all of them. The EXHAUSTIVENESS CLAIM is scoped to the wrong window (lanes.py:9-10 and selfcheck's "on 256 states").
F3 (observation): mask_of is a SET UNION, so the observer's documented "most specific first" ordering is ERASED before the law sees it. EMIT then rules on DICTIONARY NUMBERING. Measured on Box2D: flipped-comparison-direction is preceded on 100% of its 2,655 live lines, by 1.86 classes on average. Scope note the agent supplied: MechanicalObserver already emits in ascending id, so on the mechanical path THE LOSS IS PROVABLY ZERO; the ordering loss applies only to the model-backed observer, and how often that differs is UNMEASURED.
F4: kinds 13,14,15 pass the loop.py:283 filter, are EMITted faithfully, have NO APPLIER, and drain SILENTLY — never appended to acts_tried, so a refusal cannot mention them. Zero suite runs wasted; the defect is that the situation is invisible.
F5: lanes.py is the ONE Python port with no _s32 width discipline; HALT diverges from the authored C at exactly m = -2147483648. Unreachable from loop.py.
F6: guard.py:400-405 reads obs.kinds under a DIFFERENT domain than loop.py:283 and swallows the exception into cheap=False. mask_of([True]) = 2, so a JSON true becomes fault kind 1.

## 42-change-granularity-actuation  *** FOURTH REMEDY — AND IT VINDICATES THE LAW'S ACTUAL RULING ***
The edit ladder is token->line shipped, plus an atomic span rung reachable only by a taught transform, and NO CODE SELECTS A RUNG.
THE KEY INSIGHT: HIDDEN's real ladder is not the EDIT, it is THE RECORD. The body answers CHANGE_GRANULARITY with MORE SAMPLES AT THE SAME GRANULARITY, which is right on a code-correlated flake (24% -> 0% false accepts) and DESTRUCTIVE on a code-independent one (12/30 -> 0/30 correct repairs).
AN ACTUAL RECORD-GRANULARITY CHANGE — per-test records instead of per-run — IS THE ONLY SETTING CORRECT ON BOTH:
    fixture A: 30/30 correct, 0 false accepts
    fixture B: 29/30 correct
    cost: ~2x suite runs
F7: shipped CONFIRM=1 repairs 3 of 30 on a code-independent flake; PER-TEST RECORDS REPAIR 29 OF 30 at one suite run per candidate.
This is the law's own ruling taken literally — "stop judging at the granularity of a single run" meant the RECORD, and re-running was the body's substitute for it.

## 25-pair-cost-model  *** A FIFTH PUBLIC NUMBER IS A FUSION OF THREE RUNS ***
F3/F4 (TOP): the documented "1,063 single-edit candidates on contact_solver.c at 3.5s each" FUSES THREE DIFFERENT RUNS. The 1,063 is a 38-file, OVER-BROADLY-TAUGHT, 30-minute BUDGET STOP — i.e. CAPPED, not EXHAUSTED, which is the opposite of what the figure is used to argue. The 3.5s comes from two SUCCESSFUL REPAIRS, different runs again. The shipped vocabulary measures 13,523 candidates there, not 1,063.
Everything downstream inherits it: the 564,453 pair combinations and the "about 23 days" both derive from the fused 1,063 and the borrowed 3.5s. The arithmetic is right and the inputs are not comparable.
CHEAP's threshold, re-measured at 10.8s per candidate: n <= 11 at the 600s escalation budget, 26 at 3600s, 73 at a working day. Measured n is 5 and 110 on the Python fixtures and 438 / 463 / 5,041 on Box2D contact_solver.c — SO CHEAP IS FALSE FOR EVERY REAL C FILE.
And nobody decides it: pair.observe_bits is called from NOTHING in src/, leaving PAIR the one ruling of eight the law can never reach.

## 31-cross-rank-sight  *** A FIFTH CHEAP WIN: DELETE A SORT KEY THE DOCS ALREADY DISOWN ***
STRUCTURE: the two laws are not "consulted in an order" — SIGHT's answer is a PRECONDITION of RANK being asked. find_candidate_files (SIGHT) runs at guard.py:483; rank_observations runs at guard.py:511 INSIDE the per-file loop, on that file's lines only. THE BODY NEVER HOLDS BOTH ANSWERS AT ONCE, so it cannot compare them.
On the TRACEBACK path SIGHT is never consulted at all (find_candidate_files returns at guard.py:150 before line 216 imports it) — 2 of 6 fixtures. Corollary: SIGHT's FRAMED bit is nearly DEAD on the Python path, because any frame strong enough to set it triggers the early return. It fired on 0 of 12 SIGHT rulings.
DEFECT (actuation + wording, with a measured cost): sight.py:62 and guard.py:208 BOTH DOCUMENT a tie-break of (specificity, then executed-line count). guard.py:300 actually sorts (-affinity, -specificity, -n_fail, rel) — AFFINITY FIRST. Affinity is the same filename-token-overlap signal as SIGHT's NAMED bit, which the law DEMOTES TO CIRCUMSTANTIAL precisely because it once promoted the wrong click file. Inside the priority-0 class the caller reinstates it above specificity.
MEASURED: removing it (i.e. making the code do what both comments already say) cuts F5 from 10 suite runs / 12.49s to 6 / 2.91s, and F6 from 10 / 6.45s to 6 / 3.36s — 40% FEWER SUITE RUNS ON BOTH, at zero extra observation cost. It only re-keys a sort over data already computed.
Swapping the two laws changes the candidate reached first on only 1 of 6 fixtures, for a structural reason: RANK's FRAME bit and SIGHT's FRAMED bit are measured FROM THE SAME REGEX OVER THE SAME TRACEBACK, so THE STRONGEST BIT OF EACH LAW CAN NEVER POINT AT DIFFERENT FILES.
On these fixtures SIGHT emitted priority 0 for EVERY file — it discriminated nothing, correctly, because SCARCE saturates on six-line modules. So the caller's tie-break carried the whole outcome. The agent recorded that explicitly as NOT a defect.

## 46-raise-budget-curve  *** --budget DOES NOT DO WHAT ITS DOCSTRING SAYS ***
D1 (ACTUATION): with `--budget 450` the escalation was cut at 211.6s of the 422.3s remaining and the run REFUSED AT 238.7s WITH 211.3s (46.9%) OF THE USER'S BUDGET UNSPENT. Cause is guard.py:591-592, `file_share = (deadline - now) / 2` — the arithmetic matches the measured return to 0.03s. The halving is PER FILE, so file k of an escalation gets (1/2)^k of the remaining clock. guard_once's own docstring (guard.py:452, 550-551) says "budget caps the ENTIRE pass ... escalation gets ALL remaining wall clock". It does not.
F4: THE REPAIRING CANDIDATE WAS FOUND AT t=118.5s AND THE PASS REPORTED A REFUSAL ANYWAY. The budget was SUFFICIENT TO FIND and INSUFFICIENT TO PROVE: 90.6s of the escalation's 211.6s share reached the fix; the remaining 120.4s went into the uniqueness proof, which file_share cut short. A control with no deadline confirms it exactly: the repairing candidate is candidate 401 of 791, at observation rank 400 of 802.
D2/D3: the same BUILT+CAPPED -> RAISE_BUDGET ruling is produced and DISCARDED (guard.py:598-608 tests only .repaired and .ambiguous), then guard.py:611 rebuilds situation(REFUTED=True) WITH capped0 STILL TRUE IN SCOPE. The measured byte is 96 (CAPPED+REFUTED -> RAISE_BUDGET); the body asks byte 64 and gets HARVEST_COUNTEREXAMPLE. The user is told "every generated candidate was rejected by the suite" when TWO CANDIDATES PASSED.
F1: the progress-rate curve is FLAT, not diminishing-returns: 4.56 cand/s pass 0, 3.74 cand/s escalation, drift explained entirely by mean suite-run time. Suite time is 99% of wall clock. The search is a pure suite-run budget.
F3: 109 of pass 0's 110 candidates (99.1%) were re-judged in escalation, because `tried` is LOCAL TO EACH repair() CALL (loop.py:187). As a fraction of the whole run that is 12.2% of suite runs and 29.1s.
F6/F7/D4 — THE C PATH: a 258s cguard run on an injected cglm defect made ZERO LAW CONSULTATIONS. Worse, the bit is TRUE and thrown away: build_packet_c computed truncated=True for the very file holding the defect, and THE DEFECT LINE 944 IS NOT IN THE PACKET AT ALL (110 lines sampled of 1278). decide(situation(CAPPED=True)) is RAISE_BUDGET. NO --budget CAN EVER REPAIR THAT DEFECT, because the escalation lane that rebuilds the packet exists ONLY on the Python path. C is 23x slower per candidate (6.23s vs 0.26s) because every candidate pays a rebuild.
F8 — A CLEAN ARCHITECTURAL ANSWER: decide() is 8 observation bits in, 3 BITS OF ACT IDENTITY OUT. No wiring of the existing kernel can emit a NUMBER. "How much" must be either (a) a second machine-authored kernel with a magnitude alphabet, or (b) a quantity the BODY computes, with the engine law only gating whether it is spent.
F9: every "how much" number today is a BODY CONSTANT — budget/3, escalate_budget 600, file_share /2, 990, 10**9, limit 999. None is derived from a measurement of the search in progress, and the /2 appears in no docstring, no --help and no test.
POTENTIAL — seven quantities ALREADY COMPUTED at the moment of refusal and thrown away, with measured values: untried observations (cglm 93 of 110, 84.5%), rate (0.161 vs 3.74 cand/s), cost per candidate (6.23s vs 0.26s), sight growth on a raise (110 -> 802 observations, 7.29x — literally the multiplier the budget needs), a green already in hand, repeated work (13.9%), and POINTED (already measured, used only to choose refusal wording).

## 44-author-successor-teaching  *** THE CORE COMMERCIAL CLAIM, TESTED ON REAL HISTORY ***
THE CLAIM: "a class taught once is repaired forever, on every future instance."
TESTED ON THE SIX REAL ONE-TOKEN FIXES IN CGLM'S OWN GIT HISTORY (2016-2024).

STAGE 1 — THE CLASS GENERALISES, AND THIS PART IS REAL. 6 of 6 at transform level.
ONE register() class, written from ONE worked example (cd1f179, 2016), emits the historically-correct repair for FOUR historical fixes spanning 2016-2023 and four different headers — including the 2023 aabb2d case, which it reaches only because the transform mines the digit pool from obs.all_lines (the digit 2 occurs nowhere on the broken line). Three classes cover 6/6.
  refract  1 candidate,  correct rank 1     transform  6 candidates, correct rank 3
  frustum 32 candidates, correct rank 9     maxsign    1 candidate,  correct rank 1
  rotatemake 6,          correct rank 2     euler     12 candidates, correct rank 10
NOTE: frustum emits EXACTLY 32 — the documented cap — so a slightly wider pool would have TRUNCATED THE CORRECT CANDIDATE AWAY.

STAGE 3 — END TO END, WITH CGLM'S OWN SUITE AS JUDGE: *** 0 OF 6 REPAIRED. ***
  3 of 6 defects ARE INVISIBLE TO THE SUITE. glm_aabb2d_transform and glm_frustum_corners have NO TEST AT ALL (grep of test/ returns nothing). glm_vec3_refract IS tested but the assertions do not pin the sign — and commit 48839a3, THE "fix refract" COMMIT ITSELF, LOOSENED THEM (ASSERT(dest[1] < -sqrtf(0.5f)) became < -0.3f). Injecting each defect leaves 1131/1131 passing.
  1 of 6 sites NO LONGER EXISTS at HEAD (the euler two-solution block is gone).
  2 of 6 are reachable and BOTH REFUSE UPSTREAM OF THE TAUGHT CLASS:
     - find_candidate_files_c NEVER NOMINATES THE DEFECT FILE. It scores failing-test-name tokens against file STEMS, and cglm's affine and util modules export glm_rotate_at, glm_decompose, glm_uniscaled, glm_inv_tr, clamp — none containing the token "affine" or "util", so those files score ZERO. The convention holds for cglm's vec/mat modules and FAILS for affine and utility.
     - With SIGHT PINNED to the true file, both STILL refuse — on BUDGET, not vocabulary: 54 candidates / 339.7s = 6.3s each; 64 / 340.5s = 5.3s. The rotatemake packet holds 80 observations and the index class emits up to 32 candidates each, so the space is 10^3-10^4 seconds. THE CLASS IS RIGHT; THE BUDGET IS THE WALL.
F5: once the file is named, the taught class FIRES ON THE EXACT DEFECTIVE LINE (observation on line 140: kinds [1,4]; on line 145: [0,4,10]). Vocabulary, signal and packet all work on the real defect. What is missing upstream is the file.
Only 1 of the 6 falls inside the SHIPPED vocabulary (maxsign, already kind 10).
F7 (wording): the C refusal advises `name the file yourself (--file <path>)`. `--file` EXISTS ONLY ON `repair`, the pytest path. On a C project THE FIRST REMEDY THE REFUSAL OFFERS CANNOT BE EXECUTED.
NO WRONG REPAIR was produced at any point; the tree was restored byte-exactly after every run.
The agent also caught and retracted its OWN harness bug: a substring test printed REPAIRED_CORRECTLY=True for maxsign because `if (a > b)` occurs at line 177 while line 145 was still defective.

## 37-cglm-lane-log  *** THE DEFINITIVE C-PATH PICTURE ***
Five single-token defects in cglm produced FIVE REFUSALS, 132 candidate suite runs, and ZERO engine, ranking, SIGHT and PAIR rulings. Only the lanes law and the router ran — 330 calls, all correct.
FINDING 3 — THE SINGLE BIGGEST C-PATH DEFECT, AND IT IS ONE LINE. All 66 kind emissions across all five runs were KIND 1, literal-off-by-one — INCLUDING on the three defects whose class was 3, 9 and 10. Chain, verbatim:
    acts.py:60      "kinds: most specific first"
    observers.py:37 kinds = [k for k,... in SORTED(KINDS.items()) if sig.search(line)]   <- NUMERIC order, not specificity
    loop.py:283     mask = mask_of(...)   <- ORs the bits; ANY order is destroyed
    loop.py:297     kind = kind_of(EMIT(mask))  <- lowest live bit, correctly and by spec
And KIND 1's SIGNAL IS THE REGEX `\d`, the least specific in the vocabulary. So on any C line containing a digit — nearly every line of cglm — the loop tries literal decrements FIRST and reaches the real class only after exhausting them. The lanes law ruled exactly per its docstring on all 264 calls; the mask it is handed does not carry the ranking the body's own contract promises.
NO RUN REACHED ITS OWN DEFECT LINE. Defect at observation index 40 / 33 / 50 / 71 of 110 / 110 / 59 / 110; the runs consumed 16 / 11 / 17 / 11.
FINDING 6 — THE PROOF IT IS THE PIPELINE, NOT THE LAW: handed the defect line DIRECTLY, the engine law ruled BUILT -> SHIP once and the repair landed BYTE-EXACT IN SIX SUITE RUNS (~45s, restored_original: true). Even there acts_tried was [6, 8, 0] — kind 1 first again — but with one observation instead of 110 it costs three suite runs instead of the whole budget.
FINDING 7 — ONE DEFECT IS UNREPAIRABLE BY CONSTRUCTION: kind 8 (minmax-swap) uses `\b(?:min|max)\(` in BOTH its signal AND its applier. A word boundary cannot occur after `_`, so it can never match C's namespaced `glm_min(`. The lane exists in the vocabulary and the router; the observation and the actuation both go blind on the C spelling.
FINDING 5: packet.truncated is computed at coracle.py:656 and READ ONLY IN guard.py — the Python path. On D5 the defect line was NOT IN THE PACKET AT ALL (the 110-line stride sampler dropped it), so no budget could have found it. That situation is exactly CAPPED, and the ruling for it was never asked for.
FINDING 2: loop.py:201 returns BEFORE decide() whenever no candidate went green, so A REFUSAL CAN NEVER CARRY A RULING ON THE C PATH, BY CONSTRUCTION. Line tracer: loop.py:[201,202] executed in all five runs; loop.py:217 in none.
HONEST NEGATIVE THE AGENT RECORDED: the file ranking is code rather than the SIGHT law, but it put the defect file at RANK 1 ON 5 OF 5. A code decision that did NOT change the outcome. Likewise the coverage tier correctly declined to drop candidates on a degenerate probe.
CHEAPEST FIXES the agent identified: pass packet.truncated and the rejected-candidate list into a decide() at coracle.py:750/770 the way guard.py:539 already does — NO NEW MEASUREMENT, and it changes five refusals from "--budget exhausted" to the law's own RAISE_BUDGET and HARVEST_COUNTEREXAMPLE.

## 36-box2d-lane-log  *** ONE RULING IN 2,233 KERNEL INVOCATIONS ***
Five Box2D cguard runs: 1 REPAIRED, 4 refused, 403 candidates, 2,233 kernel invocations, and EXACTLY ONE ENGINE-LAW RULING — byte 1, BUILT -> SHIP, actuated byte-exactly. Ranking law, SIGHT law and PAIR law: ZERO consultations across all five.
FINDING 3, CONFIRMED STATICALLY: coracle.py IMPORTS NO LAW MODULE AT ALL — not engine, rank, sight, pair, router or lanes. Six decide() sites exist in the body; TWO are reachable from cguard. SIGHT has exactly one body call site, Python-only. PAIR HAS ZERO CALL SITES ANYWHERE IN THE BODY — confirmed by call-graph reachability, not assumed.
FINDING 2: all four refusals returned from coracle.py:750-753 with a hand-written hint, no decide() on that path. Both CAPPED and REFUTED were TRUE in all four (64, 64, 211, 64 candidates rejected). The counterfactual is measured: byte 96 -> RAISE_BUDGET, byte 64 -> HARVEST_COUNTEREXAMPLE. The C body never packs them and never asks. The observations are ALREADY IN ITS OWN LOCALS: packet.truncated (computed coracle.py:656, discarded) is CAPPED; non-empty attempts is REFUTED. Making the lane reachable is packing TWO BOOLEANS THE C BODY ALREADY HOLDS.
FINDING 4 — FILE ORDER DECIDED THREE OF THE FOUR REFUSALS. Defect-file ranks: 1 of 7, 2 of 9, 42 OF 54, 27 of 34, 4 of 12. THE ONE RUN THAT REPAIRED IS THE ONE WHERE THE SCORE PUT THE DEFECT FILE FIRST. D3 is misdirection in pure form: ShapeTest names shape.c exactly (+3), but Box2D's mass functions live in geometry.c, which shares no token with any failing test, scores 0, and lands 42nd.
FINDING 6 — A DEFENCE THAT HELD IN THE WILD, UNPROMPTED. The first D4 run overran the wrapper and was SIGKILLed with a candidate on disk. THE NEXT RUN RECOVERED IT: "recovered src/arena_allocator.c: a previous run was killed mid-candidate; original bytes restored from the journal". That file was not one of the agent's five, so its own restore would not have touched it. recover_inflight did the work. This is the crash journal working on a real repo, on a file nobody was watching.
ALSO MEASURED — TWO UNENFORCED DEADLINES: the C deadline is checked only BETWEEN CANDIDATE FILES and between observations, NEVER INSIDE A CANDIDATE SET — up to 32 candidates at ~8s each. D4 at --budget 240 never returned within 300s; re-run at 120 it returned at 121s. And the gcov block (coracle.py:697-744) has NO DEADLINE CHECK AT ALL, so its cost is paid before the budget clock is ever read — it is what grew D3's candidate list from ~4 to 54 files.
Kinds 8 (minmax-swap) and 12 (flipped-boolean) were NEVER ROUTED in 482 router calls: their signals match no Box2D C line, because b2MinFloat( contains no min( and C has no True/False. Same class of defect agent 37 found on cglm.
NO WRONG REPAIR, NO WRONG RULING. The single ruling was correct and byte-exact; all four refusals were honest.

## 38-python-lane-log  *** THE CONSTRUCTIBLE VOCABULARY IS 10 BYTES OF 256 ***
43 guard passes over the Python fixtures. The body spoke FIVE DISTINCT ENGINE BYTES and NEVER RULED WRONG.
F2/F7 (TOP): static enumeration proves ONLY 10 OF 256 ENGINE BYTES ARE CONSTRUCTIBLE. RESHAPE and AUTHOR_SUCCESSOR are UNREACHABLE BY CONSTRUCTION — not merely unmeasured.
Worse: 3 OF 10 REFUSALS REACH THE LAW AS BYTE 0x00 — an EMPTY OBSERVATION, which the law can only answer SHIP — because BITS HAS NO LANE FOR "no candidate was ever generated". The refusal that follows is then hardcoded. Observation gap, not a wrong ruling. (This is the same defect agent 01 found as D1, now with a rate: 30% of Python refusals.)
IMPORTANT POSITIVE: BOTH live decide() calls ARE LOAD-BEARING. Suppressing guard.py:539's RAISE_BUDGET FLIPS A REPAIR TO A REFUSAL — measured. So the two consultations that exist are not decorative; they carry real weight. The problem is their number, not their quality.
SIGHT ORDERED NOTHING in 38 consultations. RANK's RETRIED veto fired 0 times in 1,904 calls — the fourth independent confirmation that the lane is dead.

=== BOTH WAVES COMPLETE: 44 research reports, 20 adversarial attacks ===
