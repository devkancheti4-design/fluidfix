# 50 targets. One per agent. NN-slug is your directory name.

## ENGINE law (engine.py)
01-engine-exhaustive: re-derive all 256 rulings from the formula; compare to the docstring spec and to what tests/test_engine_fusion.py pins; list every input no test pins.
02-engine-lane-reach: find every decide(situation(...)) call in loop.py/guard.py/acts.py; enumerate which of the 256 situations the body can actually construct; list lanes it can never reach (UNREAD? NOTWIN? REFUTED? SELF?) and the observation each would need.
03-engine-actuation-map: for each of the 8 ACTS, is it actuated in acts.py/loop.py, partially, or not at all? Table with line numbers.
04-engine-amb-adversarial: build programs where two green candidates are one program spelled twice (units>=10 vs units>9) versus two genuinely different programs; test whether the body's measurement (set_amb, distinct sites in loop.py) classifies each correctly; hunt for a misclassification.
05-engine-hidden-flaky: build a flaky test fixture; measure false-accept rate with FLUIDFIX_CONFIRM=0,1,2 over >=30 runs each; report what CHANGE_GRANULARITY actually does in the body today.
06-engine-capped-budget: sweep budget on tests/test_span_edits.py's fixture (150..900); confirm BUILT+CAPPED -> RAISE_BUDGET and its message; find the threshold; is the first-pass/escalation split a code decision?
07-engine-precedence: when several bits are set (BUILT+AMB+CAPPED, BUILT+HIDDEN+AMB ...), which act wins and why, algebraically from the formula; does the precedence match the intended one in the docstring?
08-engine-monotonicity: property test over all bit-flip pairs: can adding one evidence bit ever move a ruling from a refusal to SHIP? Enumerate every such pair and judge whether each is intended.
09-engine-self-lane: what SELF means; can the body ever measure it today; what decide() rules for every SELF combination; design (report only) the observation.
10-engine-refuted-harvest: REFUTED and HARVEST_COUNTEREXAMPLE: is any counterexample harvested today? What would harvesting have given on the Box2D contact_solver.c refusal (1,063 candidates, recorded in CHANGELOG/docs)?

## RANKING law (rank.py)
11-rank-exhaustive: all 256 inputs vs the docstring spec; prove the RETRIED veto holds on every input; list inputs no test pins.
12-rank-winning-class: on the Python fixtures in tests/, log the rank the law gives each candidate class and which class actually repairs; distribution of "rank of the winner".
13-rank-vs-recurrence: measured recurrence in real histories (Box2D: off-by-one 14, compare 4, logic 3, boundary 2, sign 2; cglm: off-by-one 4, compare 2 — from the coordinator's scan) vs the ranking law's lane order; would ordering by recurrence save suite runs, and is that the law's business or a bit it lacks?
14-rank-ties: find observation bytes where two classes tie; how does the body break ties (line numbers); is tie-breaking a code decision?
15-rank-bits-audit: for each RANK bit, the exact code that measures it; classify measured / approximated / hardcoded.

## SIGHT law (sight.py)
16-sight-exhaustive: all 256 inputs vs sight.c's spec; R1/R2 algebraic check; UBIQUITOUS penalty behaviour on every input.
17-sight-real-files: copy Box2D into your dir; inject 20 single-token defects in 20 different source files; for each, measure the SIGHT rank of the true file (top-1, top-3, median) using the body's file ranking WITHOUT running repairs (build once, run the suite per defect under nice/timeout).
18-sight-bits-audit: which of FRAMED/SCARCE/LITERAL/FAILONLY/NAMED/TOUCHED/SMALL/UBIQUITOUS the body measures, how, and which are never set in practice.
19-sight-vs-coverage: on the same injected defects as a small Box2D or cglm copy, compare SIGHT's ranking to the gcov coverage tier in coracle.py: agreement, speed, and whether combining them is a code decision today.
20-sight-misdirection: build a repo where the failing test NAMES a file that is not the defect; does SIGHT rank the wrong file first, and what does the body do next?

## PAIR law (pair.py)
21-pair-exhaustive: all 256 vs spec, R1-R5, the five incidents in docs/PAIR_LAW_PROMPT.md; list inputs no test pins.
22-pair-observation-design: how the body could measure EXHAUSTED/PARTIAL/DISJOINT/COUPLED/CHEAP/TAUGHT/CANCELING/CAPPED from data loop.py already has; write a report-only script that computes the byte from a completed search on a fixture; report the byte and the ruling.
23-pair-two-bug-fixture: build a genuine two-bug Python program (two independent faults, two tests, each fix reduces failures); run the single-edit guard; compute the observation byte; confirm the law rules PARTITION.
24-pair-canceling-fixture: build the compensating-repair shape (a sign flip plus a candidate that breaks an operator so the faults cancel); compute CANCELING from single-edit results; confirm the veto.
25-pair-cost-model: measure single-edit candidate counts on fixtures and on one Box2D file; compute pair counts; where would CHEAP's threshold sit and who decides it today?

## ROUTER and LANES (router.py, lanes.py)
26-router-exhaustive: all 16^3 inputs of route(F1,A1,Fq); verify the formula; explain what F1/A1/Fq are in fluidfix and where route() is called.
27-lanes-exhaustive: enumerate every input of lanes.py EMIT/ADVANCE/HALT; verify against its docstring and tests/test_lanes.py; list unpinned inputs.
28-router-reach: with a wrapper script (not by editing src), log every route()/lanes call during guard runs on the Python fixtures; which routes are ever produced.
29-lanes-termination: can any input sequence make ADVANCE/HALT loop forever or halt early? Prove termination or exhibit a counterexample.

## CROSS-LAW
30-cross-engine-pair: engine CAPPED/RAISE_BUDGET vs pair BUDGET/CAPPED: enumerate the 256x256 combinations where one law says continue and the other says stop; is any such combination constructible?
31-cross-rank-sight: class ranking vs file ranking: which is consulted first in the body, does the order change outcomes; measure on fixtures.
32-cross-hidden-retried: engine HIDDEN vs rank RETRIED: both concern trying again; overlap, gap, or contradiction?
33-incident-audit: search git log, CHANGELOG.md, docs/ for every recorded incident; classify each (observation/actuation/wording/ruling); verify tests/test_law_never_ruled_wrong.py covers all of them; list any it misses.
34-body-decision-census: every `if` in loop.py/guard.py/acts.py/oracle.py/coracle.py that chooses between repair OUTCOMES (not measurement plumbing); list each with line number as law-ruled or code-decided.
35-magic-number-census: every numeric constant in the body that affects an outcome (budget split, confirm count, coverage credibility >=5 files, timeouts, escalation caps); which law should own each and as which bit.

## REAL-REPO LANE LOGS (heavy: nice, timeout 300, one run at a time, copy the repo first)
36-box2d-lane-log: 5 injected single-token defects in Box2D; run cguard per defect; log every law ruling; table of lanes hit and outcomes.
37-cglm-lane-log: same on cglm, 5 defects.
38-python-lane-log: run the guard on every Python fixture under tests/; log every ruling; table of lanes hit.
39-java-lane-log: the Java path (javaoracle.py, tests/test_java.py); run it if the toolchain exists; lanes hit; else document exactly what is missing.
40-refusal-anatomy: gather every refusal recorded in docs/, CHANGELOG.md and the games page text (research/../ghpages if present, else CHANGELOG only); classify each by the law's reason; for each, what observation or actuation would have turned it into a repair.

## ACTUATION POTENTIAL (prototype in your dir only)
41-add-state-actuation: ADD_STATE = ask for one pinning test. Prototype generating a differential test from two green candidates on an AMB fixture; does it disambiguate? Measure.
42-change-granularity-actuation: what granularity ladder exists (token/line/statement/block); prototype the switch on a flaky fixture; measure.
43-add-material-actuation: prototype widening the file set from SIGHT tier 2 on a misdirection fixture; measure.
44-author-successor-teaching: teaching from one worked example (tests/test_teaching.py, docs/TEACHING.md); apply it to the 6 real cglm one-token fixes from git history (subjects: "fix refract", "fix transform", "frustum: fix array index", "optimize operations, fix max sign", "fix rotate make", "fix euler angle val"); how many teach a class that then repairs the same defect re-injected?
45-harvest-counterexample: prototype keeping rejected candidates as negatives; measure candidate-count reduction on a second run of the same class on a fixture.
46-raise-budget-curve: progress-rate curve (candidates tried vs time) on the span fixture and one cglm defect; what observation bits would tell the law how much to raise.
47-reshape-actuation: what RESHAPE means per the engine docstring; is anything actuated; prototype one reshape on a fixture; measure.
48-estimate-potential: `fluidfix estimate` on 10 small public-style repos you construct or the fixtures; what fraction gets a number vs a refusal; which missing observation causes each refusal.
49-hotspots-remeasure: rerun `fluidfix hotspots` on the Box2D copy; reproduce or refute the recorded "60% of defects guarded by 58 files (18%)"; document the method.
50-zero-token-ledger: build the ledger of suite runs vs tokens for every run recorded in CHANGELOG.md and docs/; for each number, name the reproducible source; list any number that cannot be reproduced.
