# 04-tautological-test — tests that pass no matter what

RED TEAM agent 04, 2026-09-07. fluidfix at `/Users/kanchetidevieswar/neo/fluidfix`
(`.venv/bin/fluidfix`, mechanical observer, zero tokens, defaults everywhere).
Every run: `nice -n 15` + the `./tmo` perl-alarm timeout wrapper, one at a time.
No fluidfix source, env var, or git state was touched.

---

## 1. Target

Build suites that cannot fail — `assert True`, a swallowing `try/except`, a test
that never calls the function, an assertion inside a branch that never runs, an
empty `parametrize` — and find out whether fluidfix notices it has no oracle, or
"repairs" against one anyway.

---

## 2. Attack design

fluidfix's entire soundness argument is one sentence: *the suite is the judge*.
`loop.py` collects every candidate that turns the suite green, and the engine law
is asked once with three measured bits — `BUILT` (something went green), `AMB`
(two greens, or greens at two lines), `CAPPED` (budget cut the search). One green
and nothing else is `BUILT` alone, which rules `SHIP`.

The gap I attacked is not in that law. It is that **a hollow test and a real test
are byte-identical inputs to it.** Both contribute "passed" to the exit code.
Nothing in `src/fluidfix/` measures whether the suite has any power to
discriminate: the only oracle-integrity checks that exist are
`oracle.py::_EXIT_MEANING` (pytest collected nothing / usage error / internal
error) and `oracle.py::_still_reports_failures` (exit 0 while the summary still
prints failures). The second is explicitly a defence against *a candidate that
silences the oracle*. Neither fires when the oracle was **already silent before
fluidfix arrived**.

So the prediction was: fluidfix does not need a hollow suite to be told apart,
and a hollow suite does not make it refuse — it makes it *more* decisive, by
deleting the greens and the rejections that would otherwise have produced `AMB`
or `REFUTED`. A weaker suite is, to this design, a *cleaner* signal.

Concretely I wanted a case where a hollow test removes the only rejection, so a
**compensating** edit becomes the unique green and is shipped as a repair.

### The victim (`fixtures/*/net.py`, identical in every arm)

```python
"""Invoicing and payroll arithmetic."""

BONUS = 8


def gross(units, price):
    return units * price + units      # <- SEEDED DEFECT, correct: units * price
                                      #    (out of fluidfix's vocabulary: no act
                                      #     deletes a term)

def invoice(units, price):
    return gross(units, price) + BONUS


def payslip(hours):
    return hours * BONUS
```

`BONUS = 8` and `payslip` are **correct code**. One genuine, correct test is red:

```python
def test_invoice_one_unit():
    assert invoice(1, 10) == 18       # correct: 1*10 + 8; defective: 11 + 8 = 19
```

The true fix is out of vocabulary, so it can never go green. But decrementing the
*correct* constant `BONUS` by one cancels the +1 the defect adds:
`11 + 7 == 18`. That candidate is in vocabulary (kind 1, literal-off-by-one) and
it is the only green — **provided nothing else pins `BONUS`.** The suite contains
a test that appears to pin it exactly (`assert payslip(3) == 24`). In one arm it
is honest; in the other it is one of the five tautologies.

---

## 3. Attempts

### Attempt 1 — every test tautological, suite therefore green. **DEFENDED.**
`fixtures/f1_allhollow` — the defective `net.py` plus five hollow tests and
nothing else. Baseline: `4 passed, 1 skipped`.

```
[14:36:43] suite green — nothing to do
  TREE: byte-identical
```

`loop.py:repair()` refuses before anything runs (`if oracle.green(): reason =
"no failing test — nothing to repair"`), and `guard_once` short-circuits on
`oracle.failing_output()`. **Not a finding** — a refusal with a correct reason.
Worth recording as a limit, though: the reason given is "nothing to do", and the
user is never told that their suite is green because it is incapable of being
anything else, on code that is demonstrably broken.

### Attempt 2 — an oracle that can never be satisfied. **DEFENDED.**
`fixtures/f2_unsat` — hollow suite plus `def test_cannot_pass(): assert False`.
No edit to `net.py` can green it.

```
[14:36:46] REFUSED: fault is outside the taught vocabulary (candidate files tried: none found).
  TREE: byte-identical
```

Honest refusal, bounded, tree untouched. **Not a finding.**

### Attempt 3 — the A/B. **SUCCEEDED (S1).**
`fixtures/f3_real` and `fixtures/f3_hollow`: byte-identical `net.py`
(`sha256 7798b9d8…`), the *same* single failing test, the same failure text
(`assert 19 == 18`). The only difference is that the three tests which mention
`BONUS`/`payslip` are honest in one arm and tautological in the other.

Honest arm:

```
[14:34:32] REFUSED: fault is outside the taught vocabulary (candidate files tried: net.py).
  hint: every generated candidate was rejected by the suite
        (engine law: REFUTED -> HARVEST_COUNTEREXAMPLE)
=== f3_real net.py unchanged? === BYTE-IDENTICAL
```

with, in `logs/f3_real.last_refusal.json`:

```json
{ "at": "net.py:3", "tried": "BONUS = 7",
  "why": "FAILED tests/test_bonus.py::test_bonus_constant - assert 7 == 8" }
```

Hollow arm — same code, same red test, candidate no longer killed:

```
[14:34:00] net.py: repaired line 3 in 6 suite runs (2.0s):
  - BONUS = 8
  + BONUS = 7
```

### Attempt 4 — flavour ablation, one pinning test in six spellings. **5/5 shipped.**
`fixtures/f4_*`: two tests only — the honest red `test_invoice_one_unit`, and one
pinning `test_payslip_three_hours` written six ways.

| pinning test | spelling | outcome | tree |
|---|---|---|---|
| `f4_honest` | `assert payslip(3) == 24` | **REFUSED** (correct) | byte-identical |
| `f4_swallow` | `try: assert … except AssertionError: pass` | **repaired** `BONUS = 8` → `7` | mutated |
| `f4_nevercalls` | `assert net.payslip is not None` | **repaired** `BONUS = 8` → `7` | mutated |
| `f4_deadbranch` | `for _ in []: assert payslip(3) == 24` | **repaired** `BONUS = 8` → `7` | mutated |
| `f4_emptyparam` | `@parametrize("hours,expected", [])` | **repaired** `BONUS = 8` → `7` | mutated |
| `f4_asserttrue` | `assert True` | **repaired** `BONUS = 8` → `7` | mutated |

Every tautology flavour named in the target is individually sufficient. Nothing
about the outcome distinguishes them from each other or from a real suite.

### Attempt 5 — could the hollow suite instead trip `AMB`? **No — it does the opposite.**
I expected the hollow suite might create ambiguity. It removes it. `AMB` needs a
*second* green; hollowing tests never adds greens, it only deletes the
*rejections*. `logs/f3_hollow.repair.json` reports `"ambiguous": false,
"greens": ["BONUS = 7"]`. Hollow suites make fluidfix look **more** certain, not
less. This is why the attack is cheap: the defence that exists (AMB) is
structurally unable to fire on this shape.

### Attempt 6 — S2 (corruption) on the refusal paths. **Failed, defence held.**
Every refusing arm (`f1`, `f2`, `f3_real`, `f4_honest`) left `net.py` byte-identical
to the pristine `sha256 7798b9d8…`; `.fluidfix/inflight.json` was cleared in all
runs. `loop.py`'s `finally: _write(path, src)` and the journal did their job.

---

## 4. Outcome

### S1 — WRONG REPAIR SHIPPED

**Reproduction**

```sh
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/04-tautological-test
./build_fixtures.sh
cd fixtures/f3_hollow
../../tmo 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard . --budget 180
```
(`./reproduce.sh` runs all ten fixtures, ~60s, one at a time.)

**What fluidfix reported**

```
[14:34:00] net.py: repaired line 3 in 6 suite runs (2.0s):
  - BONUS = 8
  + BONUS = 7
```
exit 0. `"repaired": true, "refused": false, "ambiguous": false,
"greens": ["BONUS = 7"], "reason": "engine law: BUILT -> SHIP"`.

**The diff fluidfix wrote** (`logs/f3_hollow.shipped.diff`)

```diff
--- net.py (pristine)
+++ net.py (after fluidfix)
@@ -1,6 +1,6 @@
 """Invoicing and payroll arithmetic."""

-BONUS = 8
+BONUS = 7


 def gross(units, price):
```

**Why this is S1 and not a green-only imposter.** `docs/SCALE.md:41` already
concedes "byte-exactness is bounded by suite strength" — a *suite-equivalent*
line that behaves the same. This is not that. The shipped program is
observably **wrong, in more places than before fluidfix ran**:

```
gross(1,10)  = 11   (correct 10)   <- the actual defect, untouched
payslip(3)   = 21   (correct 24)   <- NEWLY BROKEN by the shipped edit
BONUS        = 7    (correct 8)    <- NEWLY BROKEN by the shipped edit
invoice(1,10)= 18                  <- right answer, two wrongs cancelling
```

fluidfix edited a correct line, left the defect in place, and reported a repair.
README.md's headline table ("silently wrong repairs: **0**") and README.md:7
("Every output is either a repair your suite accepts … or an explicit refusal")
are both literally satisfied and materially wrong here: the suite *did* accept
it, because the suite cannot reject anything.

**Classification: `observation`.**

- Observation byte passed to the law:
  `situation(BUILT=True, AMB=False, CAPPED=False)` = `0x201` = **513**
  (bits 8–9 = 2 are the constant DEBUG job field).
- Act the law returned: **`SHIP`** — verified directly:
  ```
  $ .venv/bin/python -c "from fluidfix.engine import decide, situation
  print(hex(situation(BUILT=True,AMB=False,CAPPED=False)), decide(situation(BUILT=True,AMB=False,CAPPED=False)))"
  0x201 SHIP
  ```
- **The law is not at fault.** On `0x201` `SHIP` is right. The two honest
  outcomes were both available from the same law and both unreachable:
  `0x203` (`BUILT+AMB`) → `ADD_STATE` ("refuse, ask for one pinning test"), and
  `0x240` (`REFUTED`) → `HARVEST_COUNTEREXAMPLE`, which is exactly what the
  honest arm produced from identical code.
- The defect is that `BUILT` was measured from an oracle with **zero
  discriminating power at the repair site**, and no bit in
  `BITS = [BUILT, AMB, UNREAD, NOTWIN, HIDDEN, CAPPED, REFUTED, SELF]` encodes
  that. The body measured "the suite went green" and delivered it as "the
  program is right". `NOTWIN` is the unallocated bit whose name fits the
  situation, and `engine.py` documents it as never set.

**A free observation that would have separated the two arms.** fluidfix already
collects it and throws it away. In `RepairResult.tried_log` every rejection
carries the test that killed it:

```
f4_honest  -> 2 distinct killing tests: test_invoice_one_unit, test_payslip_three_hours
f3_real    -> 2 distinct killing tests: test_invoice_one_unit, test_bonus_constant
f3_hollow  -> 1 distinct killing test:  test_invoice_one_unit          (SHIPPED)
```

When *every* rejection in the entire search is attributed to the test that was
already failing, the suite has demonstrated no discriminating power beyond the
one assertion that started the run, and a lone green is not evidence of
uniqueness. That count is zero extra suite runs. Report-only — I made no change
to `src/`.

### Not found
No S2 (nothing was left corrupted on any refusal path), no S3 beyond the S1
itself, no S4.

---

## 5. What defended

1. **The green-suite precondition** (`loop.py:repair()` — "no failing test —
   nothing to repair"; `guard_once`'s `oracle.failing_output()` early return).
   A wholly tautological suite is green, and fluidfix will not search a green
   tree at all. This is the single defence that makes the pure form of this
   attack impossible, and it held.
2. **`REFUTED -> HARVEST_COUNTEREXAMPLE`** with an honest suite: `f3_real` and
   `f4_honest` refused, named the file, and logged `BONUS = 7` with the exact
   test that killed it. The honest arm is fluidfix working perfectly.
3. **Byte-exact rollback**: four refusing runs, four byte-identical trees,
   journal cleared each time.
4. **The unsatisfiable oracle** (`assert False`) produced a bounded honest
   refusal, not a grind and not a guess.
5. `_still_reports_failures` and `_EXIT_MEANING` — not exercised here, but they
   are the reason I could not reach this by making the *candidate* silence the
   oracle; I had to make the suite silent beforehand.

---

## 6. Verdict

**fluidfix held against a fully tautological suite (it refuses to search a green
tree) but did not hold against a partly tautological one: with one honest failing
test and one hollow pinning test, all five tautology flavours shipped
`BONUS = 8` → `BONUS = 7` — an edit to correct code that leaves the real defect
in place and newly breaks `payslip` — as `engine law: BUILT -> SHIP` on byte
`0x201`, a correct ruling on an observation that never measured whether the
oracle could reject anything (classification: observation, `NOTWIN` unset).**

---

### Files kept

| path | what |
|---|---|
| `build_fixtures.sh` | regenerates all ten fixtures from scratch, idempotent |
| `reproduce.sh` | runs all ten, one at a time, prints tree state + shipped behaviour |
| `tmo` | the timeout wrapper (`nice -n 15` + perl alarm + process-group kill) |
| `fixtures/f1_allhollow` | all tests hollow → green → refused |
| `fixtures/f2_unsat` | `assert False` → unsatisfiable → refused |
| `fixtures/f3_real`, `fixtures/f3_hollow` | the headline A/B |
| `fixtures/f4_{honest,swallow,nevercalls,deadbranch,emptyparam,asserttrue}` | flavour ablation |
| `logs/f3_hollow.guard.log`, `logs/f3_hollow.repair.json` | the shipping run, human + machine report |
| `logs/f3_hollow.shipped.diff`, `logs/f3_hollow.net.py.AFTER` | what was written to disk |
| `logs/f3_real.guard.log`, `logs/f3_real.last_refusal.json` | the control refusal, with `BONUS = 7` rejected |
| `logs/f4_*.guard.log` | the six ablation runs |

Pristine `net.py` in every fixture:
`sha256 7798b9d80c23f156f5760e18c42680f00419ade5625c5bf84c9081b30dccb853`.
All fixtures were restored to it after the runs.
