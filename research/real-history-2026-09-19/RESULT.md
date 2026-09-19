# Testing the four growth claims — 2026-09-19

The fluidnet page carried four ideas under a banner saying none of them had been measured, each with a
`needs:` line. This tests them. **Two are much weaker than the page implied, one is structurally wrong as
written, and one cannot be tested the way we proposed.** The measurements are below; the page and the call
prep need changing.

---

## Claim 2 and 3 — shape coverage, and learning from a team's history

> *Self-healing CI* — needs shape coverage of real incidents, the number we do not have.
> *Learning from one team's history* — needs a real incident history, not a corpus we generated.

Both wanted the same number, and git has it. Four real repositories — click, arrow, rich,
python-sortedcontainers, 9,927 commits between them — mined for commits whose subject says they fix
something, touching exactly one non-test Python file, at most 40 changed lines, no merges or reverts.
**289 such commits.** Every diff measured, never read.

### Two corrections were needed before the number meant anything

| pass | said | why it was wrong |
|---|---|---|
| 1 | 46% of real fixes replace exactly one line | counts typos and translated strings as fixes |
| 2 | masking strings and comments: 66% of those touch code | a line *inside a docstring* tokenises as bare names, so prose still counted as code |
| 3 | the rule used here | **a change our own abstraction cannot see is not a change to the program's shape** |

The third rule is the one a repair tool must obey anyway: it is exactly the set of edits whose difference
the tool has no way to represent.

### The result

| | n | of one-liners | of all 289 fixes |
|---|---|---|---|
| one-line diffs | 134 | — | 46% |
| … text only — prose, message, comment | 67 | 50% | 23% |
| … would not tokenise | 13 | 10% | 4% |
| … **code — the teachable space** | **54** | **40%** | **19%** |
| **the vocabulary produces the committed line exactly** | **2** | — | **0.7%** |

And one of those two "hits" is a docstring line that happens to tokenise as code, so the true figure is
**1 of 54**.

### What this does to a number we have been quoting

On our own seeded mutations we measured **22 of 38 breaks inside the taught vocabulary — 58%**. On real
history the same vocabulary reaches **under 2%**. The seeds were faults of shapes *chosen in advance*, so
that 58% measured our own choices, not the world. **It was roughly thirty times optimistic and should not
be used again.**

### Does teaching from history pay?

Only if the same transformations come back. Among the 54 real code fixes: **6 shapes recur twice or more,
covering 12 of 54 (22%)**, and the recurring ones are small syntactic repairs — `}` → `]`, a missing comma,
adding `()` — not the semantic classes worth a dictionary slot. Only three recur across repositories, all at
noise level.

**The honest read:** the ceiling for a line-rewriting vocabulary on real fixes is **19%**, not 58%; today's
reach is about **2%**; and the gap between them is real but does not obviously cluster. At n = 54 that is
suggestive, not conclusive — and four unrelated open-source libraries is the *wrong* test for "one team's
history", where idioms recur far more. That experiment still needs one team's repository.

---

# RETEST — 2026-09-19, later the same day

Asked to retest, and the retest broke my own result as well as the original claim. **Two things above are
wrong and one of them is the headline.**

## Wrong 1 — the commit filter was biased, and biased the other way

The first pass demanded a commit touch **exactly one file**. A well-made bug fix changes the code *and ships
a regression test*, so that filter excluded every properly-tested fix and kept the ones too trivial to test.
Half the survivors being typos should have been the clue.

Re-mined allowing test files alongside the one source file:

| | commits kept | one-line share |
|---|---|---|
| first pass — exactly one file in total | 289 | 46% |
| **corrected — one source file, tests allowed** | **565** | **38%** |
| … of those, shipping a regression test | 198 | **24%** |
| … no test shipped | 367 | **45%** |

**It discarded 198 fixes that came with their own regression test** — and those are nearly half as likely
to be one-line. The filter selected for triviality, so the 46% was inflated, not deflated.

## Wrong 2 — "produces the committed line exactly" is the wrong question

fluidfix does not have to reproduce the maintainer's characters. It has to produce a line **the tests
accept**. Measuring against the committed text asks it to match a style, and undercounts by an unknown
amount. So the 2-of-134 figure — and the "under 2% on real history" conclusion drawn from it — does not
measure what it claimed to.

## The right experiment, and why it did not run

The 198 tested fixes carry their own judge, so the whole thing is runnable: check out the parent commit,
take **only the test files** from the fix, confirm the suite goes red, hand the source file to the guard,
and let that test decide. `run_real.py` does exactly this.

It is blocked by something duller than a result: **old revisions do not collect under a modern toolchain.**

```
ERROR tests/test_basic.py - pytest.PytestRemovedIn10Warning: Passing a non-Co...
Interrupted: 1 error during collection
```

Coverage therefore comes back empty, the packet has no executed lines, and the guard returns
NO-OBSERVATIONS having run **zero suite runs** — which is a harness failure wearing the costume of a
refusal. 22 of 23 click cases were exactly that, and an earlier run of the same file produced the same
shape for a different reason (I had not installed `pytest-cov` at all).

**Genuinely judged, in the end: 2 cases.** Both sortedcontainers, both real searches (85 and 8 suite runs),
both refused, and neither was a one-line fix. Two cases is not a measurement.

## So the honest state of shape coverage on real history

| figure | status |
|---|---|
| 58%, from our seeded mutations | **withdrawn** — the seeds were shapes chosen in advance |
| "under 2% on real history" | **withdrawn** — rested on exact-line matching, the wrong question |
| the real number | **unknown** |

Both the optimistic number and my own pessimistic one are gone. What remains is a method that works and an
environment problem that blocks it: replaying history needs an **era-appropriate toolchain**, a pytest
contemporary with each commit, which is a day of work and not a hard one.

Until that is done, **every claim resting on shape coverage is unsupported in both directions** — including
the ones I marked "weak" above.

---

## Claim 1 — a gate on every merge

> *The same six checks run against a pull request instead of a local tree.*

**Structurally wrong, and it takes one run to show it.** The six gates begin with RED-BEFORE. An ordinary
pull request is green before and green after. Handed a correct, behaviour-preserving refactor on a green
tree:

```
a correct refactor on a green tree -> NOT-RED
  why: the suite already accepts this code — there is nothing to certify
```

So the gate cannot judge a healthy pull request at all. What it actually gates is a **red build** — a much
narrower and much more honest product. A merge gate would need a different check entirely: not "did red
become green", but "does this patch change behaviour the tests do not pin", which is the UNIQUE gate used
on its own, against the base revision rather than against a rival patch. That is a different thing and it
has never been built.

---

## Claim 4 — proof the localisation makes the model cheaper

> *needs: proof the localisation makes the model cheaper — untested.*

**It could not be tested on our corpus, and the reason is a finding.** The A/B was set up: two identical
eight-module worlds, both models given the failing test output, one also given fluidfix's localisation.
Then look at what the test output already says:

```
pkg/percentile.py:8: NameError
FAILED tests/test_percentile.py::test_percentile_0 - NameError: name 'ceil' is...
```

**The traceback had already localised it.** When a failure raises, pytest names the file and the line for
free, and our localisation adds nothing. It can only be worth something when the failure is an *assertion*
whose traceback names the test rather than the cause — which is the case the real-repo study kept hitting
("a failure whose traceback named a docstring rather than the code", and an arrow fault four lines above
where the suite pointed).

Our toy world cannot produce that case either: one module per test, named identically, so `test_windows.py`
names `windows.py`. **The experiment needs a real repository where a failing test does not name the faulty
file** — and until it is run, the claim stays unproven and the cost split (0 tokens against ~96,000) remains
a statement about two halves costing different amounts, not about a saving.

---

## What has to change

- **Stop quoting 58% shape coverage.** Real history says under 2% today, with a 19% ceiling.
- **"Self-healing CI" is not supported.** At 19% ceiling and 22% recurrence, most red builds will need a
  model or a person, and the honest product is the localisation plus the certificate, not the repair.
- **"A gate on every merge" should be "a gate on a red build"** until a green-tree check exists.
- **The localisation's value is conditional** on the failure not already pointing at the fault. That
  condition should be measured — what fraction of real failures carry a traceback that names the right
  file — before any claim rests on it.

## Not claimed

- The commit filter is crude: a subject line matching fix/bug/regression and excluding merges, reverts,
  lint, docs and tests. Fixes that do not say so are missed, and some matched commits are not fixes.
- Single-file diffs of at most 40 lines. Larger fixes are excluded, which can only *lower* the mechanical
  share, not raise it.
- Four mature open-source libraries. A company's application code is a different distribution and the
  recurrence question in particular deserves that setting.
- 54 code fixes is a small sample for the recurrence claim, and the abstraction that produced the
  signatures is ours.

---

# THE TEST, RUN — 2026-09-19

The replay works now, and it gives the number that both withdrawn figures were standing in for.

## Four harness defects had to be fixed first, and every one of them looked like a result

| defect | what it looked like | what it was |
|---|---|---|
| `pytest-cov` never installed | `NO-OBSERVATIONS`, 0 suite runs | coverage empty, so the packet had no executed lines |
| the repo's own `filterwarnings = error` | `SKIP-NO-COLLECT` on 30 of 31 click cases, at every era | a pytest *deprecation warning* raised as a collection error. `-W default` collects 583 tests instead of none |
| tests already failing at the parent revision | baseline never green | interpreter drift, unrelated to the commit. Deselected, and the count recorded |
| dependencies change across a repo's own history | `SKIP-NO-COLLECT` on rich | rich needed `commonmark` before it moved to markdown-it-py; installing once at HEAD leaves old revisions unable to import their tests |

**A guard whose coverage came back empty returns a refusal after zero suite runs, and that is indistinguishable
from a real refusal unless you look at the suite-run count.** Three separate runs of this file produced exactly
that shape before the harness was right.

## The protocol

Every case must clear three preconditions before the guard is allowed to run, so nothing broken is ever counted
as a refusal:

- **COLLECTS** — the suite at the parent revision collects without error
- **GREEN** — with the fix's test files removed, the suite passes
- **RED** — with the maintainer's own regression test added, it fails

Then the source file is handed over with the shipped and taught vocabulary, and **that test decides**. Nothing
is compared to what the maintainer typed.

## Result: click, 31 fixes from 2022 onward that ship their own test

| | |
|---|---|
| attempted | 31 |
| **genuinely judged** | **26** |
| **repaired, accepted by the maintainer's own test** | **0** |
| skipped — the test passes at the parent anyway | 4 |
| skipped — suite error | 1 |

These were real searches, not empty ones: **1,116 suite runs across the 26**, between 1 and 100 each, ranking
between 1 and 185 candidate lines per case. Every one ended in the same ruling — `HARVEST_COUNTEREXAMPLE`,
the law's REFUTED exit: every candidate built was rejected by the suite.

Adding sortedcontainers' two genuinely-judged cases: **0 repaired out of 28.**

## Why, and it is not the vocabulary's coverage

**Only 2 of the 26 judged fixes were one-line diffs at all.** The rest change several lines, which a
line-rewriting vocabulary cannot express however much is taught. The seeded mutations that produced
"7 of 22 exact" were single-line *by construction* — that was the whole of the difference.

So the honest statement, at last with a number behind it:

> On real, tested bug fixes from a real repository, the vocabulary repaired **0 of 28**. The ceiling is not
> set by which shapes are taught; it is set by real bug fixes not being single-line edits.

## What this does not say

- 26 cases from one repository, plus 2 from another. rich's 49 are still running at roughly twelve minutes
  each and will be added; they are not in this number.
- 2022 onward only. Older revisions need an era-appropriate toolchain that this harness does not build.
- Commits whose subject says they fix something, touching one source file and its tests. Fixes that say
  nothing, or that touch two files, are absent.
- It says nothing about the **localisation**, which is the half that costs nothing and was not on trial here.
  Every one of the 26 refusals named the file, ranked the lines the failing test executed, and printed the
  test that killed each candidate.

---

# rich finished — two "repairs", and both are wrong

rich's 49 completed: **29 genuinely judged, 2 REPAIRED**. The first non-zero on real history. Both were
one-line fixes, both real searches (37 and 51 suite runs, ruling SHIP), and both maintainer fixes land
squarely inside the vocabulary:

```
rich/segment.py    len(text)         ->  (len(text) - 1)     taught class 7, learned on CLICK
rich/traceback.py  frame_index == 1  ->  frame_index == 0    shipped class 1, literal-off-by-one
```

So it looked like the result the whole exercise was after — including a class taught on one repository
repairing a real bug in another. **It is not.** Re-running both and printing what was actually shipped:

### segment.py — the right line, the wrong program

```
maintainer:   pos = int((cut / cell_length) * (len(text) - 1))
fluidfix:     pos = int((cut / cell_length) *  len(text) - 1)
```

The `- 1` went outside the multiplication instead of inside it. Over 1,452 combinations of `len(text)` and
`cut / cell_length`, the two disagree on **736** — at `len=2, cut/cell=3`, the maintainer returns 3 and
fluidfix returns 5. Different programs.

### traceback.py — not the fault at all

```
maintainer:   first = frame_index == 1      ->  == 0        (line 452 area)
fluidfix:     padding=(0, 1),               ->  (0, 0),     (line 452)
```

It changed a padding tuple somewhere else entirely, and the suite went green. A compensating edit, not a
repair.

### Why both slipped through, and it is my doing

Each of these revisions had **22 and 24 tests already failing** under a modern interpreter, and the harness
deselects those so the suite can go green at all. That thins the judge — and the tool did exactly what it is
documented to do: *the judge is absolute, and it will serve a suite that lies.* I weakened the suite to make
the experiment runnable, and the weakened suite accepted two patches that a whole one would very likely have
rejected.

## The result, corrected

| repository | judged | shipped a repair | correct on inspection |
|---|---|---|---|
| click | 26 | 0 | — |
| python-sortedcontainers | 2 | 0 | — |
| rich | 29 | 2 | **0** |
| **total** | **57** | **2** | **0** |

**0 correct repairs out of 57 real, tested bug fixes — with 2 false accepts, both traceable to tests I
deselected.**

Two things follow, and they point in opposite directions:

- **The ceiling is structural.** Only 11 of the 57 judged fixes were one-line diffs at all. A line-rewriting
  vocabulary cannot express the other 46 however much is taught.
- **The false accepts are the more useful finding.** They are the first time the documented weakness has
  been caught on real code rather than a constructed case, and they were caused by degrading the suite by
  about 4%. That is a sharper warning than any of our synthetic overfitting demonstrations: *this tool is
  exactly as good as the suite it is given, and thinning the suite is enough to make it wrong.*

## What still stands

The **localisation**, which was never on trial here. All 55 refusals and both false accepts named the file,
ranked the lines the failing test executed, and printed the test that killed each candidate — at zero
tokens. Nothing measured today touches that half.

## Not claimed

- 57 cases, three repositories, 2022 onward, commits whose subject says they fix something and that touch
  one source file plus its tests.
- The deselection is a harness compromise, not a product setting. A real deployment runs the whole suite,
  where these two patches would have had 22 and 24 more tests to satisfy — but *whether they would have
  been rejected is not measured*, only likely.
- "Correct on inspection" is my reading of two diffs, though the segment.py divergence is arithmetic and
  shown above rather than asserted.

---

# CORRECTION — I tested one guard, not fluidnet

Fair objection, and it changes what the 57 cases are evidence *about*. `replay.py`'s guard is:

```python
o = Oracle(...); pk = build_packet(o, rel, ...); res = repair(o, rel, obs)
```

That is **one fluidfix guard, on a file I handed it**. No survey, no growth by ruling, no memory carried
between the 57 cases, no descent — and no certificate: `repair()` accepts on a single green, where
fluidnet's CERTIFY re-checks, checks collateral, and checks uniqueness. So the two false accepts might have
been an artefact of testing the wrong thing.

**They are not.** Running the six gates against both, on the real revisions:

| gate | segment.py | traceback.py |
|---|---|---|
| RED BEFORE | yes | yes |
| GREEN AFTER | yes | yes |
| STABLE (3 re-runs) | yes | yes |
| NO-COLLATERAL | yes | yes |
| UNIQUE | *a rival passes* | no rival found |
| ROLLBACK | byte-exact | byte-exact |

The UNIQUE hit looked like the gate working — until I checked where that rival came from. **I supplied it
myself**, by hand, as the maintainer's own fix. The real gate only compares candidates the search produced,
and at that line the vocabulary produces exactly one:

```
line:                pos = int((cut / cell_length) * len(text))
class 7 proposes:    pos = int((cut / cell_length) * len(text) - 1)     ← the wrong one
maintainer's fix:    pos = int((cut / cell_length) * (len(text) - 1))   ← NOT among the candidates
```

One green, so no ambiguity, so it ships. **Both false accepts survive full certification.** Adding the
gates does not change the result.

## A product defect found on the way: taught class 7 has a precedence bug

`len-as-last-index` was taught from one worked example — `last_index = len(words)` in click's `utils.py` —
and its applier appends ` - 1` after the closing paren. That is correct when `len(...)` *is* the
right-hand side, and wrong whenever it is an operand:

```
last_index = len(words)                       ->  last_index = len(words) - 1          correct
pos = int((cut / cell_length) * len(text))    ->  ... * len(text) - 1                  WRONG
n = total / len(items)                        ->  total / len(items) - 1               WRONG
return offset + len(buf)                      ->  offset + len(buf) - 1                WRONG
```

**A class taught from one example generalised its signal but not its semantics.** The signal correctly finds
every `len(...)` that could be a last-index mistake; the applier only produces the right line for the shape
of its own example. This is the first time teaching-by-example has been shown to produce a class that is
confidently wrong rather than merely narrow, and it is the direct cause of one of the two false accepts.

The fix is one line — wrap the call rather than trail the expression — but
`examples/taught-2026-09-16/rules_session.py` is checksummed and referenced in the sales material as a
frozen teaching set, so it is **recorded here and not silently edited**.

## What the 57 cases do and do not measure, corrected

**They measure:** whether the taught vocabulary can produce a line that the maintainer's own regression test
accepts, on a file it is told to look at. Answer: 0 correct in 57, 2 shipped wrong, and the gates do not
catch either.

**They do not measure fluidnet.** Survey, growth by ruling, memory carried between incidents, and descent
into the memory were all absent. Those determine **cost and reach** — how many nodes it takes to find the
file, and whether the second incident is cheaper — not whether a shipped repair is right. On this evidence
the net's growth machinery would change the price of the 57 searches and none of their outcomes.
