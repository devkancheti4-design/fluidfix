# 49-hotspots-remeasure — REPORT
(Relayed by the coordinator: the agent's own write was blocked by a harness rule.
Scripts and raw outputs on disk beside this file: tmo.sh, remeasure.py, top57.py,
rename_aware.py, sensitivity.py, margin.py, vendored.py, run1-run7*.txt. Rerun
each as ./tmo.sh 300 <venv-python> <script> ./box2d)

## 1. Target
Rerun `fluidfix hotspots` on a private Box2D copy; reproduce or refute the
recorded claim that 60% of Box2D's defects are guarded by 58 files (18%).

## 2. Method
cp -R the shared box2d clone (HEAD dc67c40, 1377 commits, 23M); the shared clone
was never touched. No coreutils timeout, so every run went through tmo.sh
(nice -n 15 + perl alarm; verified to return 124 on timeout and pass the child's
exit status through). Serial, one at a time.
Read: hotspots.py bugfix_churn (59-91), coverage_to_reach (94-113),
rank_hotspots (116-148); cli.py cmd_hotspots (280-322). The claim is recorded in
THREE PLACES THAT DISAGREE WITH EACH OTHER: README.md:154-155,
CHANGELOG.md:122-129, hotspots.py:15-26.

## 3. Findings

F1. The number reproduces to within one file; the 18% reproduces exactly.
    scanned 1377 commits · 576 look like bug fixes · touching 322 source files
      guard 30% ->  17 files  (5%)
      guard 50% ->  40 files  (12%)
      guard 60% ->  57 files  (18%)
      guard 80% -> 136 files  (42%)
    Recorded: 17 / 40 / 58 / 138. Measured: 17 / 40 / 57 / 136.
    THE NUMBER THAT REPRODUCES IS 57, NOT 58. The "(18%)" is printed verbatim.

F2. The one-file gap is knife-edge and consistent with history drift.
    total touches = 2029; 60% target = 1217.4
      rank 56 +9 -> cum 1209  share 0.5959  src/body.c
      rank 57 +9 -> cum 1218  share 0.6003  src/world.c
      rank 58 +8 -> cum 1226  share 0.6042  Box2D/glfw/config.h
    Rank 57 clears the threshold by 0.6 of a touch out of 2029. Stable from
    HEAD~0 to HEAD~20; 56 at HEAD~30, 53 at HEAD~50. The record says 1,383
    commits; this clone has 1,377. So 58 is NOT a fabrication — it is the same
    measurement six commits ahead. Whether those six flip it is UNMEASURED.

F3 (HEADLINE). 54 of the 57 files DO NOT EXIST in Box2D. The set is not testable.
    rank  1  60 touches  MISSING  Box2D/Box2D/Dynamics/b2World.h
    rank  2  59 touches  MISSING  Box2D/Box2D/Dynamics/b2Body.cpp
    rank  3  56 touches  MISSING  Box2D/Box2D/Dynamics/b2World.cpp
    rank 52  10 touches  EXISTS   include/box2d/box2d.h
    rank 56   9 touches  EXISTS   src/body.c
    all history:  322 files, 2029 touches
      extant:      47 files,  144 touches
      vanished:   275 files, 1885 touches
THREE of the 57 exist. 92.9% of the aggregated defect mass lives in files Box2D
DELETED — the v2.x C++ tree removed by the 2018 restructure and the v2->v3
rewrite to C (336992f 2018-06-17 "Restructured folders").
This is an inconsistency INSIDE ONE COMMAND'S OUTPUT: rank_hotspots
(hotspots.py:127-129) drops files not on disk, so the ranked table prints 25 real
files; coverage_to_reach does NOT filter, so the "WHAT IT BUYS" number printed
underneath is computed over a 322-path universe of which 275 are gone.

F4. Recomputed over files that exist today, the answer is 16 files.
      guard 30% ->  6 files (13% of the 47 extant files that ever broke)
      guard 50% -> 12 files (26%)
      guard 60% -> 16 files (34%)
      guard 80% -> 28 files (60%)
    THE ACTIONABLE NUMBER IS 16 FILES — 21% of the 75 code files in the tree.

F5. README's "58 files, not 60% of the engine" is wrong in both directions.
    60% costs 57 files. Denominators:
      files that have ever broken (what the CLI prints): 322 -> 18%
      code files in the CURRENT tree (the "engine"):      75 -> 76%
    57 files is 76% of the engine, not a fraction of it — and the comparison is
    void anyway because 54 of the 57 are not in it. Separately CHANGELOG.md:129
    asserts "60% of defects costs ~30% of files"; the tool prints 18%. The 30%
    comes from the docstring's different run (61/201), so that CHANGELOG entry
    PAIRS ONE RUN'S FILE COUNT WITH ANOTHER RUN'S PERCENTAGE.

F6. hotspots.py's own docstring records a third run that does not reproduce.
    Claims 1,383 commits, 207 bug fixes, 201 files, 60% -> 61.
    The shipped _FIX finds 576 fixes / 322 files -> 57. Five alternative fix
    regexes were tried; NONE reproduces 207/201/61. Which configuration produced
    the docstring's numbers is UNMEASURED.

F7. 11.8% of counted defect mass is vendored or demo code _SKIP misses.
    80 files / 240 touches, incl. Box2D/HelloWorld/HelloWorld.cpp (16),
    Box2D/glfw/config.h (8), Contributions/Platforms/iPhone/... (6).
    _SKIP covers extern|external|third_party|vendor|deps, but Box2D vendored
    GLFW at Box2D/glfw/ and shipped HelloWorld/ and Contributions/.
    Box2D/glfw/config.h is RANK 58 — the file added if the threshold moved one.

F8. Rename-following recovers almost nothing; the loss is a rewrite, not renames.
    rename-aware churn: 235 files, 1895 touches; still on disk: 48 files.
    Collapses 322 paths to 235 and recovers exactly ONE extant file (47 -> 48).
    Rename-aware extant ranking: src/physics_world.c 12, include/box2d/box2d.h 10,
    include/box2d/types.h 9, src/body.c 9, src/distance.c 6.

F9. coverage_to_reach's arithmetic is correct.
    30/50/60/80%: mine == module on all four. Tie ordering cannot change the
    answer. THE DEFECT IS IN THE INPUT UNIVERSE, NOT THE SUMMATION.

## 4. Lanes
hotspots.py is NOT one of the six authored laws. It contains no ruling — no
decide(), no route(), no observation byte. Pure measurement and reporting,
invoked from cli.py:280, reachable only through `fluidfix hotspots`. No law lane
was reached and none could be.
Reached: bugfix_churn, coverage_to_reach, rank_hotspots on a real 1,377-commit
history, plus rank_hotspots' decl_only branch (visible in run1: include/box2d/
box2d.h with 10 defects ranks 19th, below files with 3, as documented).
Never reached: the `covered` path (cmd_hotspots --coverage). Needs an
instrumented Box2D build, not run. Every `covered` column reads ?, so every gap
was 1.0 and the ranking measured here is DEFECT DENSITY ALONE.

## 5. Potential
- SIGHT ranks files inside a repair; hotspots ranks files for a human. Same
  question at two timescales, no shared code today. Whether rename-aware extant
  churn would improve SIGHT's tier-1 ordering is UNMEASURED.
- The coverage lane would multiply density by a real gap instead of 1.0. Value
  UNMEASURED; without it the ? column carries no information.
- Fixing the extant-file filter costs ONE LINE and changes the headline from a
  57-file set with 3 testable files to a 16-file set with 16 testable files:
  5.3x more actionable targets for the same claim.

## 6. Defects
D1 OBSERVATION. coverage_to_reach counts historical paths that no longer exist
   while rank_hotspots in the same command drops them. On Box2D, 275 of 322 paths
   and 1,885 of 2,029 touches are gone; 54 of the 57 files the headline names
   cannot be tested. The summation over the byte it is given is provably correct.
D2 OBSERVATION. _SKIP does not exclude vendored trees under non-standard names
   (Box2D/glfw/), samples (HelloWorld/), or Contributions/. 11.8% of counted
   defect mass, including the file at the exact 60% boundary.
D3 OBSERVATION. bugfix_churn uses git log --name-only, no -M. One logical file is
   counted under every path it has held.
D4 WORDING. Three recorded values of the same measurement disagree:
   hotspots.py:15-21 (61 files / 201 / 30%), CHANGELOG.md:122-129 (58 files,
   "~30% of files"), README.md:154-155 (58 files, "not 60% of the engine"). The
   tool prints 18%, never 30%.
NO RULING DEFECT. No law ruled on anything in this target.

## 7. Verdict
The headline arithmetic reproduces — 57 files, not 58, and the printed 18%
exactly, the one-file gap explained by a knife-edge threshold (0.6003 at rank 57)
and six commits of history drift — but THE CLAIM IS NOT USABLE AS STATED: 54 of
those 57 files were deleted from Box2D in the v2-to-v3 rewrite, 11.8% of the
counted defect mass is vendored GLFW and demo code, and the number that survives
on files that exist today is 16 FILES (34% of the 47 that have ever broken and
still exist, 21% of the 75-file engine).
