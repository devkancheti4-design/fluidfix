# fluidfix — the whole proof, with the boundaries

Every number here came from a run on this machine against real code. Each
claim names the command that reproduces it and the limitation that bounds
it. Where a trial failed, the failure is here too — the failures are why
the successes are worth anything.

---

## 1. The claim

**Your tests catch the regression. fluidfix restores the code.** It repairs
what it has been shown one example of, proves every repair with your own
suite, and refuses everything it cannot prove — leaving the tree
byte-identical and telling you exactly what it tried.

It is not a linter, not a detector, not a model writing code. Three
machine-authored integer laws decide; your suite is the only judge.

---

## 2. One example teaches a CLASS — 5/5, reproducible in 11 seconds

```bash
python3 docs/proof_one_example.py
```

One worked example is taught (`.get(key)` with no default, letting `None`
poison arithmetic). Then five **different** members of that class are
injected — different files, names, keys, arithmetic, a loop accumulator,
and two members on one line — with **nothing further taught**:

| member | what differs | result |
|---|---|---|
| `billing.py` | different key + accumulator | byte-exact, 4 suite runs |
| `metrics.py` | different file, quoting, multiplication | byte-exact, 5 runs |
| `scoring.py` | different names, subtraction, nested call | byte-exact, 3 runs |
| `cart.py` | member inside a loop | byte-exact, 4 runs |
| `report.py` | **two** members on one line | byte-exact, 5 runs |

**5/5 byte-exact.** The control — a bug *outside* the class — was refused
with the tree untouched and the killing test named
(`tried 'return w * 2' -> FAILED test_cost - assert 4 == 11`).

CI-enforced: `tests/test_one_example_generalises.py`. If one example ever
stops generalising, the build goes red.

---

## 3. Left alone on a real repo (click — 28,581 LOC, 1,990 tests)

Three rules taught, one worked example each (`company_rules.py`:
boundary-off-by-one, constant-drift, sign-flip). No file named, no line,
no hint. One regression at a time, as they actually occur. Pass mark is
**byte-identical to the pristine baseline**, not merely "tests pass".

| regression | tests broken | verdict | time |
|---|---|---|---|
| `testing.py:726` constant drift | 28 | **byte-exact**, committed | 138 s |
| `formatting.py:143` constant drift | 15 | **byte-exact**, committed | **36 s** (8 suite runs) |
| `_textwrap.py:109` constant drift | 244 | *(see §7 — blast radius)* | |

fluidfix authored its own commits: `fluidfix: restore src/click/formatting.py:143`.

**The scaling law this exposes:** repair time tracks *how noisy the failure
signal is*, not how big the repo is. 15 failing tests → 36 seconds. 244
failing tests → minutes, because every rejected candidate replays all 244.
A guard running on every push lives in the 1–20 failure regime.

---

## 4. It lands the fix — not just validates it

A bare `fluidfix guard .` in CI validates a repair and then throws it away
with the runner. The GitHub Action pushes it back:

```yaml
- uses: devkancheti4-design/fluidfix@master     # mode: push (default)
```

Live, public, reproducible: **github.com/devkancheti4-design/fluidfix-action-demo**
— a regression was pushed, and GitHub's runner repaired it byte-exact and
pushed the restore commit back to `main` in a **23-second job**. The commit
history shows `baseline → ship a regression → fluidfix: restore billing.py:2`.

---

## 5. Large-repo benchmarks (seeded, no cherry-picking)

Protocol, raw logs and every autopsy: [SCALE.md](SCALE.md).

- click / arrow / sortedcontainers, seeded mutation sites, serial runs:
  **14/18 byte-exact**, 3 safe refusals each with a named cause, **0 wrong
  repairs**; out-of-vocabulary safety 3/3 refused.
- All four v0.5 misses were later replayed byte-faithfully and **all four
  now repair byte-exact** (v0.6.1).
- Coordinated two-line defects (neither line fixable alone, triple-liveness
  proven): **3/4 byte-exact atomic repairs** via `SpanEdit`.
- **Zero wrong repairs across every benchmark ever run in this project.**

---

## 6. What it refuses — and how loudly

A refusal leaves the tree byte-identical and writes
`.fluidfix/last_refusal.json` naming every rejected candidate **with the
test that killed it** (engine law: `REFUTED -> HARVEST_COUNTEREXAMPLE`):

```
tried mod.py:6  'if (units > 10) {'  ->  BillingTest.boundaryGetsDiscount:8 expected:<15> but was:<0>
```

Ambiguity is refused too: when two *different* candidates both satisfy a
weak suite, fluidfix refuses and asks for one pinning test rather than
guessing (`BUILT+AMB -> ADD_STATE`). It never ships a repair whose
uniqueness it could not prove — including under a wall-clock deadline.

---

## 7. The boundary — measured on 21 years of enterprise history

SQLAlchemy: 18,270 commits, 21.2 years, 201,066 source LOC, 880 authors.
Mining every one-line bug fix in real code (docstring prose excluded via
AST) gives 44 fixes in 6 classes, 4 of them recurring — **95% of fixes
belong to a class the repo had already seen.**

Recurrence, however, is **not** repairability. Teaching one example per
class and replaying 38 later real bugs:

| outcome | count |
|---|---|
| exact fix inside the 32-candidate budget | 2/38 |
| exact fix generated but ranked past it (rank 42 … 10,563) | 23/38 |
| exact fix never generated | 13/38 |

**What actually decides whether one example pays off is the size of the
answer set, not how often the class recurs.**

- **Rule-shaped classes have one answer** ("add the missing default",
  "flip the operator", "the constant drifted"). One example covers the
  family forever. This is §2 and §3 — and it is most of what breaks a
  deployed service.
- **Value-shaped classes have as many answers as your file has names.**
  fluidfix mines them and your suite judges, but the correct name can rank
  in the thousands. `--max-candidates` reaches further when your suite is
  cheap; otherwise it refuses. Safely, and worth nothing.

Sell on answer-set size, never on recurrence. Ask: *when this class hits
you, is the right answer derivable from the line and the file, or does
someone have to know it?*

Third independent confirmation (arrow, click, SQLAlchemy) that mature,
heavily-reviewed OSS libraries are **not** the customer for a paid
dictionary. Run `prove/quote.py` on the prospect's repo and let their own
history decide — including telling them not to buy.

---

## 8. Bugs this testing found in fluidfix itself (all fixed, all pinned)

The trials were run to break the product, and they did:

- **A suite that never ran looked identical to a failing suite.** SQLAlchemy
  collects 1,466 tests with `-p no:cacheprovider` and **zero** with the
  cache provider that `--lf` requires — so every candidate scored red and a
  21-minute run ended in "outside the taught vocabulary" when the truth was
  that no test had executed. pytest exit 3/4/5 now raise `HarnessError`
  naming the cause.
- **…but a candidate in the tree owns whatever pytest chokes on**, so
  `check()` rejects rather than aborting the run. Only baseline judgments
  raise. (My first fix over-reached; the suite caught it.)
- **The fail-fast optimization now disables itself** on harnesses that
  cannot support it, instead of breaking the run.
- **Two paths cited the engine law in strings while branching on hardcoded
  conditions.** Both now consult `decide()`, and a test parses every
  "engine law: X → Y" claim in the shipped source and re-derives it from the
  vendored law, so a comment can never drift from the ruling it names.
- **The candidate cap was calibrated for full-suite costs**, before
  fail-fast made rejections ~10× cheaper. It is now a budget
  (`--max-candidates`), not a wall.

---

## 9. The three kernels, and the audit

| repo | role |
|---|---|
| [fluid-router](https://github.com/devkancheti4-design/fluid-router) | **decides** — routes a fault kind to its repair in four integer instructions; verified on all 4,096 cases |
| [fluid-router2](https://github.com/devkancheti4-design/fluid-router2) | **drives** — EMIT/ADVANCE/HALT over the candidate mask; 256 states, termination proved |
| [dev](https://github.com/devkancheti4-design/dev) | **governs** — the engine law: escalate, refuse, harvest, or ship |
| [proven-reason](https://github.com/devkancheti4-design/proven-reason) | **proves** — authors the smallest rule from examples, then checks all 4,294,967,296 int32 inputs |

The fusion is audited, not asserted: fluidfix's copy of the engine law is
byte-identical to the dev repo's (sha256 `48bf50bf…`, 1,555 chars), agrees
with it on **all 1,024 situations**, rules exactly on **all 22 measured
events**, and job-invariance is 0/256.

```bash
fluidfix selfcheck        # re-derives every law on your machine, ~1 second
```

---

## 10. What this is worth

The value is not that it is clever. It is that **it has never once shipped a
wrong repair** — across every benchmark in this project, including the ones
built specifically to break it.

That is what makes unattended operation possible. A tool that fixes 90% and
corrupts 1% cannot be left alone on a production repo at any price. A tool
that repairs a bounded class perfectly, refuses everything else, and hands
you the evidence can run on every push forever.

Price it on your own history, not on a claim:

```bash
python3 prove/quote.py /path/to/your/clone
```

It prints every input it measured and will tell you not to buy when your
history says so.
