# 03-weak-assert — a suite whose assertions are true for a family of wrong programs

RED TEAM agent 03, 2026-09-07. All fixtures, scripts and per-defect run
directories are in this directory and rerunnable.

## 1. Target

Build test suites whose assertions are true for a whole FAMILY of wrong
programs, and measure how often fluidfix ships a family member that is not the
original — a rate, with its denominator.

## 2. Attack design

fluidfix's only source of truth is the suite. Its stated defence against a
suite that cannot tell two programs apart is the engine law's AMB lane:
"two DIFFERENT candidates both pass the suite -> ADD_STATE" (refuse, ask for a
pinning test). The whole no-silently-wrong-repairs claim rests on that bit
being measured correctly.

`loop.py::_rule` measures AMB as

    set_amb or len(sites) > 1

`set_amb` is set only when two greens land **inside one candidate set** (one
act, one line). `sites` counts **distinct line numbers**. So the proxy asks
*where* the greens came from, never *whether they are the same program*.

The gap that follows: **two greens that are genuinely different programs, found
at ONE line by TWO DIFFERENT acts, are invisible to both terms.** `set_amb`
stays False (one green per set) and `len(sites) == 1`. The law is then handed
the byte BUILT alone and rules SHIP — on `greens[0]`, the first green found.

Green order is not evidence-ranked. `lanes.EMIT` returns the lowest live bit,
so kinds are tried in **ascending kind number**: 0 strictness, 1 literal,
2 swapped-return-operands, 3 flipped-additive, 8 minmax, 9 aug-assign,
10 comparison-direction, 11 reversed-minus, 12 boolean. Whichever numerically
lower kind produces a green first wins, whether or not it is the repair.

A weak assertion is exactly what turns that latent gap into a shipped defect,
because it makes a second act's output green. `assert f(a, b) > 0` on a line
`return a - b` is satisfied by three different programs — `a - b`, `b - a`,
`a + b` — and two of those are reachable by two different acts.

So the prediction: **whenever the true repair's kind number is HIGHER than a
competing green's kind number, fluidfix ships the wrong program, silently.**
This is a quantified instance of known surface C; the new part is the rate, the
direction, and the fact that the outcome is decided by an integer ordering
rather than by any evidence.

## 3. Attempts

Two victim libraries, each ~15 ordinary five-line helpers, each with a weak
suite. Nothing in the libraries is adversarial; the weakness is entirely in the
assertions, which are the species real suites contain:
`is not None`, `isinstance(...)`, `len(x) == 3`, `> 0`, `>= 0`, `!= 0`,
`set(d) == {...}`, `any(d.values())`, smoke calls far from every boundary.

  * `victim/`  — `weakpkg/core.py` + `tests/test_core.py` (15 tests, 0.02s)
  * `victim2/` — `weakpkg2/core.py` + `tests/test_core.py` (15 tests, 0.02s)

Defects were injected with **fluidfix's own act appliers** (`inject.py` imports
`fluidfix.acts.candidates`), so every injected defect is by construction inside
the vocabulary fluidfix claims to repair. No strawman mutants, no hand-picking:
the enumeration is exhaustive over (line x matching kind x candidate).

`run_one.py` runs one defect end to end in a fresh copy: apply, check the suite
is red, `fluidfix repair . --file <pkg>/core.py --python <venv python> --json`,
then diff the resulting file against the **pristine** original byte for byte.
Every invocation is `nice -n 15` under `timeout.sh` (a perl-alarm wrapper —
this machine has no coreutils `timeout`), one at a time.

**Attempt 1 — two greens inside ONE candidate set (the original AMB).**
Fixture: `audit_flags`/`defaults`, `return {"cache": True, "trace": False}`
under `assert any(v is True for v in d.values())`. The defect turns the one
True off; the boolean applier proposes a flip of *every* boolean on the line,
so two greens land in one set. **Blocked.** `set_amb` fired and fluidfix
refused (`runs2/21`):

> AMBIGUOUS: 2 candidates at 1 different lines (62) all pass the suite — the
> tests cannot tell them apart, and one may CANCEL the fault rather than
> repair it. Add one pinning test (engine law: BUILT+AMB -> ADD_STATE, never
> guess)

**Attempt 2 — greens at two different lines.** Same defence, via `len(sites) > 1`.
`runs/18` (`peak_gap`, four greens at one line, all from different sets *and*
one set with two) refused correctly. This term works.

**Attempt 3 — one green per set, two sets, one line.** This is the one that
lands. `return a + b` under a sign-only assertion, defect `return a - b`:

  * kind 2 (swapped-return-operands) -> `return b - a` — green, **wrong program**
  * kind 3 (flipped-additive)        -> `return a + b` — green, the original

Kind 2 < kind 3, so `greens[0]` is the wrong program. `set_amb` is False (one
green per set), `sites == {10}`, the law gets BUILT alone, rules SHIP, and
fluidfix writes the wrong program to disk and prints "repaired".

**Attempt 4 — does the guard path differ?** No. `fluidfix guard .` on the same
defect ships the same wrong line (`repro_guard/`, transcript in section 4).
This is the README's headline unattended use ("deploy, commit, forget"), where
with `--commit` the wrong program is committed with no human in the loop.

**Attempt 5 — is the tree ever left dirty?** No. 0 of 6 refusals left the file
in any state other than the injected defect. Rollback held throughout.

## 4. Outcome

### The rate (the deliverable)

`summarize.py` pools both victims; raw output in `RESULTS.txt`.

```
injected in-vocabulary defects            : 65
  undetected by the weak suite (green)    : 33
  DETECTED -> fluidfix asked to repair    : 32   <-- denominator
    accepted repair shipped to disk       : 26
    refused                               : 6

WRONG PROGRAM SHIPPED  4/32 detected defects = 12.5%
                       4/26 accepted repairs = 15.4%
NOT BYTE-EXACT         5/26 accepted repairs = 19.2%  (4 wrong program + 1 equivalent respelling)
SHIPPED WITH >1 GREEN  10/26 accepted repairs = 38.5%
tree left dirty after a refusal           : 0
```

Denominators, stated plainly:

  * **65** in-vocabulary single-line defects injected across two weak-suite repos.
  * **32** of them turn the weak suite red, i.e. are defects fluidfix is
    actually asked to repair. (The other 33 are invisible to the suite;
    fluidfix correctly refuses with "no failing test" and they are excluded.)
  * **26** of those 32 ended in an accepted repair written to disk.
  * **4** of those 26 are a different program from the original: **15.4% of
    accepted repairs, 12.5% of detected defects.**
  * A 5th is byte-different but semantically identical
    (`page * size - size` -> `size * page - size`), which is not a wrong repair
    but is not byte-exact either.

The failure is not random. Restricted to the shape it targets — a
flipped-additive defect on a `return a + b` line whose assertion pins only a
sign — fluidfix shipped the wrong program **4 times out of 4 (100%)**. In all
10 multi-green ships, `greens[0]` was the output of the numerically lowest
matching kind; the run was correct exactly when the repairing act happened to
be that kind, and wrong exactly when it was not.

### S1 — WRONG REPAIR SHIPPED (4 cases)

Reproduction, from a clean tree, ~3 seconds:

```
/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/03-weak-assert/repro_s1.sh
```

Actual transcript:

```
--- suite with the defect in (must be RED) ---
FAILED tests/test_core.py::test_total_due_positive - assert -60 > 0
1 failed, 14 passed in 0.04s
--- fluidfix repair ---
repaired line 10 in 3 suite runs (2.5s):
  - return subtotal - tax
  + return tax - subtotal
--- what is on disk now ---
    """What the invoice says."""
    return tax - subtotal

--- suite after the 'repair' (green, and the program is wrong) ---
15 passed in 0.06s
total_due(100, 8) = -92   (correct: 108)
```

The diff fluidfix wrote to `weakpkg2/core.py`:

```diff
 def total_due(subtotal, tax):
     """What the invoice says."""
-    return subtotal + tax
+    return tax - subtotal
```

The invoice total for a 100 subtotal and 8 tax is now **-92**. The suite is
green. Nothing in the output says a second program also passed.

The guard path, same defect, `repro_guard/`:

```
[14:37:09] weakpkg2/core.py: repaired line 10 in 3 suite runs (2.1s):
  - return subtotal - tax
  + return tax - subtotal
```

All four S1 cases (each with its own run directory, `result.json`, and full
`fluidfix --json` report):

| run | original | injected defect | SHIPPED | reason reported |
|---|---|---|---|---|
| `runs/01`  | `return base + shipping`      | `return base - shipping`      | `return shipping - base`      | `engine law: BUILT -> SHIP` |
| `runs2/02` | `return subtotal + tax`       | `return subtotal - tax`       | `return tax - subtotal`       | `engine law: BUILT -> SHIP` |
| `runs2/04` | `return travel + buffer`      | `return travel - buffer`      | `return buffer - travel`      | `engine law: BUILT -> SHIP` |
| `runs2/06` | `return on_hand + delivered`  | `return on_hand - delivered`  | `return delivered - on_hand`  | `engine law: BUILT -> SHIP` |

Each recorded `ambiguous: false`, `suite_runs: 3`, `acts_tried: [7, 8]` (act 7
= swapped-return-operands, act 8 = flipped-additive), and a `greens` list of
**two different programs**, the second of which is the original.

**Classification: `observation`.**

  * Observation byte PASSED to the law: `situation(BUILT=True)` = **513**
    (`0x201`; bit 0 BUILT set, bit 1 AMB clear, job bits 8-9 = 2).
    `decide(513)` -> **SHIP**. The law ruled correctly on the byte it got.
  * The act the law returned: **SHIP**, actuated at `loop.py:223` (`_write`).
  * Byte the run actually supported: two greens
    (`return tax - subtotal`, `return subtotal + tax`) that are different
    programs, i.e. AMB is true: `situation(BUILT=True, AMB=True)` = **515**
    (`0x203`). **`decide(515)` -> `ADD_STATE`** — refuse and ask for one
    pinning test.
  * The defect is the AMB measurement at `loop.py:217`,
    `AMB=set_amb or len(sites) > 1`. It measures the provenance of the greens
    (same set? same line?) and never compares the greens to each other. Both
    terms are false here while AMB is true.

This is not a `ruling`. The law was given a false bit and did the right thing
with it.

### S3 — FALSE CONFIDENCE (10 cases, a superset of the S1s)

**10 of 26 accepted repairs (38.5%)** were shipped while fluidfix held a
second, different, suite-passing program in `RepairResult.greens`. In every one
the reported reason is the bare `engine law: BUILT -> SHIP` and the
human-readable output is only the one-line diff. `greens` is never printed by
`cli.py::cmd_repair` (which prints `result.summary()`) nor by
`guard.py::GuardReport.summary()`; it exists only under `--json`, which the
guard never uses. A user of the documented commands is told a unique repair was
found when the run established no such thing.

The six non-S1 members of this set happened to ship the original — by kind
ordering, not by evidence:

```
runs/02   greens=['return revenue - cost',      'return cost + revenue']
runs/28   greens=['return demand - supply',     'return supply + demand']
runs2/07  greens=['return limit - used',        'return used + limit']
runs2/26  greens=['return size * page - size',  'return size + size * page']
runs2/28  greens=['return page * size - size',  'return size + page * size']
runs2/32  greens=['return arrivals - served',   'return served + arrivals']
```

`RepairResult.restored_original` — the git-HEAD provenance check that would
have returned False for all four S1s in a real repo — is computed at
`loop.py:226` and then **never surfaced anywhere**: `grep -rn restored_original
src/` finds only its definition, its assignment, and one CHANGELOG line. It
gates nothing and is printed by nothing.

**Classification: `wording`** for the six that shipped the original (right
outcome, report claims a uniqueness the run did not establish), and the same
`observation` defect above for the four that did not.

### S2, S4 — none

0 of 6 refusals left a dirty tree. Every refusal named a cause that matches
what happened in that run (section 5). No hang, no non-termination.

### Not byte-exact but not wrong (1 case)

`runs2/26`: original `return page * size - size`, shipped
`return size * page - size`. Multiplication commutes, so this is the same
program respelled — not an S1, but it is a counterexample to a literal reading
of "byte-exact". Reported here rather than folded into the S1 count.

## 5. What defended

  * **`set_amb` — two greens inside ONE candidate set.** Held every time it
    applied. `runs2/21` (`{"cache": True, "trace": False}` under
    `any(v is True for v in d.values())`) is the canonical weak-assert family
    and it was refused, with the tree restored to the defect byte for byte.
  * **`len(sites) > 1` — greens at two different lines.** Held. `runs/18`
    found four greens on line 53 and refused.
  * **The green-suite precondition.** All 33 undetected defects produced
    "no failing test — nothing to repair" rather than a search. `loop.py`'s
    comment on this is exactly right and it is why the undetected defects are
    excluded from the denominator rather than counted as failures.
  * **Refusal honesty.** All 6 refusals were accurate:
    `runs2/10` "no observation named a kind this vocabulary can repair" — the
    mutated line `return list(range(count))` genuinely matches no kind regex;
    `runs/15`, `runs2/13`, `runs2/30` "every candidate left the suite red" —
    true, the repairs need an *increment* and the vocabulary only decrements;
    `runs/18`, `runs2/21` AMBIGUOUS — true and correctly explained.
  * **Rollback.** 0 dirty trees across 32 searches, including the syntax-error
    defects (`runs/16`, `runs2/11`, `runs2/24`) where candidates were rejected
    at compile time.
  * **The free syntax rejection** kept the search cheap: every accepted repair
    took 3 suite runs and under 2.6s.

The one defence that did not exist is the one this attack needs: nothing
anywhere compares two greens to each other.

## 6. Verdict

**fluidfix held on rollback, refusal honesty and the two AMB terms it does
measure, and did not hold on the one it does not: over 32 defects that a weak
suite actually detects it shipped a different program from the original 4 times
(12.5%; 15.4% of its 26 accepted repairs) and reported a bare
`engine law: BUILT -> SHIP` on 10 of 26 (38.5%) while holding a second,
different, passing program it never mentioned — an `observation` defect at
`loop.py:217`, where AMB is measured as green provenance instead of green
identity, handing the law byte 0x201 (SHIP) when the run supported 0x203
(ADD_STATE).**

---

### Files

```
ATTACK.md          this report
RESULTS.txt        summarize.py output, verbatim
timeout.sh         nice -n 15 + perl-alarm timeout wrapper (no coreutils timeout here)
inject.py          exhaustive in-vocabulary defect enumerator (uses fluidfix's own appliers)
run_one.py         one defect end to end; writes runs*/NN/result.json
summarize.py       pools both victims, prints the rate table
repro_s1.sh        3-second standalone S1 reproduction
victim/  victim2/  the two pristine victim repos (library + weak suite)
defects.json  defects2.json   the enumerated defects
runs/  runs2/      one directory per defect: the repo as fluidfix left it, plus result.json
repro/  repro_guard/          the two standalone reproductions, left as they finished
```

Rerun everything:

```sh
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/03-weak-assert
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin
./timeout.sh 60 $V/python inject.py
for i in $(seq 0 31); do ./timeout.sh 400 $V/python run_one.py $i; done
VICTIM=victim2 PKG=weakpkg2 RUNS=runs2 DEFECTS=defects2.json ./timeout.sh 60 $V/python inject.py
for i in $(seq 1 33); do VICTIM=victim2 PKG=weakpkg2 RUNS=runs2 DEFECTS=defects2.json \
    ./timeout.sh 400 $V/python run_one.py $i; done
./timeout.sh 60 $V/python summarize.py
```
