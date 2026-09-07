# 25-pair-cost-model

## 1. Target

Measure single-edit candidate counts on the fixtures and on one Box2D file, compute the
corresponding pair counts, and determine where the PAIR law's CHEAP threshold should sit and who
decides it today.

## 2. Method

Read, in `/Users/kanchetidevieswar/neo/fluidfix/`:
`src/fluidfix/pair.py` (the law and its cost paragraph, lines 49-56), `docs/PAIR_LAW_PROMPT.md`,
`src/fluidfix/loop.py` (the candidate loop, lines 264-412), `src/fluidfix/acts.py` (`KINDS`,
`candidates()`, `_CAP_DEFAULT`), `src/fluidfix/lanes.py`, `src/fluidfix/guard.py` (lines 343-412,
where rank's CHEAP is measured), `src/fluidfix/coracle.py` (`_c_sources`, `find_candidate_files_c`,
`build_packet_c`, `_Coverage`, `cguard_once`), `src/fluidfix/localize.py`, `CHANGELOG.md`,
`tests/test_pair_law.py`, and `/private/tmp/.../scratchpad/ghpages/games.html` (the project's own
published games page, the only artifact that records the run behind the 1,063 figure).

Wrote, all in this directory, all rerunnable:

| script | what it does |
| --- | --- |
| `timeoutwrap.sh` | this machine has no coreutils `timeout`; `nice -n 15` + a perl `alarm`. Verified: `./timeoutwrap.sh 5 /bin/sh -c 'sleep 20'` -> `[timeoutwrap] TIMEOUT after 5s`, exit 124 |
| `count_candidates.py` | replicates `loop.repair()`'s candidate enumeration exactly (same `MechanicalObserver`, same `lanes.EMIT/ADVANCE` walk, same `acts.candidates()`, same NOPROGRESS skip, same SpanEdit bounds/anchor checks, same `tried` dedup key) but writes nothing and runs no suite. Returns the n an EXHAUSTED single-edit search would try |
| `measure_fixtures.py` | -> `fixtures_output.txt`. Builds the two shipped Python fixtures in temp dirs here, asks the real `build_packet()` for the real packet, counts |
| `measure_box2d.py` | -> `box2d_output.txt`. Box2D `src/contact_solver.c` in four regimes + a repo-wide per-file sweep |
| `gen_coverage.py` | -> `coverage.json`, `coverage_output.txt`. Builds the gcov tier on the copy with fluidfix's own `_Coverage` |
| `measure_candidate_cost.sh` | -> `candidate_cost_output.txt`. Re-measures seconds per candidate on Box2D (rebuild + suite run) |
| `covbuild_leak.py` | -> `covbuild_leak_output.txt`. Whether the gcov tier's own directory enters the candidate FILE set |
| `threshold.py` | -> `threshold_output.txt`. The CHEAP inequality solved for n, the law's behaviour with CHEAP clear, and the documented arithmetic against its sources |

Box2D was copied first (`cp -R` -> `box2d_copy/`, commit `dc67c40`); the shared clone was never
touched. Every run was one at a time, `nice -n 15`, under the wrapper. No `src/`, `tests/` or
`docs/` file was modified; no git state was changed.

## 3. Findings

### F1. The shipped Python fixtures: n = 5 and n = 110

```
$ ./timeoutwrap.sh 300 .venv/bin/python measure_fixtures.py      # fixtures_output.txt
    [packet mode=coverage truncated=False]
--- tests/test_guard.py BUGGY (count_above, strictness)
    anchor lines in packet   : 6
    SINGLE-EDIT CANDIDATES n : 5
    naive PAIR combinations C(n,2)           : 10
    by fault class : literal-off-by-one=2, strictness=1, flipped-comparison-direction=1, flipped-augmented-assign=1
    [packet mode=coverage truncated=True]
--- tests/test_span_edits.py budget fixture (806-line mod.py)
    anchor lines in packet   : 110
    SINGLE-EDIT CANDIDATES n : 110
    naive PAIR combinations C(n,2)           : 5995
    by fault class : flipped-boolean=109, literal-off-by-one=1
```

The 6-line `count_above` fixture the whole guard suite is built on has a **five**-candidate space.
The 806-line span fixture is packet-capped at 110 anchor lines and yields exactly 110 candidates —
one per line, 109 of them `flipped-boolean` on the `f_xxx = True` filler.

### F2. Box2D `src/contact_solver.c`: n = 438 as the body actually searches it, 463 with gcov, 5,041 uncapped

```
$ ./timeoutwrap.sh 300 .venv/bin/python measure_box2d.py         # box2d_output.txt
A. WHOLE FILE, UNCAPPED (no 110-line packet cap)
    anchor lines in packet   : 1769
    SINGLE-EDIT CANDIDATES n : 5041
    naive PAIR combinations C(n,2)           : 12703320
    by fault class : literal-off-by-one=3977, strictness=717, flipped-additive=249, ...
B. THE PACKET THE BODY ACTUALLY BUILDS (build_packet_c, no gcov)
    [packet mode=affinity truncated=True lines=109]
    SINGLE-EDIT CANDIDATES n : 438
    naive PAIR combinations C(n,2)           : 95703
C. THE PACKET WITH GCOV COVERAGE (638 executed lines)
    [packet mode=coverage truncated=True lines=110]
    SINGLE-EDIT CANDIDATES n : 463
    naive PAIR combinations C(n,2)           : 106953
```

The 110-line packet cap (`coracle.py:565 max_lines=110`) is what actually bounds n: it cuts the
file's 5,041-candidate space by 91%. Coverage changes *which* lines, barely the count (438 -> 463).
The 638 executed lines are full-suite coverage measured here by `gen_coverage.py`; the CHANGELOG's
608 is the failing-test-filtered figure, which I did not reproduce separately.

Repo-wide sweep, same cap, 74 production sources (`box2d_output.txt` section D):

```
    total single-edit candidates       : 16158     mean per file : 218.4
        592  src/manifold.c ... 438  src/contact_solver.c ... 395  src/sensor.c
    sum over the  38 richest files       : 13523   -> C(n,2) = 91,429,003
```

### F3. The 1,063 figure does not describe what `pair.py` says it describes, and I could not reproduce it

`pair.py:49-51` and `docs/PAIR_LAW_PROMPT.md:30-31` both say: *"Measured on Box2D's
`contact_solver.c`: a single-edit search tried 1,063 candidates ... at 3.5s per candidate."*
The number appears nowhere in `CHANGELOG.md`. Its only recorded source is the project's own
games page:

```
$ grep -n -A8 "1,063 candidates" .../ghpages/games.html | sed 's/<[^>]*>//g'
728:      38 files. 1,063 candidates. Refused.
729-      We taught a class whose signal matched
730-      ->anything - which is nearly every statement
731-      in C. Nothing could point anywhere, the search space exploded, and after
732-      30 minutes it refused. The class was correct. The shape was not.
```

So 1,063 is (a) a **38-file** total, not a `contact_solver.c` total; (b) produced by a **taught
class with an over-broad signal** that is not in the repo, not by the shipped vocabulary; and
(c) a **30-minute budget stop**, i.e. a truncated count, not an exhausted candidate space.
It is not re-measurable: the class that produced it was never committed. What I can measure is the
same shape with the shipped vocabulary — **13,523 candidates over the 38 richest files (F2)**,
12.7x the recorded 1,063, which is consistent with a run that stopped on a clock rather than on
exhaustion.

### F4. The 3.5s belongs to two *different*, successful runs, and does not reproduce on this machine

`threshold_output.txt` section 5:

```
  C(1063,2)                        = 564453   (docs say 564,453 -> reproduces)
  564453 x 3.5s                    = 1,975,586s = 22.87 days (docs say "about 23 days" -> reproduces)
  1063 x 3.5s                      = 3,720s = 62 min (docs:33 say "~1 hour")
  BUT the run that produced 1,063 is recorded as refusing after
  30 MINUTES (ghpages/games.html:728-732), i.e. 1800/1063 = 1.69s per candidate, not 3.5s.
  The 3.5s figure comes from DIFFERENT runs in CHANGELOG.md:
    1479s / 428 runs = 3.456s   (CHANGELOG.md:227)
     116s /  34 runs = 3.412s   (CHANGELOG.md:201)
```

Both documented figures reproduce **as arithmetic** and neither reproduces **as a measurement of
one run**: the candidate count comes from the 30-minute refusal and the per-candidate cost from
two byte-exact repairs (428 runs / 1479s and 34 runs / 116s).

Re-measured here on the Box2D copy — one candidate = touch `contact_solver.c`, `cmake --build -j8`,
run `build/bin/test`, exactly what `COracle.check()` does:

```
$ ./timeoutwrap.sh 300 ./measure_candidate_cost.sh 6            # candidate_cost_output.txt
load before: load averages: 13.64 13.01 11.05
  candidate 1: 11.655s ... candidate 6: 11.624s
mean per candidate: 11.401s over 6
  rep 1: build=0.804s  test=10.507s  total=11.310s
  rep 2: build=0.867s  test=9.597s   total=10.463s
  rep 3: build=0.624s  test=9.954s   total=10.579s
```

**3.5s does not reproduce here; ~10.8s does** (0.77s build + 10.0s suite). The confound is stated
plainly: 50 agents share this machine and the load average was 13-23 on 12 cores throughout, so I
cannot separate machine contention from build configuration, and I am **not** claiming the recorded
3.5s was wrong. The decomposition is the durable part: the build is 7% of a candidate and the suite
is 93%, so a candidate that fails to compile costs ~0.8s and a candidate that compiles costs ~11s.

### F5. Nothing in the body measures PAIR's CHEAP — or any PAIR bit

```
$ grep -rn "observe_bits\|from .pair\|import pair" src/fluidfix/*.py
src/fluidfix/cli.py:527:    from .pair import pair_law as _pair
src/fluidfix/guard.py:216:    from .sight import observe_bits as _sight_bits, sight as _sight
src/fluidfix/guard.py:356:    from .rank import observe_bits, rank as _rank
src/fluidfix/pair.py:150:def observe_bits(...)
```

`pair.observe_bits` is imported by nothing. `pair_law` is imported once, by `cli.py:527`, which is
`selfcheck` feeding it synthetic bytes. The docstring's "Fused, NOT actuated yet" is accurate: the
law's input byte is never constructed from a real search.

### F6. With CHEAP unmeasurable, PAIR is the one ruling the law can never reach

```
$ ./timeoutwrap.sh 120 .venv/bin/python threshold.py             # threshold_output.txt
  inputs whose ruling is PAIR                  : 2/256  ['0b11011', '0b111011']
  ... every one has CHEAP set                  : True
  ... any of them ruling PAIR (CHEAP clear)    : False
  rulings reachable with CHEAP forced 0        : {'SINGLE': 16, 'TEACH': 3, 'WIDEN': 2,
      'PARTITION': 8, 'BUDGET': 3, 'REFUSE': 64, 'CAPPED': 32}
  rulings reachable with CHEAP free            : {'SINGLE': 32, 'TEACH': 5, 'WIDEN': 4,
      'PARTITION': 16, 'PAIR': 2, 'BUDGET': 3, 'REFUSE': 130, 'CAPPED': 64}
```

CHEAP halves the input space; the only *ruling* it gates is PAIR. Seven of the eight acts survive
CHEAP=0. So an unmeasured CHEAP does not silence the law — it silences exactly the quadratic lane,
which is the conservative failure and matches R5.

### F7. The threshold is an inequality, and its answer is small

CHEAP means `C(n,2) * t <= B`, so `n* = largest n with n(n-1)/2 * t <= B`:

```
  budget                               0.20     3.46     3.41    18.80    10.80   <- s/candidate
  --escalate-budget default (600s)       77       19       19        8       11
  --suite-timeout default (300s)         55       13       13        6        7
  the recorded cguard run (3600s)       190       46       46       20       26
  one working day (28800s)              537      129      130       55       73
  one week (604800s)                   2459      592      595      254      335
```

Against the measured n (at the 600s `--escalate-budget` default):

```
    n=     5 vs n*=  77  ->  CHEAP       tests/test_guard.py count_above fixture
    n=   110 vs n*=  77  ->  NOT cheap   tests/test_span_edits.py budget fixture
    n=   438 vs n*=  19  ->  NOT cheap   Box2D contact_solver.c, packet-capped
    n=   463 vs n*=  11  ->  NOT cheap   Box2D contact_solver.c, coverage-anchored
    n= 13523 vs n*=  19  ->  NOT cheap   Box2D 38 richest files
```

**Where the threshold should sit.** On the C path, at the body's own 110-line packet cap and the
re-measured 10.8s/candidate, `n* = 11` for one escalation budget, `26` for the recorded 3600s run,
`73` for a working day, `335` for a week. The measured per-file n on Box2D is 218 on average and
438-592 on the biggest files. So **CHEAP is false for every real C file the body searches today, at
every budget short of about a week** — and that is not a tuning problem, it is the 110-line cap:
a packet capped at 110 lines still admits ~440 candidates, and `C(440,2)` is 96,000 suite runs.
Making CHEAP ever true on the C path requires n <= ~26, i.e. a packet of roughly **7 anchor lines**
at the measured 4.2 candidates/line — well over an order of magnitude below the current cap. On the
Python path the threshold is reachable: `n* = 77` at 0.2s/candidate and 600s, and the guard fixture's
n = 5 sits comfortably under it.

### F8. Who decides it today: hardcoded constants in the body, and for PAIR, nobody

No law owns any of these. Every one is a literal in the body that changes an outcome:

| constant | site | what it bounds |
| --- | --- | --- |
| `_CAP_DEFAULT = 32` | `acts.py:376` (env `FLUIDFIX_CANDIDATE_CAP`) | candidates one act may propose for one line |
| `max_lines = 110` | `coracle.py:565`, `localize.py:89` | anchor lines in a packet — the dominant term in n (F2) |
| `limit = 5` / `limit = 3` | `coracle.py:494`, `guard.py:119` | candidate files searched |
| `escalate_budget = 600` | `guard.py:443` | B, the budget side of the inequality |
| `0 < n < 8` | `guard.py:403` | the **ranking** law's CHEAP bit — a different law's bit, and the only "cheap" threshold anything in the body actually computes |

`guard.py:399-404` is worth quoting because it is the closest thing to an existing answer:

```python
        try:                       # CHEAP: few candidates, no suite runs
            from .acts import act_for, candidates
            n = sum(len(candidates(body.strip(), act_for(k), obs))
                    for k in (obs.kinds or [])[:2])
            cheap = 0 < n < 8
```

That is the right *measurement* — it counts candidates with no suite runs, exactly as PAIR's CHEAP
would need — attached to the wrong law, capped at the first two kinds, and with its threshold (8)
written as a literal rather than derived from a budget. Extending it to a whole packet and
comparing `C(n,2)*t` against the remaining deadline is a plumbing change, not a new decision.

### F9. Once the gcov tier has run, its own directory enters the candidate FILE set

`_c_sources(root, build_dir)` (`coracle.py:470-491`) skips only the *fast* build dir. `_Coverage`'s
instrumented tree is hardcoded to `covbuild` (`coracle.py:333`) and is not in the skip set.

```
$ ./timeoutwrap.sh 120 .venv/bin/python covbuild_leak.py         # covbuild_leak_output.txt
total basenames in the candidate-file set : 206
...resolved into covbuild/                : 132
...by covbuild subdirectory               : {'CMakeFiles': 4, '_deps': 128}
real src/ basenames SHADOWED by a covbuild path: 0 []

no-evidence fallback (coracle.py:560) = 5 biggest sources, as it is on a SECOND pass:
      958231  covbuild/_deps/imgui-src/imgui.cpp
      581901  covbuild/_deps/imgui-src/imgui_demo.cpp
      541366  covbuild/_deps/imgui-src/imgui_widgets.cpp
      424209  covbuild/_deps/imgui-src/imgui.h
      377275  covbuild/_deps/imgui-src/imgui_draw.cpp
the same fallback on a FIRST pass (no covbuild/ yet):
      110583  src/physics_world.c
       93422  src/recording_replay.c
       86534  src/contact_solver.c
       76531  include/box2d/box2d.h
       68845  src/solver.c
```

The skip set contains `deps`, `extern`, `samples` — but the directory CMake creates is `_deps`, so
glfw/imgui/implot/nfd sources walk straight in. The candidate-file set goes 74 -> 206 files and the
candidate space 16,158 -> 42,609 (2.64x) purely from fluidfix's own instrumentation tree.
The first-pass listing also **reproduces the CHANGELOG's recorded observation exactly**: with no
frame and no name affinity, `src/contact_solver.c` lands **3rd by size** (`coracle.py:319`: *"the
defect file landed 3rd"*).

Bounded honestly: on a first pass `covbuild/` does not exist when `find_candidate_files_c` is called
(`cguard_once` calls it before `oracle.coverage()`), and on a later pass the credible-coverage
filter (`coracle.py:740-745`) drops files the failure never executed, which removes the imgui
files. The exposure is the `credible = False` path, where no dropping happens at all.

## 4. Lanes

**Reached by this work.** All eight PAIR acts were exercised over all 256 inputs by `threshold.py`
section 1, and the specific bytes for the recorded Box2D situation in section 2:

```
  byte=  1 EXHAUSTED                 ->  3 TEACH
  byte= 33 EXHAUSTED|TAUGHT          ->  4 BUDGET
  byte=160 TAUGHT|CAPPED             ->  5 CAPPED
  byte=162 PARTIAL|TAUGHT|CAPPED     ->  5 CAPPED
```

**Never reached, and cannot be.** PAIR (act 1, 2 of 256 inputs) — F5/F6: it requires CHEAP, and
CHEAP is never measured, so the byte handed to the law can never have bit 4 set. Nothing else in the
law is blocked by this: seven acts remain reachable with CHEAP forced to 0 (F6).

**Never reached because the byte is never built at all.** Every PAIR lane, in practice. `pair_law`
is called only from `selfcheck`. The observation that would make PAIR reachable is a real byte
assembled at the end of a completed single-edit search, and F8 shows the body already computes the
one hard piece of it (`guard.py:399-404` counts candidates without running a suite).

**A lane the law has that the body never consults.** CAPPED (act 5, 64 of 256 inputs). The recorded
Box2D situation is a 30-minute budget stop (F3), which is CAPPED, not EXHAUSTED — and `pair_law`
rules `CAPPED` on it, correctly, without needing CHEAP at all. `docs/PAIR_LAW_PROMPT.md:93` and
`pair.py:50` both frame that run as EXHAUSTED.

## 5. Potential

- **Measuring CHEAP costs no suite runs.** `count_candidates.py` computed n for a 2,500-line C file
  and for 74 Box2D sources in seconds, using only the observer and the appliers — the same
  technique already in `guard.py:399-404`. Measured: n = 438 (contact_solver.c, affinity packet),
  463 (coverage-anchored), 16,158 (whole repo). The cost of the measurement is ~0 suite runs; the
  value is that a search could report `C(n,2)*t` before starting instead of after a 30-minute clock
  stop.
- **What CHEAP would rule today, if measured.** Never true on the C path below a week-long budget
  (F7): `n* = 11` at 600s, `26` at 3600s, `73` at a working day, against a measured per-file n of
  218 mean / 592 max. So the actuation worth building first is not PAIR — it is honest
  BUDGET/CAPPED reporting, which needs EXHAUSTED and CAPPED only.
- **The reachability price of the 110-line cap.** Lowering `max_lines` from 110 to ~7 would make
  CHEAP true on a C file at a 3600s budget. What that would cost in localisation accuracy is
  **unmeasured** here (agent 17's target).
- **Value of fixing F9.** 2.64x fewer candidate files on any pass after the gcov tier has run
  (16,158 measured clean vs 42,609 with the leak). Whether that ever changes an outcome in practice
  is **unmeasured** — the credible-coverage filter masks it on the paths I inspected.
- **Per-candidate cost as a bit.** The law has no way to know t. Measured here: 0.77s build +
  10.0s suite on Box2D under load; 0.2s on the Python fixtures (agent 23's figure, not re-measured
  by me). Whether t belongs in the byte or is the body's to fold into CHEAP is a design question I
  did not resolve.

## 6. Defects

1. **WORDING — `pair.py:49-51` and `docs/PAIR_LAW_PROMPT.md:30-31` attribute two numbers from three
   different runs to one measurement.** Evidence F3, F4. "Measured on Box2D's `contact_solver.c`:
   a single-edit search tried 1,063 candidates before refusing, at 3.5s per candidate" fuses a
   38-file, over-broadly-taught, 30-minute budget stop (games.html:728-732) with the per-candidate
   cost of two byte-exact repairs (CHANGELOG.md:201, 227). The self-inconsistency is visible without
   any measurement: 1,063 x 3.5s = 62 minutes, and the run is recorded as refusing after 30.
   Not a wrong ruling — the *conclusion* (a pair search over that space is unaffordable) is
   understated if anything: the shipped vocabulary on those 38 files measures 13,523 candidates
   (F2), 91.4M pairs, 3,657 days at 3.46s.
2. **WORDING — `docs/PAIR_LAW_PROMPT.md:93` states the Box2D incident's byte as EXHAUSTED when the
   run it cites was CAPPED.** Evidence F3, and section 2 of `threshold_output.txt`: a 30-minute
   budget stop sets CAPPED, and `pair_law(TAUGHT|CAPPED) = 5 CAPPED`. The listed byte also omits
   TAUGHT, without which `pair_law(EXHAUSTED) = 3 TEACH`, not the BUDGET the incident requires;
   `tests/test_pair_law.py:97` pins `EXH|TAU -> BUDGET`, so the test is right and the prose is
   short a bit. The ruling is correct on either byte — both refuse a pair search.
3. **OBSERVATION — `_c_sources` does not exclude the gcov tier's own directory.** Evidence F9.
   `coracle.py:470-491`'s skip set omits `covbuild` (hardcoded at `coracle.py:333`) and `_deps`
   (CMake's FetchContent directory; the set has `deps`). Measured: 132 of 206 candidate basenames
   resolve into `covbuild/`, and the no-evidence size fallback would return five imgui files instead
   of five Box2D sources. This is a mismeasured observation — the candidate-file set — not a wrong
   ruling, and it is bounded by the credible-coverage filter on the paths I inspected.

No wrong ruling found. On every byte I put to it, `pair_law` ruled correctly on the situation it was
given.

## 7. Verdict

The PAIR law's CHEAP threshold is `n <= n*` where `n* = 11` at the 600s escalation budget, `26` at
the recorded 3600s Box2D budget and `73` at a working day (re-measured 10.8s/candidate on this
loaded machine); measured single-edit spaces are 5 and 110 on the shipped Python fixtures and 438
(affinity) / 463 (coverage-anchored) / 5,041 (uncapped) on Box2D `contact_solver.c`, so CHEAP is
false for every real C file today — and nobody decides it, because `pair.observe_bits` is called
from nothing in `src/`, leaving PAIR the one ruling of eight the law can never reach, while the
documented 1,063-at-3.5s that anchors the whole cost paragraph turns out to fuse three different
runs and does not re-measure.
