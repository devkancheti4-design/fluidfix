# fluidnet

**You teach it a bug once, and it repairs every future one — with a proof, not a guess.**

Longer, and this is the version that survives the first hostile question: fluidnet repairs the faults you
taught it, proves each fix correct over every input in range, certifies fixes it didn't write, and never
attempts open-ended bugs, by design.

What it is *not*: a token saver, and not a general repair tool. It is a narrow, cheap replacement for a
model on the part of the work that repeats — and on that part it is load-bearing and has no limit.

---

## How a software engineer uses it

**Every time you fix the same shape of bug twice, teach it once. From then on it owns that shape and hands
you a proof with every fix.**

Teaching is two artefacts written beside your code, versioned with it, once per shape:

| | what it is | what it buys |
|---|---|---|
| **the fault class** | the signal (what the fault looks like) and the applier (the rewrite) | every future instance of that shape is repaired for free |
| **the class property** | one sentence of English plus a checker: what must stay true of *every* rewrite | every future rewrite of that class is proved or refused, for free |

Neither is per-bug. Both are per-*shape*, written once, and they hold on code nobody has written yet.

The working loop:

1. You hit a mechanical fault you have hit before. You fix it yourself.
2. You add the class and its property — a few lines in a dictionary file in your repo.
3. Every later instance is found, repaired, proved and certified without you.
4. You keep the open-ended work. It never attempts it.

Teach a property with a control that *fails* it. A property nothing can fail proves nothing — that is not
advice, it is enforced: a check that evaluates zero inputs reports UNPROVEN, never PROVEN.

---

## Architecture

```
                 YOU TEACH, ONCE PER SHAPE
        ┌──────────────────┐   ┌──────────────────────┐
        │   fault class    │   │   class property     │
        │ signal + rewrite │   │ what every rewrite   │
        │                  │   │ keeps true           │
        └────────┬─────────┘   └──────────┬───────────┘
                 └───────────┬────────────┘
                             v
                    ┌─────────────────┐
                    │    overseer     │   routes a failing test
                    │ routes by kind  │   to the guard that holds
                    └───┬────┬────┬───┘   the matching class
              ┌─────────┘    │    └─────────┐
              v              v              v
         ┌─────────┐   ┌─────────┐    ┌─────────┐
         │  net 1  │   │  net 2  │    │  net 3  │   7 taught classes each
         └────┬────┘   └─────────┘    └─────────┘
              │
              v   INSIDE ONE NET
   ┌──────────────────────────────────────────────────────────────┐
   │  localise  ──>  six fused laws  ──>  applier                  │
   │  ranks the      rule the             proposes                 │
   │  lines the      situation            candidates               │
   │  test ran                                │                    │
   │      ┌───────────────────────────────────┘                    │
   │      v                                                        │
   │  property gate ──> your suite ──> certificate                 │
   │  refuses for       the ONLY       six gates,                  │
   │  free              acceptor       byte-exact rollback         │
   │       ^                 │                                     │
   │       └─────────────────┘                                     │
   │   still red, but FEWER tests failing: keep the fix, go again   │
   └──────────────────────────────────────────────────────────────┘
```

**Why a swarm and not one big guard.** A dictionary is 16 slots, of which 7 are usable for your own
classes — a hard ceiling. But it is a ceiling *per process*: each net loads its own dictionary, so N nets
carry 7N taught classes and the overseer only has to route. That is the whole reason the product is many
small cheap nets under one overseer rather than one large one.

**Why the last row is in that order.** The property gate runs *before* the suite because it refuses for
free — measured 2026-09-19, six wrong candidates killed at zero suite runs, including the one that shipped
into `rich` and that rich's own tests accepted. The suite is the only thing that can *accept*; the property
is the only thing that can *prove*. Rejection restores the file byte-exactly.

**Certification mode** is the same bottom row pointed at a patch the net didn't write — a model's, a
colleague's. 14/14 accepted, 29/29 adversarial refused.

---

## More than one bug at a time

Suppose your code has two bugs and the net knows how to fix both kinds.

**What used to happen.** It applies its first fix. That fix is *correct* — but the second bug is still
there, so the tests are still red. Its only question was "are the tests green now?", the answer was no, so
it threw the correct fix away and undid it. Same for the second. It refused, holding both right answers
the whole time. The problem was never the knowledge; it was that **red** and **less red** looked identical
to it.

**What happens now.** It counts how many tests are failing. A real run, three bugs, three different taught
classes:

```
start                                      5 tests failing
off-by-one        len(words) -> len(words) - 1     4 failing   better, keep it
wrong operator    and -> or                        2 failing   better, keep it
flipped guard     if x: -> if not x:               0 failing   green, done
```

A step is kept only if the count goes **down** and nothing that was passing starts failing. It walks
downhill until green.

**What did not change.** Only the final state is accepted, and only on the whole suite going green. If it
walks downhill and gets stuck short of green, every edit is rolled back byte-for-byte and the answer is
still refusal. Intermediate steps are working guesses, never certified.

**Two bugs on the same line** need one more thing. Neither fix alone changes which tests fail — the two
faults mask each other, so there is no gradient to follow — so a candidate is fed back through the
vocabulary and the pair is tested together:

```
return words[len(words)] and fallback          both tests failing
  fix the index only                           both still failing   no signal
  fix the operator only                        both still failing   no signal
  compose:  words[len(words) - 1] or fallback  green
```

Measured 2026-09-20: two faults across two lines, 6 suite runs; three faults across three lines, 11 runs;
two faults on one line, 4 runs. All refused outright before this.

**The safety cost, and who pays it.** Smaller steps are a new way to be wrong, so it was tested against a
deliberately weak suite — one that cannot tell the right fix from the wrong one, exactly like the suite
that accepted the `rich` incident. Without the property gate it confidently shipped the wrong fix. With
the gate it refused, blocking 8 candidates before a single suite run. **The properties are what make
descent safe, not the descent itself.**

**And they fail open.** Properties live in a separate file from the classes. Load the classes without them
and the gate silently does nothing — every check returns UNPROVEN, every candidate passes, and it reports
zero refusals, which reads as a clean bill of health. Call `props.classes_without_properties(kinds)` after
loading and act on what it returns, or use `gate(..., strict=True)` to refuse unproved rewrites outright.

---

## The placement law, and its 2026-09-19 correction

Several taught classes insert a token into an existing expression (`- 1`, `+ 1`, a negation, a clamp).
Where the token goes is not the applier's decision — the body measures the syntactic context into a
situation word and the **law** decides TRAIL or WRAP.

```
x = (L << 3) | R          L, R = precedence class of the adjacent operator, each 0..6
place(x) -> 0 TRAIL       append the token after the call
            1 WRAP        bracket the call with the token inside
```

### What was wrong

The law was verified exhaustively against its 49-case truth table and **the table was wrong**. It held `+`
and `-` in the same precedence class 4, but a minus to the *left* negates the call, so it enters the
enclosing expression with coefficient −1 and appending ` - 1` subtracts where subtracting one from `len(x)`
would add:

```
k - len(x) - 1     is  k - L - 1        -len(x) - 1     is  -L - 1
k - (len(x) - 1)   is  k - L + 1        -(len(x) - 1)   is  -L + 1
```

Off by two, on every input. Nothing that checks law-against-table can see this — the table itself was the
defect. What found it was a class property: an algebraic statement about the rewrite, checked exhaustively
with no suite and no repository.

### The fix, and why it is in the body

**The law is byte-for-byte unchanged.** `_left_class` in `src/fluidfix/place.py` now measures a left-hand
`-` as class 5, which forces WRAP. This repository's discipline is that the law decides and the body only
measures; the body had mis-measured.

After the fix: the law still scores 0 violations on all 49 reachable situation words, `fluidfix selfcheck`
still re-derives all six laws, the 225 tests still pass, and four positions nothing had tried before now
hold — `k - len(x)`, `-len(x)`, `(k - len(x)) * 2`, `abs(k - len(x))`.

**Corollary worth keeping:** verifying a law against its spec does not verify the spec.

---

## How it generalises

Three axes, and they are the only ways an instance can differ from the one example you taught:

| axis | does it generalise? | evidence |
|---|---|---|
| names and values | **fully, immediately** | 240/240, and 30/30 per class — each class took its entire share of the stream the moment it loaded |
| the repository | **fully** | the four classes taught from `click` ran unchanged against `rich` and `sortedcontainers` |
| syntactic position | **this was the blind axis** | as taught, 6 of 16 positions land the token wrong; with the placement law, 0 of 17 |

What filled the third axis was not more teaching — it was one law, plus the measurement fix above. Nine of
the ten positions that now hold were never taught to anything.

---

## What is measured

| | |
|---|---|
| generalisation within a taught shape | 240/240; 24/24 on unseen span instances |
| certification of fixes it didn't write | 14/14 accepted, 29/29 adversarial refused, 307 suite runs |
| class properties | 5/5 controls refuted; 6 wrong candidates killed at zero suite runs |
| real fix sizes (what the ceiling actually is) | 37% one-line, 70% ≤5 lines, 91% ≤20 lines |
| rollback | byte-exact, sha256-checked, every rejection |

## What it deliberately does not do

Open-ended bugs. There is no path through the architecture for them, and that is the design, not a gap.
On novel work it can still do the thing it is best at: **certify that somebody else's fix is correct.**

---

Detail: `research/property-gate-2026-09-19/RESULT-classes.md` (properties and the law hole),
`research/certify-2026-09-18/RESULT.md` (certification), `research/real-history-2026-09-19/RESULT.md`
(the real-repository study, including its retractions).
