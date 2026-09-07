# raw `fluidfix estimate` runs

4/16 got a number; 12/16 refused.


## 01-py-flat-green  (NUMBER, exit 0, 1.1s wall)

missing observation: -

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/01-py-flat-green --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  2 passed in 0.07s
  suite runtime: 0.56s  (+~0.5s pytest startup per run)

EXPECTED REPAIR TIME on this repo
  typical in-vocabulary defect (2-10 suite runs):  2.1s - 11s
  harder localisation (up to 80 runs):             ~85s

  Fast suite: repairs will land in seconds. Ideal for the GitHub Action
  on every push.

  The arithmetic: time ~= runs x (suite time + startup). Nothing else
  in fluidfix costs measurable wall clock — the kernels decide in
  nanoseconds; your tests are the entire bill.
```

## 02-py-flat-red  (NUMBER, exit 0, 0.64s wall)

missing observation: -

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/02-py-flat-red --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  1 failed, 1 passed in 0.02s
  suite runtime: 0.31s  (+~0.5s pytest startup per run)

EXPECTED REPAIR TIME on this repo
  typical in-vocabulary defect (2-10 suite runs):  1.6s - 8s
  harder localisation (up to 80 runs):             ~65s

  Fast suite: repairs will land in seconds. Ideal for the GitHub Action
  on every push.

  The arithmetic: time ~= runs x (suite time + startup). Nothing else
  in fluidfix costs measurable wall clock — the kernels decide in
  nanoseconds; your tests are the entire bill.

  NOTE: your suite is currently RED, so this timing includes failing
  tests. fluidfix only acts on a red suite, so this is the realistic
  number.
```

## 03-py-src-layout-uninstalled  (NUMBER, exit 0, 0.65s wall)

missing observation: -

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/03-py-src-layout-uninstalled --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  1 error in 0.17s
  suite runtime: 0.46s  (+~0.5s pytest startup per run)

EXPECTED REPAIR TIME on this repo
  typical in-vocabulary defect (2-10 suite runs):  1.9s - 10s
  harder localisation (up to 80 runs):             ~77s

  Fast suite: repairs will land in seconds. Ideal for the GitHub Action
  on every push.

  The arithmetic: time ~= runs x (suite time + startup). Nothing else
  in fluidfix costs measurable wall clock — the kernels decide in
  nanoseconds; your tests are the entire bill.

  NOTE: your suite is currently RED, so this timing includes failing
  tests. fluidfix only acts on a red suite, so this is the realistic
  number.
```

## 04-py-no-tests  (REFUSAL, exit 1, 0.83s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/04-py-no-tests --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/04-py-no-tests with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.04s
```

## 05-py-unittest-nonglob  (REFUSAL, exit 1, 0.72s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/05-py-unittest-nonglob --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/05-py-unittest-nonglob with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.02s
```

## 06-py-all-skipped  (REFUSAL, exit 1, 0.58s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/06-py-all-skipped --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/06-py-all-skipped with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
1 skipped in 0.02s
```

## 07-py-bad-addopts  (REFUSAL, exit 1, 0.49s wall)

missing observation: a pytest invocation this repo's config accepts

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/07-py-bad-addopts --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest usage/configuration error (exit 4) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/07-py-bad-addopts with no extra args
--- last output ---
ERROR: usage: python -m pytest [options] [file_or_dir] [file_or_dir] [...]
python -m pytest: error: unrecognized arguments: --nonexistent-option
  inifile: /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/07-py-bad-addopts/pytest.ini
  rootdir: /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/07-py-bad-addopts
```

## 08-py-slow-suite  (REFUSAL, exit 1, 5.2s wall)

missing observation: suite runtime (suite exceeded --suite-timeout)

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/08-py-slow-suite --python .venv/bin/python --suite-timeout 5
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  your suite did not finish within --suite-timeout (5s).

EXPECTED REPAIR TIME on this repo
  unmeasurable here, and that IS the answer: at >5s per run even a
  2-run repair costs over 0 minutes. Guard a fast subset instead --
  pass test paths after the root, or raise --suite-timeout if the suite
  really is that long and you accept the cost.
```

## 09-js-node  (REFUSAL, exit 1, 0.46s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/09-js-node --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/09-js-node with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.01s
```

## 10-c-cmake  (REFUSAL, exit 1, 0.39s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/10-c-cmake --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/10-c-cmake with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.01s
```

## 11-java-maven  (REFUSAL, exit 1, 0.39s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/11-java-maven --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/11-java-maven with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.01s
```

## 12-py-midsize  (NUMBER, exit 0, 0.38s wall)

missing observation: -

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/12-py-midsize --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  1 failed, 42 passed in 0.03s
  suite runtime: 0.22s  (+~0.5s pytest startup per run)

EXPECTED REPAIR TIME on this repo
  typical in-vocabulary defect (2-10 suite runs):  1.4s - 7s
  harder localisation (up to 80 runs):             ~58s

  Fast suite: repairs will land in seconds. Ideal for the GitHub Action
  on every push.

  The arithmetic: time ~= runs x (suite time + startup). Nothing else
  in fluidfix costs measurable wall clock — the kernels decide in
  nanoseconds; your tests are the entire bill.

  NOTE: your suite is currently RED, so this timing includes failing
  tests. fluidfix only acts on a red suite, so this is the realistic
  number.
```

## 13-py-all-skipped-runtime  (REFUSAL, exit 1, 0.36s wall)

missing observation: a summary line naming passed/failed/error counts

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/13-py-all-skipped-runtime --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  pytest ran but reported no test results, so this repo has nothing
  for fluidfix to be judged by yet. Run `fluidfix init` to generate a
  starter smoke suite, then estimate again.
```

## 01-py-flat-green  (REFUSAL, exit 1, 0.19s wall)

missing observation: a pytest importable by the target interpreter

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/01-py-flat-green --python .venv/bin/python --python /usr/bin/python3
timing your suite (one run, /usr/bin/python3)...
  the suite did not run, so there is nothing to time.

the interpreter running your suite has no pytest, so no test has been judged.
  interpreter: /usr/bin/python3
  fix: point fluidfix at your project's interpreter --
       fluidfix ... --python /path/to/venv/bin/python
  (or install pytest into the interpreter above)
```

## 15-go-module  (REFUSAL, exit 1, 0.36s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/15-go-module --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/15-go-module with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.01s
```

## 16-rust-crate  (REFUSAL, exit 1, 0.37s wall)

missing observation: any collectable pytest test in this root

```
$ fluidfix estimate /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/16-rust-crate --python .venv/bin/python 
timing your suite (one run, /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python)...
  the suite did not run, so there is nothing to time.

pytest collected NO TESTS (exit 5) while running pytest in /Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/48-estimate-potential/repos/16-rust-crate with no extra args — the suite collected nothing, so nothing can be judged. Common causes: wrong --python (project deps missing), a testpaths/plugin interaction (SQLAlchemy collects 0 unless `-p no:cacheprovider` is passed), or no tests in this root.
--- last output ---
no tests ran in 0.01s
```
