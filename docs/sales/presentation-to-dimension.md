# Call prep — Dimension

Prepared 18 September 2026. Everything below is measured; each claim carries the run it came from, in
`research/…` in this repository. Numbers with no run behind them are marked as not measured.

---

## Where we are

They found fluidfix on PyPI, read the deck, and asked one question before the call: **what is the smallest
repo and shape where the offline-plus-API demo is clearest?** A second question was cut off in the paste.

Already sent: `pip install fluidfix`, the deck, and `examples/fluidfix_demo.py` — one file, one command,
clones Click at a pinned commit, builds a virtualenv, installs fluidfix from PyPI, then breaks one line of
`src/click/shell_completion.py` three times and lets Click's own suite judge. Verified end to end twice.

| the demo, on the released 0.15.0 | outcome | time | suite runs |
|---|---|---|---|
| a fault it knows (`[0]` → `[1]`) | exact original bytes back | 55 s | 16 |
| a fault it does not know (`if not value:` → `if value:`) | refuses, prints why, 99 candidates logged with the test that killed each | 54 s | – |
| the same fault with one rule taught | exact | 132 s | 26 |

Setup is about two minutes. No API key. Nothing installed outside the demo folder.

---

## What it is, in one sentence

**Teach it a fault shape once and it debugs that shape for free, forever, with a certificate — and refuses
everything else.**

It is not an assistant and it does not save you tokens on a model you are already calling. On the shapes it
has been taught, **the model is not called at all**. That is a narrower claim than "AI debugging" and it is
the one that survives every measurement below.

| | measured |
|---|---|
| on a taught shape, unseen instance | **100%** — 240 distinct bugs, four classes, none ever shown to it |
| a table of past fixes on the same stream | 28%, and it needed 146 rows to get there |
| cost per repair | **0 tokens.** A certificate is 4 suite runs, a refusal 3 |
| on a real repository, never told which file | found it and restored the **original bytes** |
| the same fault a second time | **1 node, 4 suite runs, 41 seconds** |
| outside the taught shapes | it refuses, and says what it eliminated |

**The number we cannot get without your repository** is the only one that decides the value: what fraction
of your incidents fall inside shapes worth teaching. A week of your CI in report-only mode produces it.

### Three things we do not claim

**It does not save tokens.** Tested directly. When a failure raises, the traceback already prints
`file.py:line`, so the localisation adds nothing; when a failure is an assertion and the cause is hidden,
the localisation ranked the guilty file **7th of 14**. The claim fails in both directions and is withdrawn
(`research/localisation-2026-09-19`).

**It does not repair real bug fixes generally.** Replayed against 57 real fixes from click, rich and
sortedcontainers — each judged by the maintainer's own regression test — it produced **1 correct repair**.
Only 11 of those 57 were one-line diffs at all; a vocabulary that rewrites one line cannot express the rest,
however much is taught.

**A certificate is exactly as strong as your suite.** A patch your tests cannot distinguish is certified
when offered alone. Offered beside a rival, the ambiguity check separated it 14 of 14 times.

---

## The main point: it searches nodes, and every node teaches it something

This is the thing to lead with. Everything else on the call is detail.

A fault arrives. The net opens **one** small guard over one file and one fault class — not a plan, one node.
What that node comes back with decides where the net grows next, and the growth is the search:

- **REFUTED** — every candidate here was rejected, so the fault is not in this file under this class. Grow
  **wider**: the next class here, this class in the next territory.
- **CAPPED** — something passed but the view was cut short. Grow **deeper**: split the line range and give
  each half its own guard.
- **MISDIRECTED** — its own memory sent the search the wrong way. Grow **down**: the memory becomes the
  territory and a guard repairs it.

The first green stops everything — and then has to earn it: green on the full suite, still green on
re-check, nothing else broken, byte-exact rollback otherwise.

**And it keeps what it learns.** Measured on the same world, 23 (file, class) pairs:

| | nodes walked | wall | tokens |
|---|---|---|---|
| first time it sees this shape | 22 of 23 | 19.3 s | 0 |
| once it remembers the shape | **5 of 23** | **5.2 s** | 0 |

It remembers the **shape**, not the place, which is why the knowledge travels: a class learned on `rich`
took the search on `arrow` — a different repository — to **one node and two suite runs**.

**When the knowledge itself is wrong, it repairs the knowledge.** Its memory is not a table, it is a file of
dispatch rules with its own test suite. When it kept dropping a class it had already learned, the net went
down, turned that incident into a test — which is what turns the memory red — and a guard repaired the
memory under the memory's own suite. **17 misdirections became 1**, and the fault never recurred.

**It also learns what kind of bug it is facing, by searching.** It tries the free repair first and widens
the budget only when the tests reject everything, so the first budget that passes *is* the fault's kind.
Run over fourteen bugs small local models actually wrote: 11 of 14 have a one-line fix. Two of those shapes
recurred across different models, were taught from the ladder's own output, and the free tier went from
**1 of 14 to 5 of 14** at zero tokens.

**And the judge does not care who wrote the patch.** Handed fixes written by a different model — whole-file
rewrites with inserted imports, nothing the vocabulary could author — it certified **14 of 14**, and refused
**29 of 29** deliberately bad ones (wrong, intermittent, breaks-something-else) with byte-exact rollback
every time.

Interactive walkthrough of all of the above, with the real terminal output:
`https://claude.ai/artifact/DhZMRkSW372Nv4z9ikFp7m` (private — share it before the call if they should see it).

**Runs:** `research/fluidnet-2026-09-18/` · `research/lake-2026-09-18/` · `research/closed-loop-2026-09-18/`
· `research/kindof-2026-09-18/` · `research/certify-2026-09-18/`

**What this does not say.** It writes a minority of the fixes — 5 of 14 there, 7 of 22 on real repositories.
The net finds and judges; a model or a person still writes most fixes. And where a fixed plan happens to
contain the answer, the net is four times slower; where it does not, the net is the only one that found the
fault at all.

---

## The one-liners

Use these as answers, not as slogans. Each is followed by what backs it.

**"It searches, and every node it opens teaches it something."** — 22 nodes the first time it sees a shape,
5 the second (`research/fluidnet-2026-09-18`).

**"It remembers the shape, not the place, so the knowledge moves between repositories."** — a class learned
on rich took arrow to one node and two suite runs (`research/lake-2026-09-18` §4c).

**"When its own memory is wrong, it repairs the memory."** — the incident becomes a test, the memory goes
red, a guard fixes it. 17 misdirections became 1 (`research/closed-loop-2026-09-18`).

**"It works out what kind of bug it is by searching for the cheapest fix that passes."** — 11 of 14 real
model-written bugs have a one-line fix; teaching two recurring shapes took the free tier from 1 to 5 of 14
(`research/kindof-2026-09-18`).

**What it does.** It never writes a guess: it takes the broken line, applies one taught transform to make a
candidate, runs your tests, and keeps the candidate only if they pass, restoring the original bytes exactly
when they do not.

**Is it any good?** On real repositories it restored the exact line in 7 of 22 in-vocabulary breaks, never
shipped a wrong repair on the 16 out-of-vocabulary ones, and the run itself exposed three product bugs that
were hiding real repairs — all now fixed.

**Is it a lookup table?** Yes for the memory of *where* a fault was, no for the vocabulary: a table of 240
programs repaired 0% of bugs it had not been handed, while six shapes repaired 100% of the same 240 and
stayed six.

**Can it fix something it has never seen?** Yes for a line, no for a class. A shape is a signal plus a
transform, so it repairs names, values and contexts that were in no example; a fault whose shape nobody
wrote is refused, never guessed.

**Do you train it?** No. You teach a vocabulary once by hand, the tool scans your repository itself on every
failure, and the memory learns only which part of the vocabulary keeps paying off.

**Is it cheaper than just asking a model?** Wrong question, and we got it wrong ourselves for a while. It
does not make a model call cheaper — measured, and withdrawn. On a taught shape it means **there is no model
call**: 240 distinct unseen bugs, 100%, zero tokens. Outside those shapes it refuses and you are back to a
model at full price.

**Why many small ones?** The tool is 5,580 lines with zero runtime dependencies, so an extra guard costs no
tool — only suite runs. It does cost cores, though: measured on twelve, four guards run at full speed,
twelve at 2.0x each, thirty-two at about 5x, and all thirty-two still repaired byte-exactly. Crowding slows
them; it never makes them wrong.

**But what does the growth actually save?** This is the real answer, and it is not smallness. A fixed plan
spends its 45 guards whether it needs them or not. The net opens only what its refusals force it to open —
129 nodes when it knows nothing, 13 once it knows the shape, 5 once it has seen this exact one — and the
first green stops everything. You pay for the nodes the search opened, and for nothing it did not need.
That cuts both ways, and the cold number is the honest half: 129 is worse than 45.

**What does the second occurrence cost?** Remembering the shape instead of the incident means a fault never
seen before, in another repository, costs one fluidfix and two suite runs instead of forty-five and three
hundred.

**Is the design flawless?** No. It is sound in the direction that matters — it never shipped a wrong memory
under attack — and it is bounded above by its tests in both directions: it cannot see a fault its suite does
not pin, and it will serve a suite that lies.

---

## The proofs

**Finding the file in a large tree.** 302 source files, 300 tests: the true file ranked first 10 times out of
10, localised in about 5 s, exact line back in about 16 s. `research/llm-fusion-2026-09-16`.

**Four real repositories, zero tokens.** click, arrow, sortedcontainers, rich. Mutation sites chosen by a
fixed seed over library files only, liveness checked twice, the repository's own suite as the only judge,
300 s budget.

| | live breaks | byte-exact | wrong | refused |
|---|---|---|---|---|
| in the taught vocabulary | 22 | 7 | 1 | 14 |
| outside it | 16 | 0 | 0 | 16 |

**Teach once, judged elsewhere.** Five classes, each written by hand from a single worked example, frozen
with checksums before any hold-out ran (`examples/taught-2026-09-16/`): the teaching examples repaired 5 of
5, and on *other repositories* 6 of 11 held-out cases came back byte-exact with 0 wrong.

**A table against a shape.** 240 distinct generated bugs, six shapes, each with a test that catches it;
after every bug the arms are scored on the next 24 they have never seen.

| arm | rows stored | repairs unseen |
|---|---|---|
| table of whole programs | 240 | 0% |
| table of broken lines | 133 | about half |
| six shapes | 6, constant | 100% of bugs whose shape was taught |

**Small enough to run many.** 5,580 lines, 18 modules, 258 KB, zero runtime dependencies. On one 12-core
laptop: 1 to 4 guards cost nothing extra, 12 cost 2.0x each, 32 cost 5.1x each, and every guard repaired
byte-exactly at every width. Crowding slows them; it does not make them wrong.

**Many small ones beat one big one.** The same fault in rich `table.py`, which a single guard never solved
because its ranking never opened the file:

| | fluidfixes | wall | winner's suite runs |
|---|---|---|---|
| one guard, 900 s budget | 1 | 904 s | refused |
| one per file | 16 | 312 s | 117 |
| one per file **and** fault class | 13 | 36 s | 8 |

**Memory turns the second incident cheap.** Cold: 45 fluidfixes, 222 suite runs, 113 s. The same failure
again: 1 fluidfix, 8 suite runs, 27 s. A different repository with only the *class* remembered: 1 fluidfix,
2 suite runs, 32 s.

**Live pages** (same numbers, animated): the lake, the router law, fluidfix and the life, the growing net —
all under `https://devkancheti4-design.github.io/fluidfix/`.

---

## Say these before they ask

**One wrong repair in 22.** On arrow, the guard changed a comparison four lines above the real fault and the
project's own suite accepted it. Reproduced on the PyPI release and on the fixed tree, so it is the suite's
blind spot rather than a code defect. A suite that does not pin a behaviour cannot defend it, and no repair
tool can invent the missing test.

**The judge is absolute.** Corrupt the test suite and the tool will obediently rewrite correct code to
satisfy it — measured, two suite runs. The rule that makes it safe is the same rule that makes it credulous
about its tests.

**Refusals are common and deliberate.** 14 of 22. They split into honest kinds: a passing candidate held
because the file was too large to prove uniqueness inside the budget, a fault the ranking never reached, and
a failure whose traceback named a docstring rather than the code. Every refusal prints what was tried and
which test rejected it.

**No frontier-model numbers.** Three local 4B models scored 0 of 4 as rule authors at 4,000 to 14,000 tokens
per case. A strong author scored 3 of 4 on the same packets, labelled as an upper bound. Haiku wrote four
answers that were never judged. There is no API key in this work, so there are no GPT or Claude-API figures
and I will not invent any.

**The release is behind the tree.** PyPI has 0.15.0 from 7 September. Seven fixes found by these runs are
committed locally and unpushed, so a prospect installing today gets the version that refuses rich for a
virtualenv bug.

---

## If the call goes well

1. They run `examples/fluidfix_demo.py` on their own machine: three acts, six minutes, no key.
2. Pick one recurring shape from their own incident history and teach it by hand, together, in one sitting.
3. Point the guard at their CI on one repository, in report-only mode, and read a week of refusals — the
   refusals are the product's honest half and the best evidence either way.

---

That is the trade you get for growth driven by refusals instead of a plan fixed in advance.
