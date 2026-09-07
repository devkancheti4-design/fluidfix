# 17-sight-real-files — REPORT
(Relayed by the coordinator: the agent's own write was blocked by a harness rule.
Reproducible evidence on disk beside this file: results.jsonl, summary2.txt,
control_tiebreak.out, and rerunnable retry2.py, pick_alt2.py, summarize2.py,
control_tiebreak.py.)

## 1. Target
Inject 20 single-token defects in 20 different Box2D source files; measure the
SIGHT rank of the true file (top-1, top-3, median) from the body's file ranking,
without running repairs.

## 2. Method
Continued the interrupted run. Repo copy box2d/ at dc67c40, restored in a finally
block; verified clean at exit (only untracked covbuild/). No git state command
used: the one file an interrupted slice left mutated (src/hull.c:46) was reverted
by rewriting that token in place.
measure.py injects one token, builds and runs the suite, then calls cguard_once(
..., budget=1e-6) so the deadline expires before the first candidate opens —
report.candidates is the body's order and ZERO repairs run (assert not
report.attempts). From the same cached gcov probes it computes the eight SIGHT
bits as guard.file_priority2 does and ranks by sight().
New this pass: retry2.py (resumable), pick_alt2.py (wider site grammar),
summarize2.py, control_tiebreak.py. Every build+suite ran one at a time under
nice -n 15 ./bin/timeout 300.
Totals: 83 injections, 167.4s measured build+suite time, 49 added this pass.
Target coverage: 20/20 files done. 30 files injected; 20 red and measured, 10
never turned the suite red.

## 3. Findings

1 — The C body NEVER calls the SIGHT law; every law_rank here is counterfactual.
    grep -rn "sight(" src/fluidfix/ | grep -v sight.py
      cli.py:511,514,517,520   (selfcheck re-derivation only)
      guard.py:216,280         (the PYTHON path)
coracle.py imports only _is_test_path from guard. Its docstring names the overlap
without using the law.

2 — Body ranking over 20 red defects: top-1 3/20, top-3 7/20, median 10.
    true file ranked at all : 17/20   not in the list at all: 3
    top-1 : 3/20 (15%)   top-3 : 7/20 (35%)   top-5 : 8/20 (40%)
    median rank among the 17 ranked: 10   mean 13.3   worst 30
    ranks: [1,1,1,2,3,3,3,4,10,16,22,24,25,26,27,28,30]
On the 16 defects with a named failing test the body is WORSE: median 13.
Distribution is bimodal: 7 ranked 1-4, nothing until 10, then 9 at 16-30.

3 (HEADLINE) — SIGHT would rank the true file at median 4, but the law is NOT
what does the work. control_tiebreak.py holds each variable fixed, offline, over
16 defects:
    BODY, real candidate list              top-1 3/16  top-3 6/16  median 13
    A  sight() + law tiebreak (-n_fail)    top-1 4/16  top-3 7/16  median  4
    B  sight() + BODY tiebreak (+n_fail)   top-1 1/16  top-3 3/16  median 18
    C  no sight(), BODY key only           top-1 0/16  top-3 4/16  median 20
    D  no sight(), LAW tiebreak (-n_fail)  top-1 3/16  top-3 8/16  median 3.5
    E  NAMED bit only + LAW tiebreak       top-1 5/16  top-3 9/16  median  3
    A vs D: sight() UP on 3/16, DOWN on 4, unchanged on 9; median 3.5 -> 4
A vs B (tiebreak flipped): 4 -> 18. A vs D (law deleted): 4 -> 3.5, i.e.
DELETING THE LAW CHANGES NOTHING. The discriminating variable is one sort key:
    coracle.py:733-735
        # executed-by-the-failure first, most specific and cheapest
        # to search first among equals
        extra.sort(key=lambda r: (-_spec(r), len(fail_cov[r]), r))

4 — SIGHT's SMALL bit points the same way as that tiebreak, and is wrong 14/16
times. SMALL (0 < executed lines < 80, sight.py:21) fires on 2/16 true files. The
body applies an UNBOUNDED total-order version of the same preference; the law's is
bounded (one of four circumstantial units), which is why deleting the law barely
moves the result while flipping the tiebreak moves it 16 places.

5 — Only two of eight bits carry information; the three tier-1 "pointing" lanes
never fire.
    FRAMED 0/16   SCARCE 3/16   LITERAL 0/16   FAILONLY 14/16
    NAMED  5/16   TOUCHED 16/16  SMALL  2/16   UBIQUITOUS 0/16
TOUCHED and FAILONLY are near-constant, so cannot discriminate. FRAMED is 0/16
structurally: in C the assert fires in the test file (coracle.py:495-497).
LITERAL is 0/16 because Box2D's ENSURE prints the expression, not a 2+-digit value.

6 — 4/20 red defects yield NO named failing test; SIGHT gets an empty universe.
    red defects with >=1 NAMED failing test : 16/20
    red defects with NO named failing test  : 4/20 -> bitset.c, contact_solver.c,
                                                     island.c, recording.c
    red defects the body called 'credible'  : 14/20
_fail_tests empty -> coverage probe empty (coracle.py:709-712) -> credible=False
-> the "NOTHING POINTED ANYWHERE" branch returns the 5 largest sources. True file
present once (contact_solver.c, rank 3), absent 3 times.

7 — Two of nine SCARCE signals can never match in guard.py. LATENT, not
outcome-changing. guard.py:269 runs sig.search(b) on whole-file text with no
re.MULTILINE; acts.py:86 and acts.py:109 are ^-anchored, so they can only match a
file whose first line is a bare return. Measured on src/distance.c:
swapped-return-operands linewise=15 wholebody=0; reversed-minus-operands
linewise=18 wholebody=0. Both exceed SCARCE's <=2 threshold line-wise, so fixing
the anchor would NOT have changed SCARCE on any of the 16 defects.

8 — 10/30 injected files never turned the suite red, after up to 7 sites each:
constraint_graph.c, distance_joint.c, hull.c, motor_joint.c, prismatic_joint.c,
sensor.c, shape.c, solver_set.c, weld_joint.c, wheel_joint.c. Seven are joints or
shape code. Every site was on a line the pristine suite EXECUTES, so this is
ASSERTION coverage, not line coverage — hull.c stayed green across 7
executed-line injections.

## 4. Lanes
Reached (body, C path): its FRAMED lane (0 true-file hits), its NAMED lane (put
table.c, dynamic_tree.c, world_snapshot.c near the top), its coverage lane and
credible >= 5 floor (14/20), the degenerate-probe fallback (6/20), the "NOTHING
POINTED ANYWHERE" branch (4/20).
Reached only counterfactually: every sight() lane. Observed true-file bytes were
SCARCE+FAILONLY+TOUCHED, FAILONLY+TOUCHED, FAILONLY+NAMED+TOUCHED, TOUCHED alone,
and two SMALL variants.
Never reached at all: FRAMED as a SIGHT bit (0/16 — needs a frame naming a
non-test file, which Box2D's ENSURE never emits); LITERAL (0/16); UBIQUITOUS on a
true file (0/16, so its penalty size is unmeasured); the entire Python guard.py
SIGHT path (read and mirrored, never executed — the target is the C repo).

## 5. Potential
- FLIPPING ONE SORT KEY. coracle.py:735 len(fail_cov[r]) ascending -> descending
  moves the true file from median rank 20 to 3.5 (control C vs D), top-3 from
  4/16 to 8/16 — a MEASURED median saving of 16.5 candidate files per defect,
  each costing a compile. End-to-end repair-rate effect: UNMEASURED (no repairs
  were run).
- Consulting sight() on the C path: worth a median of -0.5 places on this corpus,
  i.e. nothing. Value on a repo where FRAMED/LITERAL can fire: UNMEASURED.
- NAMED-only ranking (control E: top-1 5/16, top-3 9/16, median 3) is the BEST
  order measured, using one bit the body already computes. With a real repair loop
  attached: UNMEASURED.
- An observation naming a failing test when the binary aborts: worth 4/20 defects
  moving from no evidence to a ranked universe. Resulting rank: UNMEASURED.

## 6. Defects
1. ACTUATION. coracle.py:735 orders equal-specificity candidates fewest-lines-
   first. SIGHT owns file order and has a bounded bit (SMALL) for that preference;
   the body applies an unbounded total order the law never ruled on. Evidence:
   control C vs D, median 20 vs 3.5. FIX THIS FIRST — but note it is a decision
   about search COST while this study measured search ACCURACY; judge a fix on
   end-to-end repair time.
2. ACTUATION. The C path never calls sight() (finding 1). Costs ~nothing here
   (finding 3), so recorded as an unactuated lane, not a wrong outcome.
3. OBSERVATION. guard.py:269 whole-file ^-anchored matching (finding 7). No
   outcome in this study changed. Latent.
4. OBSERVATION. Aborting test binary -> empty _fail_tests -> empty SIGHT universe
   (finding 6), 4/20. The body degrades honestly rather than pretending its order
   means something; a missing observation, not a wrong ruling.
5. NO RULING DEFECT FOUND. On all 16 computable bytes, sight() returned exactly
   the priority its docstring and docs/laws/sight.c specify.

CAVEATS: one repo, one commit, 20 defects, comparison/additive flips only. The
16-defect control sample is small and 8 share the same failing pair
(MultithreadingTest, DeterminismTest), so they are NOT independent. "Prefer more
executed lines" may partly reflect Box2D's shape (a few large central files carry
most executed lines) and is UNMEASURED on any other repo.

## 7. Verdict
On 20 single-token defects in 20 Box2D files the C body ranks the true file top-1
3/20, top-3 7/20, median 10; the SIGHT law is never consulted on the C path at
all, and a controlled decomposition shows adding it would change the median by
half a place — the whole measured gap (median 20 -> 3.5) comes from one
code-decided sort key, coracle.py:735, which searches the fewest-executed-lines
file first.
