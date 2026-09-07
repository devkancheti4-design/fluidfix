# 20 adversarial targets. One per agent. NN-slug is your directory name.

## Attacking the oracle (the suite is fluidfix's only source of truth)
01-oracle-gaming-c: make the C/C++ guard "repair" by weakening the ORACLE rather than the code — edit a runner, a CMake target, an assert macro, a test helper the harness filter does not classify as a test. coracle.py has `_is_harness_file` and an output cross-examination; find what they do not cover.
02-oracle-gaming-python: same against the Python guard. Try conftest.py, a fixture module, a helper imported by tests, pytest.ini/pyproject markers, a sitecustomize, a __init__ that shadows.
03-weak-assert: build a suite whose assertions are true for a whole FAMILY of wrong programs (assert result is not None, assert len(x)==3, assert isinstance, smoke tests). Measure how often fluidfix ships a member of the family that is not the original. Report the rate over >=20 defects.
04-tautological-test: tests that pass no matter what (assert True, a try/except that swallows, a test that never calls the function). Does fluidfix notice it has no oracle, or does it "repair" anything?
05-flaky-adversarial: a suite that fails on a schedule designed to beat re-confirmation — fails every Nth run, or time/order dependent rather than random. FLUIDFIX_CONFIRM defaults to 1. Find a flake shape that survives confirmation, and report the shape.

## Attacking the decision (make it ship something wrong)
06-compensating-two-site: force a compensating repair at a DIFFERENT site than the defect, in a language where SIGHT is not consulted (C). Attack surface A + C.
07-compensating-one-site: two genuinely different programs reachable at ONE line by two different acts, both green. Per surface C the proxy should call this unambiguous and ship one. Reproduce it, and measure how often the shipped one is the wrong one over >=10 fixtures.
08-capped-ship: make a search get cut by the budget with exactly one green found, so it ships as BUILT -> SHIP. Per surface B. Prove the green is NOT the unique repair by exhibiting a second green the search never reached.
09-spelling-vs-program: build the pair that separates "same program spelled twice" from "two different programs" and show the proxy classifying both wrongly in opposite directions. Propose the observation that WOULD separate them (report only, no src edits).
10-rank-veto-abuse: attack the ranking law's RETRIED veto and the class order — a defect whose true class is ranked so late the budget dies first, or a class whose retry marking suppresses the real answer.

## Attacking integrity (leave the repo worse)
11-rollback-kill: kill fluidfix at every phase (during mutation, during build, during suite run, between candidate sets) and check the repo is byte-identical afterwards. .fluidfix/inflight.json is the journal; attack its window. Use SIGKILL, not SIGTERM.
12-concurrent-guards: run two guards on one repo at once, and a guard while the user edits a file. Does the journal or the rollback clobber the other's work?
13-stale-and-symlink: attack `stale_binary()` and the file-writing path — symlinked sources, a read-only file, a file with CRLF, a file with no trailing newline, a source outside the repo root reached by a symlink. Does a repair corrupt encoding, permissions, or line endings?
14-hang-and-resource: candidates that hang, fork-bomb-lite, allocate, or spawn children that outlive the parent. The process-group kill is the defence. Find a shape that escapes it. DO NOT run anything that could destabilise the host: no real fork bombs, cap memory, one at a time.

## Attacking the claims (the website and CHANGELOG say things)
15-byte-exact-audit: fluidfix claims byte-exact repairs. Over >=10 defects, diff the repaired file against the pristine original byte for byte, including whitespace, EOL, and file mode. Report every case where "byte-exact" is not literally true.
16-refusal-honesty: collect >=15 refusals and check each reason against what actually happened in that run. Any refusal whose stated reason is not the real cause is an S3.
17-estimate-honesty: attack `fluidfix estimate` — repos where it gives a number that the actual run then contradicts. Measure predicted vs actual over >=6 repos.

## Attacking the teaching path
18-teaching-poison: teach fluidfix from a WRONG worked example, or an example that generalises to a dangerous class. What does it then do to a healthy repo? Does anything refuse a bad teacher?
19-class-collision: two taught classes whose candidate sets overlap or contradict. Which wins, and is that a law ruling or code order?

## The whole pipeline
20-end-to-end-hostile: take a real repo copy (cglm or Box2D), inject a defect, and ALSO make the environment hostile in ways a real user's repo might be: a dirty working tree, an unrelated failing test already present, a slow test, a test that writes files, a .gitignore'd generated source. Report what fluidfix does with a suite that is not green to begin with.
