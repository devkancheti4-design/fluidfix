# 09-spelling-vs-program — the ambiguity proxy measures provenance, not identity

## 1. Target

Attack surface C: `loop.py:_rule` computes the engine law's AMB bit as
`set_amb or len(sites) > 1`. Build the fixture pair that separates "one program
spelled twice" from "two genuinely different programs", show the proxy wrong in
both directions, and propose (report only) the observation that would separate
them.

## 2. Attack design

`engine.py` documents the AMB bit as *"two DIFFERENT candidates both pass the
suite"* — different **programs**, whose ruling ADD_STATE means "the suite cannot
tell them apart, ask for a pinning test". `loop.py` measures something else
entirely:

```python
ruling = decide(situation(BUILT=True,
                          AMB=set_amb or len(sites) > 1,
                          CAPPED=capped))
```

* `set_amb` — two greens arrived inside **one candidate set** (one act, one line).
* `len(sites) > 1` — greens arrived at **different line numbers**.

Both terms are questions about *where a green came from*. Neither is a question
about *what the green computes*. So the discriminator fluidfix actually uses is
**provenance**, and the property it needs is **program identity**. Those two are
orthogonal, which means a 2×2 exists and two of its cells must be wrong:

|                  | greens in the SAME candidate set | greens in DIFFERENT sets, same line |
|------------------|----------------------------------|--------------------------------------|
| **ONE program**  | proxy says AMB → **REFUSE (wrong)** | proxy says ¬AMB → SHIP (right)     |
| **TWO programs** | proxy says AMB → REFUSE (right)  | proxy says ¬AMB → **SHIP (wrong)**  |

The proxy decides on the **column**. The truth is the **row**. Building all four
cells turns "the proxy is a proxy" from an argument into a measurement, and makes
the two failures unarguable, because the two correct cells are correct *by
coincidence of column*, not by reasoning.

fluidfix's own source states the intended semantics and names the exact fixture
that breaks it (`loop.py`, inside `_rule`):

> What is NOT ambiguity: two SPELLINGS of one program reached by different acts
> at one site — `units >= 10` and `units > 9` are the same program written
> twice, and refusing those would refuse the commonest bug class there is.

Note "reached by **different acts**". The comment describes the cell the proxy
gets right and does not consider the cell where the same two spellings arrive
inside one act's candidate set. Fixture **A2** is literally that comment; fixture
**A1** is the same truth in the other column.

Everything below uses the shipped zero-token `MechanicalObserver` and the shipped
fault vocabulary. No dictionary, no LLM, no env var, no edit to `src/`.

## 3. Attempts

Every run: `nice -n 15` plus a `perl`-alarm hard timeout (`run.sh`, written
because this host has no coreutils `timeout`), one at a time.

### 3.1 Choosing a construction that survives the `tried` set (design, no run)

First plan was to reach the *same* two spellings (`units >= 10`, `units > 9`)
inside one candidate set via a taught `register()` class, so the pair would be
byte-identical across the two columns. **Abandoned after reading `loop.py`:**
`tried` is a run-global `set[(line, candidate)]`, and user kinds live at 4..7,
so kinds 0 and 1 always fire first and pre-consume both spellings; the taught
set then contributes nothing and `set_amb` never sets. Recorded as a defence of
sorts — the global `tried` set makes the same-set cell unreachable for any class
whose spellings a shipped act can also produce. The construction had to come
from a *single shipped act* that emits two spellings of one program on its own,
which `_reduce_literal` does whenever one line carries two additive constants.

### 3.2 The four cells (all run, all reproduced)

```
cd research/adversarial-2026-09-07/09-spelling-vs-program && ./reproduce.sh
```

Each cell is a 6-line module and a 2-test suite under `fixtures/`; the script
copies the fixture to `work/`, runs `fluidfix repair … --json`, and diffs
`mod.py` against its pristine copy. Raw output in `logs/*.json`.

**A1 — one candidate set, ONE program.** `return payload + 4 + 4` where the
header constant should be 3. Kind 1 → act 6 (`_reduce_literal`) proposes both
decrements in one set:

```
greens : "    return payload + 3 + 4"
         "    return payload + 4 + 3"
result : refused, ambiguous=true, acts_tried=[6], suite_runs=3
reason : AMBIGUOUS: 2 candidates at 1 different lines (6) all pass the suite …
         one may CANCEL the fault rather than repair it …
         (engine law: BUILT+AMB -> ADD_STATE, never guess)
mod.py : unchanged
```

**A2 — two candidate sets, same line, ONE program.** `return units > 10` where
the rule is "ten or more". Kind 0 → act 5 gives `units >= 10`; kind 1 → act 6
gives `units > 9`.

```
greens : "    return units >= 10"
         "    return units > 9"
result : repaired, ambiguous=false, acts_tried=[5,6,15], reason "engine law: BUILT -> SHIP"
diff   : -    return units > 10
         +    return units >= 10
```

**B1 — one candidate set, TWO programs.** `return opening + spend + income`
where `spend` should be subtracted; the suite only pins `balance(1,1,1) == 1`,
so flipping *either* `+` is green. Kind 3 → act 8 emits both in one set.

```
greens : "    return opening - spend + income"     (the real repair)
         "    return opening + spend - income"     (a compensating one)
result : refused, ambiguous=true, acts_tried=[7,8]
mod.py : unchanged
```

**B2 — two candidate sets, same line, TWO programs.** `return subtotal - tax`
where the docstring says "the subtotal plus the tax charged on it"; the suite
only pins a zero-subtotal line. Kind 2 → act 7 (`_swap_return_operands`) gives
`tax - subtotal`; kind 3 → act 8 gives `subtotal + tax`. Kind 2 owns the lower
mask bit, so the wrong one is `greens[0]`.

```
greens : "    return tax - subtotal"      <- SHIPPED
         "    return subtotal + tax"      <- the correct repair, found and discarded
result : repaired, ambiguous=false, reason "engine law: BUILT -> SHIP"
diff   : -    return subtotal - tax
         +    return tax - subtotal
```

### 3.3 Same two cells through the product surface

`fluidfix repair` is a sub-command; `fluidfix guard` is the commit-and-forget
product. Re-run to confirm the S1 is not an artefact of the smaller entry point:

```
./guard_check.sh
```

B2 through `guard`: `mod.py: repaired line 6 in 3 suite runs (2.1s)`, exit 0,
`tax - subtotal` on disk. A1 through `guard`: refused, exit 2, file unchanged —
**with a headline reason that is false** (see 4.3).

### 3.4 Ground truth, decided mechanically

```
/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python equivalence.py    # logs/equivalence.txt
```

`equivalence.py` reads the `greens` fluidfix itself reported, rebuilds a module
per green, and differential-tests the enclosing function on inputs the suite
never used:

```
A1  ONE PROGRAM   identical on all 1005 inputs         probe 0.0001s   fluidfix: REFUSED
A2  ONE PROGRAM   identical on all 1005 inputs         probe 0.0001s   fluidfix: REPAIRED
B1  TWO PROGRAMS  balance(-97,-97,-3) = -3 vs -191     probe 2 evals   fluidfix: REFUSED
B2  TWO PROGRAMS  total_due(-97,-97) =  0  vs -194     probe 1 eval    fluidfix: REPAIRED
```

A1's pair is exactly equal for every Python `int` by associativity and
commutativity of integer `+`; A2's is fluidfix's own worked example of a program
spelled twice. The two-program cells were refuted on the **first** and **second**
evaluation.

### 3.5 The engine byte, printed not asserted

```
/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python law_bytes.py      # logs/law_bytes.txt
```

```
fixture                      proxy AMB    byte law says   true AMB    byte law would say  verdict
A1-same-set-one-program           True     515 ADD_STATE     False     513 SHIP        WRONG  <<<
A2-cross-set-one-program         False     513 SHIP          False     513 SHIP        OK
B1-same-set-two-programs          True     515 ADD_STATE      True     515 ADD_STATE   OK
B2-cross-set-two-programs        False     513 SHIP           True     515 ADD_STATE   WRONG  <<<
```

**On the correct byte the law rules correctly in all four cells.** Nothing here
is a `ruling`.

### 3.6 Attempts that produced nothing (recorded as defences)

* Trying to get a taught kind-4 class to contribute the second spelling of a
  pair whose first spelling a shipped act had already produced — blocked by the
  run-global `tried` set (3.1).
* Trying to make A1's two greens land at different *sites* as well, to see the
  `len(sites) > 1` term misfire on one program: not attempted to completion; a
  single-line fixture cannot produce it, and a two-line construction is agent
  06's surface. Stated as an untested corollary in §6, not as a finding.

## 4. Outcome

### 4.1 S1 — WRONG REPAIR SHIPPED (B2)

**Reproduction**

```
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/09-spelling-vs-program
rm -rf work/guard-B2 && cp -R fixtures/B2-cross-set-two-programs work/guard-B2
./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard work/guard-B2 \
    --python /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
```

**Diff fluidfix wrote**

```diff
--- work/guard-B2/mod.py.pristine
+++ work/guard-B2/mod.py
@@ -3,4 +3,4 @@
 def total_due(subtotal, tax):
     """Amount owed: the subtotal plus the tax charged on it."""
-    return subtotal - tax
+    return tax - subtotal
```

fluidfix reported `repaired line 6 in 3 suite runs`, exit 0. The invoice module
now computes `tax - subtotal`: `total_due(50, 7)` is `-43` where the docstring
and the committed intent say `57`. The suite is green, so nothing downstream
will ever notice. **The correct repair was found in the same run** — it is
`greens[1]` in `logs/B2-cross-set-two-programs.json` — and discarded by the
tie-break, not by the search.

**Classification: `observation`.**

* Observation byte passed: `situation(BUILT=True, AMB=False, CAPPED=False)` =
  **513** (`0b10_0000_0001`: BUILT, plus the constant DEBUG job bits `2 << 8`).
* Act the law returned: **`SHIP`** (`ACTS[0]`), reported verbatim as
  `engine law: BUILT -> SHIP`.
* Correct byte: two greens that disagree on `total_due(50, 7)` are two different
  candidates in the law's documented sense, so AMB is true →
  `situation(BUILT=True, AMB=True, CAPPED=False)` = **515**.
* The law would have ruled **`ADD_STATE`** — refuse, ask for one pinning test.

This cell is the shipping direction that agent 07 owns; it is included because
the pair is the finding. The novel content is that the *same* proxy also fires
backwards (4.2) and that a single observation fixes both (§6).

### 4.2 S4 — DENIAL (A1)

**Reproduction**

```
cd /Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/09-spelling-vs-program
rm -rf work/guard-A1 && cp -R fixtures/A1-same-set-one-program work/guard-A1
./run.sh 300 /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix guard work/guard-A1 \
    --python /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
```

**Diff fluidfix wrote:** none — `mod.py` is byte-identical to the pristine copy.
That is the defect. The suite genuinely pins an in-vocabulary literal-off-by-one;
fluidfix generated a repair for it, confirmed it green, generated a *second
spelling of the same repair*, confirmed that green too, and refused on the
strength of having succeeded twice. Either candidate is a correct, byte-exact
repair; `payload + 3 + 4` and `payload + 4 + 3` are the same function on every
Python int.

**Classification: `observation`.**

* Observation byte passed: `situation(BUILT=True, AMB=True, CAPPED=False)` = **515**.
* Act the law returned: **`ADD_STATE`**, reported as
  `engine law: BUILT+AMB -> ADD_STATE, never guess`.
* Correct byte: the two greens are the same program, so AMB is false → **513**.
* The law would have ruled **`SHIP`**.

The user's remedy, as printed, is "Add one pinning test". No test can discharge
this refusal: no test can distinguish `p + 3 + 4` from `p + 4 + 3`, because
there is nothing to distinguish. The refusal is unfixable by the action it asks
for — which is the practical cost of a denial the user cannot argue with.

### 4.3 S3 — FALSE CONFIDENCE in the refusal headline (A1 **and** B1)

`GuardReport.summary()` (`guard.py`) recognises exactly three refusal causes:
no-pointing-evidence, budget-exhausted, and an `else` branch that prints

```
REFUSED: fault is outside the taught vocabulary (candidate files tried: mod.py).
teach it once: docs/TEACHING.md (or run: fluidfix kinds)
```

AMBIGUOUS has no branch, so **every** ambiguity refusal is headlined as a
vocabulary gap. Observed on A1 and on B1 (`logs/guard-A1-same-set-one-program.txt`,
`logs/guard-B1.txt`). It is false in both: the fault was *inside* the vocabulary,
and fluidfix repaired it — twice — before refusing. The real cause is demoted to
a `hint:` line. This is the exact failure mode the module's own comment says was
fixed for the budget case: *"Blaming the vocabulary sends the user to write a
rule they already have."*

Two further false claims inside the hint text itself, in every ambiguity refusal:

* `"2 candidates at 1 different lines (6)"` — the greens are at the **same** line.
  The message renders a same-line ambiguity through the different-lines template.
* `"one may CANCEL the fault rather than repair it"` — true for B1, **false** for
  A1, where the two greens are provably one function and neither cancels anything.

**Classification: `wording`.** The A1 outcome is separately wrong (4.2); the B1
outcome is right and is described wrongly, which makes this an independent
wording defect rather than a symptom.

## 5. What defended

* **`set_amb` works, in its column.** B1 is a real compensating-repair pair —
  `opening + spend - income` cancels the fault instead of removing it — and
  fluidfix caught it, refused, and left the tree untouched. The mechanism is
  sound; its input predicate is the wrong predicate.
* **Rollback held everywhere.** Both refusals (A1, B1) left `mod.py`
  byte-identical to the pristine copy (`diff -u` empty), `.fluidfix/inflight.json`
  cleared, no stray `.coverage`, no test file touched. Nothing in this target
  produced an S2.
* **The run-global `tried` set** blocked attempt 3.1 outright: a taught class
  cannot contribute a spelling a shipped act already tried, so the same-set cell
  cannot be manufactured from a dictionary alone. It had to be found in the
  shipped vocabulary's own behaviour.
* **Counterexample harvesting is honest.** B1's rejected `_swap_return_operands`
  candidate is logged with the test that killed it
  (`assert 3 == 1`), and A2's rejected `units < 10` likewise.
* **The re-confirm (HIDDEN) lane ran on every green.** `FLUIDFIX_CONFIRM`
  defaults to 1 and was left at its default, so no green here was accepted on a
  single run. (Aside, not claimed as a finding: `suite_runs` counts *candidates
  adjudicated*, not pytest invocations — the confirm re-check and `check()`'s
  `--lf` fast gate are not counted, so "repaired … in 3 suite runs" understates
  the pytest runs actually paid for. That belongs to 15/16, not here.)
* **The search never failed.** In B2 fluidfix *found* the correct repair. Only
  the tie-break lost it. That matters for the fix: no new search power is needed,
  only a new question asked of what the search already holds.

## 6. Proposed observation — report only, no `src/` edits

### What the bit should mean

`engine.py` already defines AMB as *"two DIFFERENT candidates both pass the
suite"*. The body should measure **`DISTINCT(greens)` — do any two greens
disagree on some input?** — and stop measuring provenance. `set_amb` and
`len(sites) > 1` should survive only as *hints about where to look*, never as the
bit.

### Why it is nearly free

`greens` already holds each accepted candidate as a **complete file text**
(`greens[i][1]`). fluidfix therefore already possesses both programs at the
moment it asks the law; it simply never compares them. Three tiers, in cost order:

1. **Syntactic prefilter (free, sound one way).** `ast.dump(ast.parse(a)) ==
   ast.dump(ast.parse(b))` ⇒ certainly one program. Catches comment- and
   whitespace-only differences at zero cost. Fires on neither A1 nor A2, so it is
   necessary but not sufficient — which is precisely why the proxy cannot be
   fixed syntactically.
2. **Behavioural probe (the separator).** The edited line's enclosing
   `FunctionDef` is one `ast.walk` away — fluidfix already knows the file and the
   lineno. Import each green's module in a subprocess and evaluate that function
   on: (a) the argument tuples the suite itself already passes, harvested from
   one traced run of the passing tests (fluidfix runs the suite 3–4 times per
   fixture already, so this is amortised to nothing); (b) a small perturbation of
   those — each integer ±1, 0, negated, and **arguments swapped**, which is what
   refutes B2 on the first sample; (c) a fixed spread of ints. Any disagreement
   ⇒ AMB = 1.
3. **Fail closed.** If the probe cannot run — the enclosing function is not
   callable in isolation, has side effects, raises on perturbed inputs — set
   **AMB = 1** and refuse. Do *not* fall through to today's proxy. "I could not
   decide" must mean "ask the user", never "ship `greens[0]`". Today the fallback
   points the other way, which is how B2 ships.

### Measured cost of tier 2, in this directory

`equivalence.py` decided all four cells: the two-program cells were refuted on
evaluation 1 and 2; the one-program cells ran 1005 evaluations in **0.1 ms**. One
bare run of these two-test suites, measured on this host, is **0.204 s**. The
probe is ~2,000× cheaper than a **single** suite run, against a search that
already pays three or four of them per fixture.

### What it does to the law

Nothing. `law_bytes.py` shows the law ruling correctly on all four cells once AMB
carries the truth: A1 goes 515 → 513 (`ADD_STATE` → `SHIP`), B2 goes 513 → 515
(`SHIP` → `ADD_STATE`), A2 and B1 are unchanged. This is an `observation` fix,
consistent with the project's claim that no incident has ever been a `ruling`.

### Honest limit

Behavioural equivalence is undecidable in general, so tier 2 is a **refutation**
device: it can prove "two programs", and can only fail to refute "one program".
The proposal is therefore not "decide identity" but "replace an observation with
*no* evidence for the SHIP direction by one with *bounded, stated* evidence" —
and make the unrefuted-but-unprobed case refuse rather than ship. That is a
strict improvement in both directions, not a claim of soundness.

### Two cheaper interim measures, both strictly safer than today

* **(i) Drop the provenance term: `AMB = len(greens) > 1`.** Converts B2's S1
  into an S4 and costs A2 a denial. Trading a wrong ship for a refusal is the
  direction fluidfix's own doctrine argues for ("never guess"); it is a one-line
  change and it removes the S1 today.
* **(ii) Use the provenance signal already computed.** `_restored_original()` in
  `loop.py` answers "does this repair equal git HEAD at that line?" — in a
  git-backed B2 it would say **no** for `tax - subtotal` and **yes** for
  `subtotal + tax`. (Claim from reading `loop.py:148`, not from a run: the brief
  forbids creating git state, so these fixtures are not repos and the field came
  back `null` in every log.) It is computed, serialised into `repair --json`, and
  read by nothing — `grep -rn restored_original src/fluidfix/` returns three
  hits, all in `loop.py`: the dataclass field, the helper, and the single
  assignment. When exactly
  one green equals HEAD, shipping that one is not a guess, it is a restoration —
  which is the guard's stated job. It is currently computed *after* the ruling
  and only for `greens[0]`; computing it for every green before the ruling costs
  one `git show` per green.

### Untested corollary (stated as such)

The `len(sites) > 1` term should be wrong in the same way for one program spelled
at two different lines — an equivalent edit reachable at either of two places. No
fixture here demonstrates it; two-site constructions are agent 06's surface. It
is listed so the fix is not scoped to the `set_amb` term alone.

## Housekeeping

Everything this agent created lives under
`research/adversarial-2026-09-07/09-spelling-vs-program/`. `src/`, `tests/`,
`docs/` and the shared clones were not touched, and no git command that changes
state was run.

One observation for the coordinator, not a finding against fluidfix: at the end
of this run `git status --porcelain` in the fluidfix repo reports
`M CHANGELOG.md`, containing a correction to the 0.13.0 flaky-suite entry
(agent 05's subject matter). This agent did not write it. Flagging it because
the brief confines every red-team agent to its own directory, and shared repo
state is now dirty.

## 7. Verdict

fluidfix held on rollback, on counterexample honesty, and on same-set ambiguity —
but its ambiguity bit measures **which act produced a green**, not **what the
green computes**, so it shipped `tax - subtotal` as a repair for
`subtotal + tax` (S1, `observation`, byte 513 → `SHIP` where byte 515 → `ADD_STATE`)
and refused a correct in-vocabulary repair for being correct twice (S4,
`observation`, byte 515 → `ADD_STATE` where byte 513 → `SHIP`); the law was right
on every byte it was given.
