# A model as a second judge — pilot, n = 4

## Not "replace the oracle". "Add a judge in series."

Replacing the suite with a model loses the one property that made every repair in this project safe: a
model can approve, and an approval that nothing checks is exactly the failure the whole design exists to
avoid. A model **in series** behind the suite has the opposite character:

> A patch must pass the suite **and** survive review. The model can only *reject* what the suite accepted.

That is monotone. It cannot create a false accept — every patch it sees has already passed the full suite,
re-check, collateral and uniqueness gates. Its only cost is refusing repairs that were in fact correct.

So there are exactly two numbers worth measuring, and both need controls: does it catch the patches the
suite wrongly accepted, and how many correct patches does it refuse?

## The material

The two false accepts found on real history, and — as controls — **the maintainer's own committed fixes for
the same two bugs**:

| | patch | truth |
|---|---|---|
| A | `pos = int((cut / cell_length) * len(text) - 1)` | wrong — fluidfix shipped this |
| B | `pos = int((cut / cell_length) * (len(text) - 1))` | **correct — the maintainer's commit** |
| C | `padding=(0, 1)` → `(0, 0)` | wrong — fluidfix shipped this |
| D | `first = frame_index == 1` → `== 0` | **correct — the maintainer's commit** |

Each reviewer is told the patch already makes the failing test pass, and asked only whether it fixes the
underlying bug.

## Side by side looks much better than it is

Shown all four together, the model scored **4 of 4**. That is not the gate's job. A real gate sees one patch
with no rival beside it — and the difference is the same one the ambiguity ruling showed earlier, where an
overfit patch was caught 14 of 14 *with* a rival and certified 14 of 14 *alone*.

Re-run with one patch per reviewer, in isolation, each prompt self-contained:

| patch | truth | side by side | **isolated** |
|---|---|---|---|
| A | wrong | REJECT ✓ | **REJECT ✓** |
| B | correct | ACCEPT ✓ | **REJECT ✗** |
| C | wrong | REJECT ✓ | **REJECT ✓** |
| D | correct | ACCEPT ✓ | **ACCEPT ✓** |

**Isolated: 3 of 4.** Both wrong patches caught — which is the whole point, and the thing the minimal-delta
gate managed zero times out of two. One correct patch refused: the maintainer's own shipped fix, rejected
with a fluent and wrong argument ("breaks the proportional mapping for narrow characters").

## What that means in this regime

| | |
|---|---|
| false accepts removed | **2 of 2** |
| correct repairs refused | **1 of 2** |

A 50% false-refusal rate would be ruinous for a tool whose product is free repairs. It is close to free
*here*, because the measured yield on real history is already zero: across 57 real tested bug fixes the
vocabulary produced **0 correct repairs and 2 wrong ones**. A gate that removes both wrong ships and costs
half of a yield that is zero is, in this specific regime, a clear win.

That is an argument about a bad situation, not a good gate.

## Not claimed

- **Four cases.** Two positive, two negative. This is a pilot and the rates carry no confidence at all.
- **I wrote the bug descriptions**, and a description is a channel: "a blank line is missing" plausibly
  steered the reviewer of patch C toward rejecting a horizontal-padding change. A deployed gate would have
  the failing test output, not prose written by someone who knows the answer.
- **No API key exists in this work.** These are sandboxed subagents on Haiku, not calls to the Anthropic
  API, and the wording used here says so.
- **The reasoning is unreliable even when the verdict is right.** Patch B was refused with a confident,
  incorrect explanation, and in the side-by-side run patch B was *accepted* with an explanation that called
  `len(text) - 1` a denominator. The verdicts are worth more than the arguments attached to them, which is
  an uncomfortable thing to build on.
- This measures a gate on **two bugs from one repository**. Whether it holds at the scale where it would
  have to run — every green, on every red build — is untested, as is its token cost there.
