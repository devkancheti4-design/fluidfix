# The loop closed — measured 2026-09-18

The model, in the user's words: *in the lake you put a Life, and in the Life you put another lake with one
fluidfix as its head.* Every fluidfix heads a lake; every lake's memory is itself a lake headed by one
fluidfix. The structure descends **through** the memory, not only above it, until it reaches a fixed point.

Earlier work built one turn of that loop: many guards with a memory above them (`research/lake-2026-09-18`).
The memory there is a table, so the loop stops after a single revolution. This closes it.

## How the memory becomes a lake

A memory that is a table can only be read and written. A memory that is **code** can be broken, tested and
repaired — which is what lets the same organ continue downward.

| | what it is | its judge |
|---|---|---|
| level 0 | N small fluidfixes over a repository's territories, one head | the repository's own suite |
| level 1 | the head's Life: `memory/dispatch.py`, the gate and the wave plan, as code | `memory/test_dispatch.py` — every incident the lake has already answered, replayed |
| level 2 | the lake **inside** that Life: one fluidfix per class over `dispatch.py` | the same replay suite |
| level 3 | that head's own memory: which class repairs a memory | one row; its lake is one fluidfix |

At level 3 the head, the lake and the memory are the same object, so the loop closes and descends no
further. Nothing outside the system repairs the memory: a fluidfix repairs it exactly as it repairs code,
byte-exact, with the memory's own tests as the only judge.

## Measured

`closed_loop.py` breaks the memory, checks the memory's own suite goes red, and lets the loop run.

| the memory is broken at | head's memory before | dispatched | suite runs | wall | result |
|---|---|---|---|---|---|
| the gate: `conf >= THRESH` → `>` | empty | 9 | 8 | 2.8 s | **repaired byte-exact** by class 0, learns `kind:0` |
| the same break again | `kind:0` | **1** | **2** | **2.3 s** | repaired byte-exact |
| the cap: `WAVE1_CLASSES = 2` → `1` | `kind:0` | 1, then 12 | 6 | 4.2 s | repaired byte-exact by a **taught** class 4 |

Zero tokens throughout. The second row is the loop paying off one level down: the memory's own lake
remembers which class repairs a memory, so the second memory fault costs one fluidfix instead of nine.

## Three things the run exposed

**The gate is the natural place for a memory to break.** `conf >= THRESH` becoming `conf >` means the memory
stops answering at exactly its own threshold — a boundary slip in the very comparison the judge is built on,
and the shipped strictness class repairs it in two suite runs.

**The shipped vocabulary is directional.** The cap fault needs `1` to become `2`, and the shipped literal
class only *decrements* ("a literal exactly one greater than correct"). Every shipped class refused, which
is the honest outcome, and the fix is the same ladder as everywhere else: teach the other direction once
(`memory_rules.py`, one worked example), after which the memory repairs itself and the head remembers
`kind:4`.

**A suite that does not pin a property cannot defend it.** The cap break passed the memory's own tests at
first: nothing asserted that wave 1 carries *every* remembered class. The driver refused to proceed —
it asserts the break turns the suite red — which is how the gap surfaced. A test was added, and only then
could the fault be found and repaired. My first taught signal was also wrong (`[A-Z_]+` excludes the digit
in `WAVE1_CLASSES`), and it showed up as a refusal, never as a wrong repair.

## Attacked — 2026-09-18, live, one at a time (`attack.py`, `attack_results.json`)

A design is only flawless until someone measures it. Four attacks; two found real holes.

| attack | what it does | result |
|---|---|---|
| **mutation sweep** | break the memory at every line a shipped class can touch | 1 repaired byte-exact, **0 wrong-green**, 1 fault its own suite cannot see |
| **broken judge** | corrupt the *suite*, leave the memory correct | **it rewrote a correct memory** to satisfy the lie, in 2 suite runs |
| **poison** | teach the head a class that repairs nothing, then break the memory | wasted 0 suite runs, widened, repaired byte-exact, recall self-healed |
| **determinism** | the same break three times | identical winner, bytes and memory hash (`67211b08`) each time |

### The two holes

**A corrupted judge corrupts the memory.** With `test_dispatch.py` altered to assert the opposite of its
gate test, the loop obediently rewrote the correct memory — `return conf >= THRESH` became `conf > THRESH`
— and called it a repair, because the suite went green. This is not a bug in the laws; it is the price of
the rule that makes them safe. The suite is the only authority, so the system is exactly as correct as its
tests, and nothing in the loop can tell a broken judge from a broken memory. A repair that *reverts* a line
the tests previously passed is the signature to look for, and the loop does not look for it.

**A memory's suite under-constrains its memory.** `WAVE1_CLASSES = 2 → 3` leaves every test green: the
memory silently carries more classes in wave 1 than it should, and no level of the loop can see it. This is
the same shape as the earlier finding that the cap `2 → 1` passed until a test pinned it. A memory can only
defend the properties someone thought to write down.

### What held

No wrong-green repair appeared in the sweep: every break was either repaired to the original bytes or left
alone. Poisoning is cheap and self-correcting, because the recency-dominant memory replaces the wrong class
as soon as a real repair lands, and a class that matches no line in the territory refuses for free. The
whole loop is deterministic down to the memory's hash.

### So: is it flawless?

No. It is *sound in the direction that matters* — in these runs it never shipped a wrong memory — and it is
**bounded above by its tests in both directions**: it cannot see a fault its suite does not pin, and it will
happily serve a suite that lies. Every level of the recursion inherits that ceiling, because every level
judges the same way. Making the loop stronger does not mean adding levels; it means writing the tests that
pin the properties each memory is supposed to have.

## What is not claimed

- Level 0 is cited from the recorded runs in `research/lake-2026-09-18`, not re-run here; levels 1 to 3 are
  live in every row above.
- Two memory faults, both inside or one teaching step away from the vocabulary. A memory fault that is not
  a shape — a wrong dispatch *policy* rather than a wrong token — is outside this and would reach a human.
- The fixed point is structural, not a proof of termination under adversarial memory faults.

## The third direction: the loop grows as a net (`grown_loop.py`, 2026-09-18)

`net.py` grows a search and its law returns two directions, **both of which search code** — REFUTED to wider,
CAPPED to deeper. This file's own driver descends into the memory only because a human passes
`--break gate`. So the net and the loop grew apart: nothing in the law ever says *go down*.

There is a ruling that says it, and it needs no hand:

> **MISDIRECTED** — the memory *remembered* the answering class and wave 1 still did not carry it.
> Wider and deeper both search a repository that was never the problem. Go **down**: the memory file is the
> territory and its suite is the judge.

It is decidable against the memory's **own record**, never against ground truth about the code. And it
arrives on its own: `WAVE1_CLASSES = 2` is correct for two remembered classes and becomes wrong the moment a
third is learned and an older one answers. **Nothing here is broken by hand.** The memory is outgrown, which
is what growth means.

One property makes the descent work at all, and it is the shape of the whole loop: **when MISDIRECTED fires
the memory's suite is still GREEN.** It passes every incident it has seen. So the descent must first write
the incident into the suite — that is what turns the memory red — and only then can a fluidfix repair it,
judged by a test encoding the very failure that triggered the descent.

Replayed over the 31 recorded real-repo incidents (four repositories, seven classes,
`../llm-fusion-2026-09-16/cases`), memory starting correct:

| ruling | count | what happened |
|---|---|---|
| HIT | 7 | wave 1 carried the answer — 2 or 3 fluidfixes |
| WIDER | 7 | the class had never been seen: widen to wave 2, then learn it |
| **MISDIRECTED** | **17** | it knew the class and dropped it → **down into the memory** |

**17 descents. 17 byte-exact rollbacks. 0 repairs. 0 wrong.** Each descent wrote its incident into
`test_dispatch.py`, confirmed the suite went red, and dispatched 13 fluidfixes over `dispatch.py` — the 9
shipped classes plus the 4 taught at the memory's own level (`memory_rules.py`) — and every one refused.

### Why it refused, exactly

The answering class sat at index 4, 5 or 6 of `remembered`, so the cap would have needed to jump by **3, 5
or 5** — and the shipped literal class moves a literal by one, as does the class taught at this level. **No
fixed value works either**: the cap here would have to be 7 and would grow with every class learned.

The repair the suite actually describes is not a number at all:

```python
    for k in remembered[:WAVE1_CLASSES]:   ->   for k in remembered:
```

Drop the recency slice. Checked: every misdirected answer's class *is* in `remembered`, so carrying all of
`remembered` satisfies all 17 appended tests. It is one line, and it is a structural rewrite, not a literal
move — the same shape as the four one-line rewrites the model-bug study found outside the vocabulary.

**So the loop closes and grows in three directions, and at the bottom it meets the same ceiling measured
everywhere else today.** The ruling is sound, the descent is sound, the judge is sound, the rollback is
byte-exact seventeen times over — and the vocabulary reaches a mechanical subset, here as everywhere. That
is the honest shape of the thing: `WAVE1_CLASSES` was never the fault, it was the symptom of a policy that
ranks when its own test says it must cover. **A fan-out must cover, not rank** — §2 of the lake result,
arrived at again from underneath.

### Not claimed

- The survey per repository is built from the recorded corpus — every (file, class) pair is one some case
  in that repository actually exhibited — not from a live `SURVEY` run. It is coarser than the real thing.
- 31 incidents, one memory, one break-free run. The 17 refusals are one fault repeated, not 17 faults.
- No descent went below level 2: the memory's own memory (`repairs-a-memory`) stayed empty because nothing
  ever repaired a memory, so the fixed point is still unreached by measurement.
