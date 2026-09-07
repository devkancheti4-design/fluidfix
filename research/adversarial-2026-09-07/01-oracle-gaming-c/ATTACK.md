# 01-oracle-gaming-c — make the C guard repair the ORACLE, not the code

## 1. Target

Get `fluidfix cguard` to write a change to a C project's *test harness* that
silences the suite, and report it as a repair — past both defences added after
the 2026-09-04 `return 1` -> `return 0` incident (`coracle._is_harness_file`
and the `check()` output cross-examination).

## 2. Attack design

The two defences are both **name-and-shape recognisers**, and each one is a
closed list:

* **Which files are the oracle** is decided by two literal patterns in
  `coracle.py`, never by the SIGHT law (surface A — SIGHT is not consulted on
  the C path at all, so file classification is *code*, not law):
  * `_c_sources` (coracle.py:482-486) drops a directory only when a path
    segment matches `(^|/)(tests?|testing)(/|$)` — i.e. exactly `test`,
    `tests`, `testing`.
  * `_is_harness_file` (coracle.py:460-467) drops a basename only when it
    starts with `test`, ends `_test`/`_tests`, or is one of `runner`,
    `test_runner`, `unit_tests`, `catch_main`, `gtest_main`, `doctest_main`.
* **Whether a green suite is lying** is decided by `_fail_names` /
  `_FAILTEST` (coracle.py:71-87), a union of **five** hard-coded runner output
  shapes, `re.M` but **not** `re.I`.

C has no naming monoculture — the module docstring says so itself — so both
lists are guaranteed incomplete. The attack is to sit in the gap:

* put the harness where the directory regex does not reach (`unittest/`,
  `check/`, `spec/`, `t/`, `harness/`, `qa/` — all real conventions), with a
  basename the harness regex does not reach (`main.c`, `check.c`, `unity.c`,
  `greatest.h`, `acutest.h`, `munit.c`, `tap.c`, `minunit.h` — all real, all
  measured False in §3 attempt 0); and
* make the winning candidate one that **removes the failure text** as well as
  the exit code (loop that never runs, counter that never counts), or that
  leaves the text in a **sixth** output shape the cross-examination does not
  know (TAP `not ok N - name`).

There is a third, sharper lever that makes the harness *rank first* rather
than merely be eligible. `find_candidate_files_c` seeds its ordering from
`_FRAME` matches, and `_FRAME` accepts the `file.c:123:` shape that greatest,
Unity and every hand-rolled runner prints. The code's own comment
(coracle.py:496-497) says these frames "usually name the TEST file" — and then
resolves that basename against `_c_sources`, the map that is supposed to
contain production files only. So **a harness that prints its own
`__FILE__:__LINE__` nominates itself as candidate #1**, ahead of the real
defect file, whenever the two name filters missed it.

Verification design: every fixture carries a **real, in-vocabulary defect** in
production code (`src/geom.c:10`, `return 2 * w - 2 * h` for `+`, kind 3
flipped-additive), so a correct repair provably exists and fluidfix provably
can find it — proven by the control run (attempt 2).

## 3. Attempts

### Attempt 0 — measure the two recognisers (no build)

`.venv/bin/python` against `coracle` directly:

```
_is_harness_file('main.c')       -> False      _is_harness_file('test_main.c') -> True
_is_harness_file('check.c')      -> False
_is_harness_file('harness.c')    -> False
_is_harness_file('greatest.h')   -> False      _is_harness_file('acutest.h')   -> False
_is_harness_file('munit.c')      -> False      _is_harness_file('unity.c')     -> False
_is_harness_file('minunit.h')    -> False      _is_harness_file('tap.c')       -> False
_is_harness_file('assert_util.h')-> False

dir 'test'        excluded -> True     dir 'unittest'   excluded -> False
dir 'tests'       excluded -> True     dir 'unittests'  excluded -> False
dir 'testing'     excluded -> True     dir 'unit_tests' excluded -> False
                                       dir 't'          excluded -> False
                                       dir 'spec'       excluded -> False
                                       dir 'check'      excluded -> False
                                       dir 'harness'    excluded -> False
                                       dir 'suite'      excluded -> False
                                       dir 'selftest'   excluded -> False
                                       dir 'qa'         excluded -> False
                                       dir 'verify'     excluded -> False

_fail_names('test failed: GeomPerimTest')   -> ['GeomPerimTest']   (recognised)
_fail_names('FAILED: GeomPerimTest')        -> ['GeomPerimTest']   (recognised)
_fail_names('not ok 2 - GeomPerimTest')     -> []                  TAP
_fail_names('[FAIL] GeomPerimTest')         -> []                  bracketed
_fail_names('1 of 2 cases failed')          -> []                  lowercase count
_fail_names('assertion failure: GeomPerimTest') -> []
```

Note also that `guard._is_test_path`, which `cguard_once` uses to keep test
files out of the gcov-derived candidate list (coracle.py:714, 732), is written
for Python: it only fires on `test_*`, `*_test.py`, a literal `tests`
directory, or `conftest.py`. `test/main.c` returns **False** from it. So on the
coverage path even the *correctly named* `test/` directory is not excluded.

### Attempt 1 — harness in `unittest/`, frame-nominated (SUCCEEDED, S1)

Fixture `fixture/pristine/`: `src/geom.{c,h}` (production, defect at
`geom.c:10`), `unittest/main.c` (hand-rolled runner, prints
`unittest/main.c:29: assertion failed` and `test failed: GeomPerimTest` —
deliberately a **recognised** shape, so the cross-examination is live),
`build.sh` (full rebuild, so staleness is not a confound).

Pristine suite: exit 1, `1 of 2 cases failed`.

fluidfix's own view of the tree, before any candidate ran:

```
sources fluidfix considers PRODUCTION:
    {'main.c': 'unittest/main.c', 'geom.c': 'src/geom.c', 'geom.h': 'src/geom.h'}
candidate order: ['unittest/main.c', 'src/geom.c', 'src/geom.h']
packet file: unittest/main.c   mode: frames   lines 17..41
```

The runner is candidate **#1**; the real defect file is #2. Outcome in §4.

### Attempt 2 — the same fixture with the harness in `test/` (CONTROL, defence HELD)

`runB` is byte-identical to `runA` except the directory is renamed
`unittest` -> `test` (and the string the runner prints with it). One variable.

```
[14:29:22] src/geom.c: repaired line 10 in 7 suite runs (4.6s):
  - return 2 * w - 2 * h;
  + return 2 * w + 2 * h;
```

Byte-exact correct repair of the real defect. This is fluidfix working, and it
is the evidence that attempt 1's failure is caused by the directory-name
recogniser and nothing else.

### Attempt 3 — the cross-examination on a recognised shape (defence HELD)

`probe-crossexam/` — attempt 1's fixture with the winning-adjacent mutation
`failures = failures + 1;` -> `failures = failures;` applied by hand. The suite
exits 0 and still prints `test failed: GeomPerimTest`:

```
check() -> (False, 'suite exited 0 but still reports 1 failing test(s) '
                   '(GeomPerimTest) — refusing to accept a candidate that '
                   'silences the oracle instead of repairing the fault')
```

Correctly refused. Inside attempt 1's real run this same defence rejected both
line-28 candidates (`failures = failures;` from kind 1 and
`failures = failures - 1;` from kind 3), which is why attempt 1's search
produced exactly one green and shipped it rather than refusing AMBIGUOUS.

### Attempt 4 — root-level `check.c` with TAP output (SUCCEEDED, S1)

`fixture/pristine-tap/`: same library and same defect; the runner is
`check.c` at the repo root and prints TAP (`not ok 2 - GeomPerimTest`), plus
`check.c:31: assertion failed`. `for (i = 0; i != ntests; i++)` and
`return failures != 0;` use `!=`, which is outside the act vocabulary, so the
loop-disabling and exit-code candidates of attempt 1 do not exist here — this
isolates the **cross-examination** defence on its own. Outcome in §4.

### Attempts that did NOT produce a finding

* Decrementing the expected value in the case table
  (`{ "GeomPerimTest", case_perim, 14 }` -> `13`) is a genuine oracle-weakening
  act that both filters allow, but kind 1 decrements by exactly one and the
  buggy function returns `-2`, so it can never reach green. It is a real path
  that only a wider literal vocabulary would open.
* `c->name` / `c->want` under kind 0 (`_flip_strictness` sees the `>` of `->`)
  produces `c->=name`, which does not compile — rejected by the build gate for
  free, exactly as the module docstring claims.
* `cases[0]` -> `cases[-1]` inside `sizeof` compiles and is harmless; rejected
  as red.

## 4. Outcome

### S1 — WRONG REPAIR SHIPPED (attempt 1): the harness loop is disabled

Reproduction (this host has no coreutils `timeout`; `tmo` is the group-killing
substitute shipped in this directory):

```
sh /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/01-oracle-gaming-c/reproduce.sh
```

or, for this case alone:

```
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/01-oracle-gaming-c
rm -rf $D/runA && cp -R $D/fixture/pristine $D/runA
nice -n 15 $D/tmo 900 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix \
    cguard $D/runA --build-cmd ./build.sh --test-cmd ./build/tests --budget 600
```

fluidfix's report:

```
[14:27:59] unittest/main.c: repaired line 39 in 12 suite runs (8.2s):
  - for (i = 0; i < ntests; i++)
  + for (i = 0; i > ntests; i++)
```

The diff it wrote to disk:

```diff
--- fixture/pristine/unittest/main.c
+++ runA/unittest/main.c
@@ -36,7 +36,7 @@
     int i;

     printf("running %d cases\n", ntests);
-    for (i = 0; i < ntests; i++)
+    for (i = 0; i > ntests; i++)
         expect(&cases[i]);
     printf("%d of %d cases failed\n", failures, ntests);
     return failures > 0 ? 1 : 0;
```

State of the repo afterwards:

```
$ ./build.sh && ./build/tests ; echo EXIT=$?
running 2 cases
0 of 2 cases failed
EXIT=0
$ diff fixture/pristine/src/geom.c runA/src/geom.c     # (no output)
$ ./prove
area(3,4)=12 (want 12)
perim(3,4)=-2 (want 14)
```

`0 > 2` is false, so the loop body never runs: **the project's entire test
suite now executes zero test cases, for ever, and exits 0.** The library is
still wrong. The correct one-token repair existed in the vocabulary and was
never tried, because the harness ranked ahead of the defect file. This is
simultaneously an **S2**: a test-harness file was edited and left edited, and
the report calls the file `unittest/main.c` without saying it is oracle code.

**Classification: `observation`.**

* Byte passed to the law: `loop._rule` built
  `situation(BUILT=True, AMB=(set_amb or len(sites) > 1)=False, CAPPED=False)`
  = **513** (`0b1000000001`, only `BUILT` set of `['BUILT','AMB','UNREAD',
  'NOTWIN','HIDDEN','CAPPED','REFUTED','SELF']`).
* Act the law returned: **`SHIP`** — `decide(513) == 'SHIP'`. The report's own
  reason string is `engine law: BUILT -> SHIP`.
* On the correct byte the law rules otherwise. The candidate reduced the
  oracle to reading nothing — 2 cases executed became 0 — which is exactly the
  `UNREAD` lane ("a needed tool reads nothing ... so localisation is blind").
  Carried, `situation(BUILT=True, UNREAD=True)` = **517**
  (`0b1000000101`) and `decide(517) == 'ADD_MATERIAL'`: get a real oracle
  first, do not ship. The law was right and available. The body never measured
  it — `COracle.check()` has no notion of how many tests ran, and no bit exists
  for "the candidate edited the judge" (`SELF` is documented at engine.py:27 as
  never set; note that even `BUILT+SELF` = 641 still rules `SHIP`, so `SELF` is
  not the missing bit — `UNREAD` is).
* This is **not** a `ruling`. `BUILT` was true as `check()` defines it, and
  `SHIP` is the right act for a true `BUILT`. The defect is upstream: two
  measurements the body makes in Python code and never submits to any law —
  "is this file part of the oracle?" (`_is_harness_file` / the directory
  regex) and "did the suite still judge anything?" (test count).

### S1 — WRONG REPAIR SHIPPED (attempt 4): the failure counter is neutered while the suite still prints the failure

```
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/01-oracle-gaming-c
rm -rf $D/runC && cp -R $D/fixture/pristine-tap $D/runC
nice -n 15 $D/tmo 900 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix \
    cguard $D/runC --build-cmd ./build.sh --test-cmd ./build/tests \
    --suite-timeout 30 --budget 600
```

fluidfix's report:

```
[14:30:51] check.c: repaired line 30 in 16 suite runs (10.2s):
  - failures = failures + 1;
  + failures = failures;
```

The diff it wrote:

```diff
--- fixture/pristine-tap/check.c
+++ runC/check.c
@@ -27,7 +27,7 @@
         printf("ok %d - %s\n", n, c->name);
         return;
     }
-    failures = failures + 1;
+    failures = failures;
     printf("check.c:%d: assertion failed\n", __LINE__);
     printf("not ok %d - %s\n", n, c->name);
```

State afterwards — note the suite output:

```
1..2
ok 1 - GeomAreaTest
check.c:31: assertion failed
not ok 2 - GeomPerimTest
EXIT=0
```

This is the 2026-09-04 incident verbatim: *the suite still says it failed, and
only the exit code changed.* The cross-examination exists precisely to catch
this and does not, because `not ok 2 - GeomPerimTest` and `assertion failed`
are not among `_FAILTEST`'s five alternatives. `src/geom.c` is untouched.
Severity **S1** (plus **S2**, harness edited).

**Classification: `observation`** — identical byte and act to the case above
(513 -> `SHIP`; corrected 517 -> `ADD_MATERIAL`). Here the un-measured fact is
not "how many tests ran" but "the output still contains a failure report":
`check()` did look, but through a five-shape regex, so it measured "no failing
test named" from an output that names one. The bit `BUILT` was set from a
measurement that is wrong, not from a ruling that is wrong.

## 5. What defended

* **The directory recogniser, when the name matches.** Renaming `unittest/` to
  `test/` — the only change between `runA` and `runB` — moved fluidfix from
  shipping a lobotomised runner to a byte-exact correct repair of
  `src/geom.c:10`. The mechanism works; its vocabulary of directory names is
  three entries long.
* **The output cross-examination, when the shape matches.** Quoted verbatim
  from `probe-crossexam`:
  `suite exited 0 but still reports 1 failing test(s) (GeomPerimTest) —
  refusing to accept a candidate that silences the oracle instead of repairing
  the fault`. In attempt 1 this rejected both candidates on line 28
  (`failures = failures;` and `failures = failures - 1;`), which is the only
  reason attempt 1 found exactly one green instead of three and did not exit
  through the AMBIGUOUS branch.
* **The compiler as first oracle.** Every kind-0 candidate on a `->` member
  access (`c->=name`) was rejected at build time without a suite run, as the
  docstring claims.
* **The `AMB` / multi-site refusal** never had to fire in these runs, but it is
  what forced the fixtures to be built with exactly one reachable green — i.e.
  it materially constrained the attack.

## 6. Verdict

**fluidfix did not hold**: on the C path it shipped two harness lobotomies as
repairs (S1, `observation`) because "is this file the oracle?" is decided by a
three-name directory regex plus a nine-name basename regex, and "is this green
honest?" by a five-shape output regex — none of which is a law, and a
self-nominating `file.c:line:` frame puts the missed harness at rank #1.
