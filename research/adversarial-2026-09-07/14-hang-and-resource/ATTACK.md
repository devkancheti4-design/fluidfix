# 14-hang-and-resource

## 1. Target

Candidates that hang or spawn children outliving the parent: find a shape that escapes
fluidfix's process-group kill.

## 2. Attack design

`coracle.py:177-209` is the defence, and CHANGELOG 0.7.x states it as a contract:

> **A hanging candidate is killed, not orphaned.** … The C oracle now starts a new
> session and signals the whole process group.

The property under attack is *reachability of the kill*: fluidfix believes that when a
candidate run exceeds its budget, everything that run created dies with it. Three ways
that belief can be false:

1. **The defence is not on every path.** `coracle._sh` is the only call site that uses
   `start_new_session=True` + `killpg`. `oracle.py:157` (Python) and `javaoracle.py:53`
   (Java) are plain `subprocess.run(..., timeout=)`, which on POSIX does
   `process.kill(); process.wait()` — it signals **one pid**, never a group.
2. **The group can be left.** `killpg` reaches only processes still in the group; a
   child that calls `setsid()` or double-forks is gone from it. (`SIGKILL` cannot be
   ignored, so "a candidate that ignores the signal" is not a viable shape — that part
   of the defence is sound by construction.)
3. **The pgid is looked up too late.** `os.killpg(os.getpgid(proc.pid), ...)` derives
   the group id from `proc.pid` *at kill time*. By then `proc` is frequently already
   reaped, so `getpgid` raises and the code falls into `proc.kill()` — a no-op on a
   reaped pid — while the group itself is still very much alive.

If any of these holds, an orphan survives the run. fluidfix's own lab notebook records
what an orphan then costs (CHANGELOG 0.6.x): *"an orphaned benchmark process
concurrently writing candidate lines into the arrow clone … made one contaminated run
look like a wrong repair of `arrow/arrow.py`."* So the payoff is not cosmetic.

Everything below is bounded by `bin/tmo` (nice -n 15 + a perl `alarm` that SIGKILLs the
whole child process group; this host has no coreutils `timeout`). Every helper carries
`FFX14MARKER` in argv, self-exits after ≤90 s, refuses to start past a hard population
cap, and is swept with `bin/sweep.sh`, which prints `ps` proof afterwards.

## 3. Attempts

### E0 — do the three oracle call shapes reap a grandchild? (`bin/probe_semantics.py`, `logs/E0-semantics.log`)

Ran the *verbatim* call shapes out of tree, each against a child that spawns one
grandchild and then hangs.

```
--- oracle.py:157 / javaoracle.py:53  subprocess.run(timeout=)
    result=TIMEOUT  survivors_after_kill=1
      LEAKED: 36416 36359 …/Python
--- coracle.py:191  Popen(start_new_session)+killpg
    result=TIMEOUT  survivors_after_kill=0
```

**The Python and Java guards have no group kill at all.** Anything a hung candidate's
test process started survives, reparented to pid 1. Note there is also no `--test-timeout`
backstop in this venv: `pytest_timeout` is not installed, so `oracle.py:148` never adds
`--timeout=`, and the `subprocess.run` timeout is the *only* thing that stops a hang.

### E1 — four shapes against the C path's killpg (`bin/probe_cpath.py`, `logs/E1-cpath.log`)

```
A plain-grandchild   rc=1 TIMEOUT   4.0s  survivors=0  -> reaped
B setsid-grandchild  rc=1 TIMEOUT  14.0s  survivors=1  -> ESCAPED killpg
C double-fork        rc=1 TIMEOUT  14.0s  survivors=1  -> ESCAPED killpg
D no-timeout-leak    rc=1 TIMEOUT  13.9s  survivors=1  -> ESCAPED killpg
```

A held (defence working). B and C escape as designed — expected, and arguably out of
scope for a pgid-based kill. **D was the surprise**: shape D is
`sh -c 'helper & echo ok; exit 0'` — a command that *succeeds instantly*. It should have
returned rc=0 in milliseconds. It returned `rc=1, "TIMEOUT"` after 13.9 s, and the helper
escaped a killpg that did fire.

### E2 — why D escapes (`bin/probe_D.py`, `logs/E2-shapeD.log`)

```
Popen shell pid = 51752
TimeoutExpired raised -> entering coracle's kill branch
  poll() (None=running, int=already exited/zombie): 0
  helper before kill: 51753 1 51752 SN          <-- pid ppid pgid: helper IS in group 51752
  os.getpgid/killpg RAISED ProcessLookupError: [Errno 3] No such process
  -> FALLBACK proc.kill(): signals ONLY the shell pid, not the group
SURVIVORS: 1
   51753 1 51752 SN
```

Two coupled defects in `coracle.py:177-209`:

- `communicate(timeout=)` waits for **EOF on the stdout pipe**, not for process exit. A
  backgrounded process inherits that pipe, so a command that exits 0 immediately still
  burns the entire `--suite-timeout` and is then reported as `TIMEOUT` → rc 1 → the
  candidate is rejected on a lie.
- By the time the kill branch runs, the shell has exited *and been reaped*
  (`proc.poll()` → `0`), so `os.getpgid(proc.pid)` raises `ProcessLookupError`, and the
  `except` fallback `proc.kill()` is a no-op on a reaped pid. **The group still exists —
  the helper's pgid is 51752 — and `killpg(51752, SIGKILL)` would have worked.** The code
  derives the pgid from a corpse instead of recording it at spawn. `start_new_session=True`
  makes `proc.pid` *be* the pgid, so `os.killpg(proc.pid, SIGKILL)` needs no lookup at all.

### E3 — real `fluidfix guard`, Python path, leaking session fixture (`fixtures/py-leak`, `logs/E3-*`)

Victim: `steps.py` with `n -= 2` where `n -= 1` is meant, plus an ordinary
session-scoped `conftest.py` fixture that starts a background service. Nothing
adversarial: `_flip_augmented` (`acts.py:229`) proposes `n += 2` on that very line,
which is an infinite loop — **fluidfix's own shipped act manufactures the hanging
candidate.** Result: correct repair shipped, `1` orphaned service left running
(`ppid=1`), and the report never mentions it.

### E4 — first port fixture, defeated by my own fixture

Same shape with the service holding TCP 47814. The orphan survived (`lsof` confirmed it
holding the LISTEN socket), but my fixture probed liveness by checking whether the port
was busy — so it happily adopted the *orphan's* port and the suite stayed green. My
error, not a fluidfix defence. Fixture hardened (bind without `SO_REUSEADDR`, fail the
session if the server process exits) and rerun as E5/E6.

### E5/E6 — the landed attack (`fixtures/py-port`, `logs/E6-*`)

See §4.

### Not run, on safety grounds

- **Fork bomb / unbounded process growth.** Prohibited by the brief and by judgement on a
  shared host. Worth recording that nothing in fluidfix bounds it: `grep -rn
  'resource\.|RLIMIT|setrlimit|ulimit' src/fluidfix/*.py` returns **zero hits**. There is
  no `RLIMIT_NPROC`, no `RLIMIT_AS`, no `RLIMIT_CPU` on any candidate run, on any path.
- **Memory-exhaustion candidate.** Same reason. A candidate that allocates is bounded only
  by the wall-clock timeout, and on the Python/Java paths a memory-hungry grandchild
  outlives that timeout (E0), so the allocation is not even reclaimed at kill time.
- **CPU-contention escalation to S4.** The realistic damage from E6's orphan is the case
  CHANGELOG 0.7.x describes: a leaked *spinning* process pinning every core so later
  candidates — including the correct one — time out and are rejected. Deliberately not
  run: it needs a real spinner on a machine shared with other agents' work. I substituted
  a zero-CPU orphan that contends for a *port* instead, which exercises the identical
  mechanism (a leaked process denies a resource the suite needs) at zero host cost.

## 4. Outcome

### Finding 1 — S3 FALSE CONFIDENCE. fluidfix reports "repaired"; the suite it just certified is red the moment it hands the repo back.

**Reproduction** (from `research/adversarial-2026-09-07/14-hang-and-resource/`):

```sh
sh bin/sweep.sh
cd fixtures/py-port && rm -rf .fluidfix service.log __pycache__ tests/__pycache__
printf 'def steps_to_zero(n):\n    """Count the unit steps needed to walk n down to zero."""\n    steps = 0\n    while n > 0:\n        n -= 2\n        steps += 1\n    return steps\n' > steps.py

../../bin/tmo 240 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . \
  --observer mechanical --suite-timeout 10 --candidate-timeout 10 \
  --budget 150 --max-candidates 4

ps -axo pid=,ppid=,command= | grep FFX14MARKER-server | grep -v grep   # orphan, ppid 1
../../bin/tmo 60 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python \
  -m pytest -q --no-header -p no:cacheprovider                          # the user's own suite
sh ../../bin/sweep.sh
```

**What fluidfix wrote** — the source diff is *correct and byte-exact*:

```diff
--- a/steps.py
+++ b/steps.py
@@ -2,6 +2,6 @@
     steps = 0
     while n > 0:
-        n -= 2
+        n -= 1
         steps += 1
```

**What fluidfix said:**

```
[14:47:03] steps.py: repaired line 5 in 9 suite runs (35.6s):
  - n -= 2
  + n -= 1
```

**What was true one second later** (`logs/E6-user-suite.log`):

```
ERROR tests/test_steps.py::test_four  - Failed: test server could not start (rc=4); port 47814 is already in use
ERROR tests/test_steps.py::test_one   - Failed: test server could not start (rc=4); port 47814 is already in use
ERROR tests/test_steps.py::test_zero  - Failed: test server could not start (rc=4); port 47814 is already in use
3 errors
```

`fluidfix guard`'s sole acceptance gate is *the full suite passes* (`oracle.check`,
docstring: "the FULL suite, which remains the ONLY acceptance gate"). "repaired" therefore
asserts a green suite. It hands back a machine on which the suite is red — because of a
process **fluidfix itself created and failed to reap**, during a hang **fluidfix's own
`_flip_augmented` act manufactured**. The report supports the diff; it does not support the
state of the machine the run leaves behind. Nothing in the output mentions the orphan.

There is a real path from here to a wrong repair, and fluidfix has already walked it once:
CHANGELOG 0.6.x discards two replay rounds because *"an orphaned benchmark process
concurrently writing candidate lines into the arrow clone … made one contaminated run look
like a wrong repair."* The tool still manufactures orphans of exactly that kind on the
Python path — and that path has no group kill at all.

**Classification: `actuation`** (with a `wording` component).

- **Observation byte passed:** `situation(BUILT=True)` = `513` = `0b1000000001`
  (low 8 bits `00000001`; bits 8-9 = 2, the DEBUG job). The candidate really was green,
  really was unambiguous. (`logs/E7-engine-byte.txt`.)
- **Act the law returned:** `decide(513)` → `SHIP`.
- **What the law would rule on a correct byte:** *the same act.* `SHIP` is right — the
  repair is right. Not a `ruling` defect, and not an `observation` defect either: every bit
  the law was given was accurate. **The law was never asked about process lifetime.** There
  is no bit for it — `BITS = ['BUILT','AMB','UNREAD','NOTWIN','HIDDEN','CAPPED','REFUTED','SELF']`.
  The law ruled correctly and the body then did something the act did not authorise: it left
  a live process holding a resource the certified suite needs. That is `actuation`. The
  `wording` component is separable and independently fixable: even granting the leak, the
  report could say *"1 process from a timed-out candidate could not be reaped"* and it says
  nothing.

**Reproducibility of the leak, independent of the port trick:** E3 (`fixtures/py-leak`) is
the minimal version — real `fluidfix guard`, ordinary session fixture, correct repair
shipped, orphan left running. `logs/E3-poll.txt` samples `ps` through the run.

### Finding 2 — S3. `coracle.py:200` reaches an empty group. (`logs/E2-shapeD.log`)

The C path's advertised group kill degrades to a no-op whenever the shell has exited before
the timeout fires — the common case for a command that leaves a background process. The
`ProcessLookupError` is swallowed and `proc.kill()` signals a reaped pid. `_sh` then returns
`(1, "TIMEOUT")` for a command that **exited 0**, so the candidate is rejected with a stated
reason that is not what happened. Not demonstrated end-to-end against a C repo (no CMake
victim built inside the 45-minute budget), but the failing mechanism is the verbatim
`coracle._sh` body and the log prints each step.

### Finding 3 — S3 (documentation). The CHANGELOG contract is broader than the fix.

> **A hanging candidate is killed, not orphaned.**

Headline unqualified; true on neither the Python guard (E0) nor the Java guard (E0, by
inspection of `javaoracle.py:53`), and unreliable on the C guard it does cover (E1 B/C/D,
E2). The entry's own final sentence scopes the fix to "The C oracle", so the body is honest
and the claim above it is not.

## 5. What defended

- **`SIGKILL`, not `SIGTERM`.** Choosing an uncatchable signal makes the whole
  "candidate installs a handler and ignores the kill" family impossible. Not attempted
  after reading `coracle.py:200`; it cannot work.
- **`start_new_session=True` + `killpg` really does reap ordinary grandchildren.** E1
  shape A — the plain, overwhelmingly common case of a test binary forking a helper — was
  reaped with 0 survivors. The defence does the job it was built for; my escapes are all
  at its edges.
- **The rollback and the journal held everywhere I looked.** Across E3-E6, five real guard
  runs including runs killed mid-candidate by a hang, `conftest.py` and `tests/test_steps.py`
  came back byte-identical (`logs/E5-pristine-hashes.txt` vs the post-run `shasum`:
  `7ca6b860…` and `26610c4d…` before and after). The suite was never edited. No S2.
- **Every repair shipped was the correct one.** `n -= 2` → `n -= 1` in all runs; the
  hanging candidate `n += 2` was correctly rejected every time, never shipped. No S1.
- **The engine ruled correctly on every byte it was handed.** `decide(513) = SHIP`. No
  `ruling` defect, consistent with the project's history.

## 6. Verdict

fluidfix held on correctness — no wrong repair, no repo corruption, no bad ruling — but its
"a hanging candidate is killed, not orphaned" contract does not hold: the Python and Java
guards have no process-group kill at all, the C guard's `killpg` degrades to a no-op when
the shell exits first (`coracle.py:200`), and a real `guard` run ships "repaired" while
leaving behind an orphan of its own making that makes the certified suite red — an S3
(`actuation`).
