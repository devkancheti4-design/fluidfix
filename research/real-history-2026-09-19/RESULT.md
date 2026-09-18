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
