# 20-end-to-end-hostile — attack report

RED TEAM agent 20 · 2026-09-07 · target `20-end-to-end-hostile`

---

## 1. Target

Run fluidfix end-to-end on a real repo copy (cglm, 1131 tests) carrying an injected
defect **and** the hostility a real user's repo actually has — a dirty working tree
with staged WIP, an unrelated already-failing test, a slow test, a test that writes
files into the source tree, a `.gitignore`d generated production source — and answer
the question the target names as most important: **what does fluidfix do when the
suite is not green to begin with?**

---

## 2. Attack design

fluidfix's entire epistemology is "the target's own suite is the judge". Every
defence in the tool (`oracle.check()`, the AMB proxy, the output cross-examination,
byte-exact rollback) is built on the assumption that *green means correct*. That
assumption has an unexamined precondition: **the suite was green before the defect.**

A real repo usually is not green. There is a flaky integration test, a stale
expectation someone has not got round to, a platform-specific skip that is really a
failure. So the attack is not to fool the oracle — it is to run fluidfix in the world
it actually ships into and see whether

* the **decision** stays honest (does it ship something wrong when a second, unrelated
  failure is in play?), and
* the **report** stays honest (does it tell the user the real reason, or a fabricated
  one?), and
* the **actuation** stays scoped (does `--commit` touch only what it says it touched?).

Three properties looked attackable from reading the source before running anything:

* `GuardReport.summary()` (guard.py:69-90) picks its refusal wording from
  `self.evidence["pointed"]`. `cguard_once` (coracle.py:670-771) **never constructs
  `evidence`** on any of its four `GuardReport(...)` returns. So on the C path
  `pointed` is `[]` by construction and every budget-exhausted C refusal is forced
  into the "nothing pointed at a file" branch — whether or not anything pointed.
* `repair()` returns a *reason* carrying the engine law's ruling for the
  BUILT+CAPPED case (loop.py:193-247), together with `res.greens` — the actual
  suite-passing candidates. `cguard_once` reads only `result.repaired` and
  `result.ambiguous`. Everything else, greens included, is dropped on the floor.
* `commit_repair()` (guard.py:670-694) advertises "commit a successful restoration
  (**only the repaired file**)". It runs `git add -- <file>` and then
  `git commit -m msg` — **with no pathspec**. `git commit` with no pathspec commits
  the whole index.

---

## 3. Attempts

Environment: macOS 25.5.0, `nice -n 15` + a hand-written perl-alarm timeout wrapper
(`bin/tmo`, no coreutils `timeout` on this host), one run at a time.
fluidfix from `/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix`, unmodified;
no `FLUIDFIX_*` env var set (so `FLUIDFIX_CONFIRM` was its default 1).

### Attempt 1 — control: clean cglm, one in-vocabulary defect (`logs/E0-control.log`)

`repo/` is a copy of the shared cglm clone, configured `-DCGLM_USE_TEST=ON`, 1131/1131
green. One defect injected, uncommitted:

    include/cglm/bezier.h:53   -  x   = 1.0f - s;
                               +  x   = 1.0f + s;

flipped-additive = fluidfix's shipped kind 3, dead centre of the vocabulary. Suite goes
to 1130 passed / 1 failed (`bezier`).

    cd repo && ../bin/tmo 900 .../fluidfix cguard . --budget 600

**REFUSED after 605 s.** The defect file was ranked #1 and searched. 64 candidates
rejected. See Attempt 2 for what the report said and section 4/F1 for why it is wrong.

### Attempt 2 — prove a green was found and thrown away (`logs/E0-last_refusal.json`)

The harvest shows the search reached the defect line and moved past it:

    include/cglm/bezier.h:53  '  x   = 0.0f + s;'    1 test(s) failed, first: bezier
    include/cglm/bezier.h:53  '  x   = 1.-1f + s;'   error: invalid digit 'f' ...
    ...then lines 56 and 57 were searched (9 further rejections)

Exactly two rejections at line 53, and they are exactly the two **kind 1** candidates.
The observation at line 53 carries `kinds=[1, 3]` (`bin/probe_packet.py`), the lane
machine emits kinds in ascending order, and the loop only advances to the next
observation after `HALT(mask)` — i.e. after kind 3. So kind 3 *was* tried at line 53,
and it produced no rejection record. `bin/prove_green.py` shows why:

    $ ../bin/tmo 300 python bin/prove_green.py repo include/cglm/bezier.h 53
    line 53 = '  x   = 1.0f + s;'
      kind 1 -> act 6: ['  x   = 0.0f + s;', '  x   = 1.-1f + s;']
      kind 3 -> act 8: ['  x   = 1.0f - s;']
      CANDIDATE '  x   = 1.0f - s;' -> oracle.check() ok=True why=''
    restored; sha equal: True

The kind-3 candidate is the **byte-exact pristine line** and fluidfix's own
`COracle.check()` calls it green. It was in `greens` when the 600 s deadline fired.

### Attempt 3 — build the hostile tree (`repo-hostile/`)

Fresh copy of cglm, committed as a realistic repo (`git log b4581be`) plus:

| hostility | how |
|---|---|
| unrelated already-failing test | `test/src/test_hostile.c :: hostile_stale` — a stale expectation `glm_vec3_dot((1,2,3),(4,5,6)) == 99.0f` (true answer 32). Committed, red, "we know". |
| slow test | `hostile_slow` — `usleep(2 s)` on every suite run |
| test that writes files | `hostile_writes` — appends `hostile_test_artifact.log`, writes `include/cglm/.hostile_scratch` **into the source tree** |
| `.gitignore`d generated source | `include/cglm/gen_buildinfo.h`, `#include`d by `bezier.h`, added to `.gitignore` |
| dirty working tree | `README.md` edited unstaged; `NOTES_WIP.txt` untracked; **`src/vec3.c` staged but not committed** |
| the defect | `include/cglm/bezier.h:54` (line shifted by the new include), uncommitted, HEAD holds the correct line |

Baseline: **1134 tests ran, 1132 passed, 2 failed** (`bezier`, `hostile_stale`).

### Attempt 4 — is the correct repair still acceptable? (`logs/H03-true-repair-rejected.log`)

    CANDIDATE '  x   = 1.0f - s;' -> oracle.check() ok=False
                                     why='1 test(s) failed, first: hostile_stale'

The byte-exact correct repair is **rejected**, blamed on the pre-existing unrelated
failure. `check()` requires the whole suite green, so in a repo that is not green
**no candidate can ever be accepted** — fluidfix is structurally inert, not wrong.
That part is a defence (see section 5), and I do not report it as a finding.

### Attempt 5 — end-to-end hostile run (`logs/H05-cguard.log`)

    cd repo-hostile && ../bin/tmo 600 .../fluidfix cguard . --budget 300 --commit

REFUSED after 311 s, exit 2, source bytes unchanged. What it told the user is
finding F1. What the harvest recorded is the proof (section 4).

### Attempt 6 — `--commit` with the user's own work staged (`logs/D02-guard-commit.log`)

The cglm search cannot finish inside a sane budget (Attempt 1), so the commit
*actuation* was reproduced on a minimal fixture through the real CLI. `commit_repair`
is language-independent shared code: `cmd_guard` (cli.py:125), `cmd_jguard`
(cli.py:241) and `cmd_cguard` (cli.py:271) all call the same function, and
`repo-hostile/` is set up with exactly this shape (`src/vec3.c` staged). Result: **S2,
section 4/F2.**

### Attempt 7 — repair inside a `.gitignore`d generated source (`logs/G01-guard-gitignored.log`)

Same minimal-fixture technique, defect placed in a generated, gitignored module.
Result: **S3, section 4/F3.**

### Attempt 8 — things I tried that went nowhere (defences held; see section 5)

* Getting fluidfix to edit or silence the hostile test file — never attempted a test
  file; `_c_sources` excludes `test/` and `_is_harness_file` excludes `runner.c`.
* Getting a mutation left on disk after a 311 s run with 64 mutations under a
  file-writing test — every byte restored.
* Getting the file-writing test to trip `stale_binary()` or poison the source tree
  scan — it did not; the written files carry no source extension.
* Getting a compensating repair shipped while two tests were red — impossible by
  construction, because `check()` demands the whole suite.
* An **S1** of any kind. None found. fluidfix shipped nothing wrong in this wave.

---

## 4. Outcome

### F1 — S3 FALSE CONFIDENCE: the C guard's refusal contradicts its own law, and hides the green it found

**Severity: S3.** **Classification: `wording`, with an `actuation` component.**

Reproduce (either tree; hostile shown):

    cd research/adversarial-2026-09-07/20-end-to-end-hostile/repo-hostile
    ../bin/tmo 600 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix cguard . --budget 300

What the user is told (`logs/H05-cguard.log`, identical wording in `logs/E0-control.log`):

> REFUSED: nothing in the failure pointed at a file — no traceback frame, no
> discriminating literal, no taught signal narrow enough to localise. The ranking had
> only circumstantial evidence, **so a bigger budget searches the same files in the
> same order.** Files searched: include/cglm/bezier.h, src/bezier.c. What helps, in
> order: name the file yourself (--file <path>); make the failing assertion carry a
> value that occurs in few files; or teach a narrower signal for this class.
>   hint: --budget exhausted (300s)

Four claims, all false in this run:

1. **"nothing in the failure pointed at a file"** — the failing test name `bezier` is
   precisely what put `include/cglm/bezier.h` at rank 1, via the token-affinity lane in
   `find_candidate_files_c` (coracle.py:493-563). This is not a one-off: `cguard_once`
   never passes `evidence=` to any of its `GuardReport(...)` returns (coracle.py:751,
   763, 767, 770), so `pointed` at guard.py:70 is `[]` **by construction**, and
   guard.py:71-95 forces every budget-exhausted C refusal into this branch. The C
   path cannot ever say "the failure pointed somewhere".
2. **"a bigger budget searches the same files in the same order"** — a bigger budget
   repairs the bug. The engine law had already said so.
3. **"--file &lt;path&gt;"** — `fluidfix cguard --help` lists no `--file`. The refusal
   advises a flag that does not exist on this subcommand.
4. The real cause is never stated. In the hostile run fluidfix *measured* it and put it
   in the harvest (`logs/H05-last_refusal.json`):

       {"at": "include/cglm/bezier.h:54",
        "tried": "  x   = 1.0f - s;",
        "why": "1 test(s) failed, first: hostile_stale"}

   The byte-exact correct repair was generated, tried, and rejected by a test that was
   already red before fluidfix started. Nothing in the user-facing summary says
   "your suite had 2 failures when I arrived, and one of them is not the defect."

**Observation byte and act.** In the control run, at the deadline, `repair()` called
`_rule(capped=True)` (loop.py:193) with `greens = ['  x   = 1.0f - s;']`,
`set_amb = False`, `sites = {53}`:

    from fluidfix.engine import decide, situation, BITS, ACTS
    situation(BUILT=True, AMB=False, CAPPED=True) == 545      # byte 0x21 = 0b00100001
    decide(545) -> 'RAISE_BUDGET'

The law ruled **RAISE_BUDGET** on byte `0x21`, correctly — "you found a green but the
search was cut short; spend more clock." On the byte the search would have carried had
it finished, `situation(BUILT=True) == 513` (byte `0x01`), the law rules **SHIP**, which
is also correct — the green is the pristine line. **No `ruling` defect here.** The law
was right both times.

What went wrong is downstream of the law. `_rule` set
`res.reason = "a candidate passes, but the search was cut short before it could be
shown unique … Raise the budget and re-run (engine law: BUILT+CAPPED -> RAISE_BUDGET)"`
and `res.greens = ['  x   = 1.0f - s;']` (loop.py:220, 238-243). `cguard_once` reads
only `result.repaired` and `result.ambiguous` (coracle.py:762-768); the reason and the
greens are discarded, never reach `GuardReport`, never reach
`.fluidfix/last_refusal.json`, never reach the user. The report then prints advice that
is the **negation** of the law's ruling. `wording` for the printed claims;
`actuation` for the fact that the act the law returned (RAISE_BUDGET) is neither
performed nor surfaced on the C path — `cguard_once` has no escalation stage at all,
unlike `guard_once` (guard.py:539-604).

Diff fluidfix wrote to disk: **none** (correct — it refused).

### F2 — S2 CORRUPTION: `--commit` commits the user's whole index, not "only the repaired file"

**Severity: S2.** **Classification: `actuation`** (with a `wording` component).

Reproduce end-to-end (fixture rebuilt by the commands in `bin/mk_dirtyindex.sh`):

    cd research/adversarial-2026-09-07/20-end-to-end-hostile/repo-dirtyindex2
    # HEAD carries the regression; the user has unrelated work STAGED:
    #   M  shipping.py      (half-finished rewrite, calls a function that does not exist)
    #   A  secrets_wip.txt  (private scratch notes, staged by accident with `git add -A`)
    ../bin/tmo 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . --commit --budget 120

Output (`logs/D02-guard-commit.log`):

    billing.py: repaired line 2 in 5 suite runs (3.1s):
      - if days >= 30:
      + if days > 30:
      committed

What was actually committed:

    $ git show --stat HEAD
    fluidfix: restore billing.py:2

    - if days >= 30:
    + if days > 30:

    Routed by the fluidfix kernel (engine law: BUILT -> SHIP); accepted by the
    project's own suite in 5 runs.

     billing.py      | 2 +-
     secrets_wip.txt | 1 +          <-- the user's private notes
     shipping.py     | 3 ++-        <-- the user's broken half-finished rewrite
     3 files changed, 4 insertions(+), 2 deletions(-)

    $ git status --short
    (empty — the user's staging area is gone)

Three separate harms, all in one commit:

* Unrelated, **non-building** work-in-progress (`shipping.py` calls an undefined
  `surcharge`) is now in the repo's history under a message that says
  "accepted by the project's own suite in 5 runs". It was not; the suite never saw it.
* A file the user staged by accident is now permanently in history.
* The user's carefully built index (the `git add -p` workflow) is destroyed silently.

Under `--interval` — the documented "commit-and-forget maintenance, unattended" mode —
this fires without anyone watching, on whatever happens to be staged.

**Observation byte and act.** `situation(BUILT=True) == 513`, byte `0x01`,
`decide(513) -> 'SHIP'`. The law ruled correctly and SHIP was the right act: the repair
is right and the suite accepted it. The body then did something the law never asked
for. `commit_repair` (guard.py:670-694):

    subprocess.run(["git", "-C", root, "add", "--", report.file], ...)
    subprocess.run(["git", "-C", root, "commit", "-m", msg], ...)   # guard.py:690
                                                                    # <- no pathspec

`git commit` without a pathspec commits the entire index. The docstring one line above
(guard.py:671) says "commit a successful restoration (**only the repaired file**)" —
that claim is false, hence the `wording` component. The whole defect is the missing
`"--", report.file` on guard.py:690 (or `--only`).

This is reachable from `cguard` and `jguard` too: cli.py:271 and cli.py:241 call the
same function, and `repo-hostile/` is staged exactly this way (`M  src/vec3.c`). It did
not fire there only because that run refused (F1).

### F3 — S3: a repair written into a `.gitignore`d generated source is reported as "nothing to commit"

**Severity: S3.** **Classification: `wording`.**

Reproduce:

    cd research/adversarial-2026-09-07/20-end-to-end-hostile/repo-genignored
    # gen_rates.py is generated at build time and listed in .gitignore
    ../bin/tmo 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . --commit --budget 120

Output (`logs/G01-guard-gitignored.log`), exit code **0**:

    gen_rates.py: repaired line 3 in 5 suite runs (2.2s):
      - if days >= 30:
      + if days > 30:
      tree already matches last commit — nothing to commit

Diff fluidfix wrote to disk (`gen_rates.py:3`):

    -    if days >= 30:
    +    if days > 30:

The tree does **not** match the last commit. A repair was written to a file git is not
tracking, `commit_repair` took the `git diff --quiet` early return (guard.py:676-679,
which cannot see an ignored path), and the user was told there was nothing to record.
The repair will be destroyed the next time the generator runs, `fluidfix guard
--interval` will "repair" it again, report success again, and record nothing — forever,
at exit code 0, with CI green. `--commit` never even reaches `git add`, which would
have failed loudly on an ignored path and told the truth.

`_c_sources` (coracle.py:470-491) and the Python file scan are likewise gitignore-blind,
so the same trap exists on the C path: `include/cglm/gen_buildinfo.h` in `repo-hostile/`
is a candidate file fluidfix will happily search and edit.

### Also observed, not claimed as findings

* Both cglm runs left `covbuild/` (a full instrumented build tree) and `.fluidfix/`
  untracked in the user's repo. Documented behaviour, not corruption, but it is state
  the user did not have.
* `hostile_test_artifact.log` grew to 35 lines — 35 suite runs in the 311 s hostile
  pass — showing a file-writing test's side effects accumulate unbounded across a
  guard pass. Nothing broke.
* `CHANGELOG.md` in the fluidfix working tree shows 29 added lines that are not mine
  (I wrote only inside my own directory; verified). Another agent in this wave, or a
  pre-existing edit. Flagging it, not touching it.

---

## 5. What defended

These stopped real attempts and deserve to be recorded as working:

1. **`COracle.check()` demands the WHOLE suite green** (coracle.py:268-300). This is
   what makes a not-green repo *inert* rather than *dangerous*. Every compensating or
   partial repair I could construct was rejected because a second test was still red.
   It is also the direct cause of the correct repair being rejected in Attempt 4 — the
   cost of the defence, honestly paid.
2. **Byte-exact rollback under hostility.** After a 311 s pass, 64 rejected mutations,
   a 2 s slow test, and a test writing files into `include/cglm/`, `sha256` of
   `include/cglm/bezier.h`, `README.md` and `src/vec3.c` were identical before and
   after (`logs/H04-before.sha` vs `logs/H06-after.sha`), and `git status --short` was
   unchanged apart from the new `.fluidfix/` and `covbuild/` directories. The staged
   `src/vec3.c` survived intact. No mutation was left on disk.
3. **Harness and test exclusion.** `_c_sources` skips `test/`, `samples/`, `shared/`,
   `examples/`; `_is_harness_file` skips `runner.c`. The guard never once proposed
   editing `test_hostile.c` to make `hostile_stale` pass, which was the cheapest path
   to green available to it. The output cross-examination in `check()` was never needed
   because the file filter got there first.
4. **The engine law ruled correctly every time.** BUILT+CAPPED (`0x21`) →
   RAISE_BUDGET, BUILT (`0x01`) → SHIP. No `ruling` defect. Every failure in this
   report is downstream of the law: a body that discarded the act, or a report that
   described the outcome wrongly.
5. **Refusal beat guessing.** With a green in hand and the search unfinished, fluidfix
   refused rather than shipping it. That is the right call and it is why there is no S1
   in this report.
6. **`--commit` on a refusal did nothing.** The hostile run's `--commit` was a no-op,
   correctly.

---

## 6. Verdict

**fluidfix held on the decision — no S1, no corrupted source, no test file touched, and
the law ruled correctly on every byte — but it did not hold on the report or on the
commit: `git commit` with no pathspec swept the user's unrelated staged work into a
"fluidfix: restore" commit (S2, `actuation`, guard.py:690), and on the C path every
budget-exhausted refusal claims "nothing in the failure pointed at a file" and advises
against the bigger budget the engine law had just ruled for, while silently discarding
the byte-exact green it had already found (S3, `wording`, coracle.py:762-770 +
guard.py:70).**

---

## Files kept for rerun

    bin/tmo                     nice -n 15 + perl-alarm timeout wrapper (no coreutils timeout here)
    bin/probe_packet.py         prints the packet + MechanicalObserver kinds for a file
    bin/prove_green.py          applies fluidfix's own kind-N candidates and asks its own oracle
    bin/mk_dirtyindex.sh        rebuilds repo-dirtyindex2 from scratch
    bin/mk_genignored.sh        rebuilds repo-genignored from scratch
    repo/                       cglm copy, clean tree, one defect at bezier.h:53   (Attempts 1-2)
    repo-hostile/               cglm copy, all five hostilities + defect at :54    (Attempts 3-5)
    repo-dirtyindex/            same fixture with the defect UNCOMMITTED — negative control:
                                commit_repair correctly answers "clean" (logs/D01-guard-commit.log)
    repo-dirtyindex2/           minimal fixture, committed defect + staged WIP     (Attempt 6, F2)
    repo-genignored/            minimal fixture, defect in a gitignored generated source (Attempt 7, F3)
    pristine.tar                cglm source snapshot for byte comparison
    logs/                       every run's stdout, both refusal reports, before/after sha + status
