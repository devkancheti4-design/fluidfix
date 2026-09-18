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

## What is not claimed

- Level 0 is cited from the recorded runs in `research/lake-2026-09-18`, not re-run here; levels 1 to 3 are
  live in every row above.
- Two memory faults, both inside or one teaching step away from the vocabulary. A memory fault that is not
  a shape — a wrong dispatch *policy* rather than a wrong token — is outside this and would reach a human.
- The fixed point is structural, not a proof of termination under adversarial memory faults.
