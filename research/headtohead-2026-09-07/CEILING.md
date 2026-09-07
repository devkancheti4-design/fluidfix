# The vocabulary is not the bound. The SHAPE is.

RECURRENCE.md measured how many real fixes match **the six classes fluidfix
ships**. That is the wrong denominator for what the tool can do, because a class
is *taught*: `register()` one worked example and its whole family becomes
repairable — including values the vocabulary has never seen. fluidfix has
already been measured deriving a field name it was never shown.

So the honest ceiling is: how many fixes are a **single line** at all (what a
single-edit search can reach, whatever the token turns out to be), and how many
change **one token of any kind** (what one taught class can cover).

Reproduce: `python3 ceiling.py <path-to-a-full-clone>`

| repo | fix commits | one LINE | one TOKEN, any kind | the six SHIPPED classes |
|---|---|---|---|---|
| cglm | 253 | 41 — **16.2%** | 22 — **8.7%** | 6 — 2.4% |
| raylib | 1,236 | 165 — **13.3%** | 76 — **6.1%** | 32 — 2.6% |
| Box2D | 319 | 21 — **6.6%** | 9 — **2.8%** | 14 — 4.4% |

**Teaching roughly doubles to triples the addressable share** over what ships in
the box — 2.4% to 8.7% on cglm, 2.6% to 6.1% on raylib. And the architecture's
true ceiling, any single-line fix, is **7% to 16% of all bug fixes**.

## Why the shipped vocabulary undercounts so badly

The commonest single-token changes in these repos are not boundary flips and
off-by-ones at all. They are project-specific:

    TraceLog -> TRACELOG        malloc -> RL_MALLOC       float32 -> float
    WARNING -> LOG_WARNING      RMDEF -> RMAPI            NULL -> nullptr
    transfrom -> transform      _mm_load_ps -> glmm_load  GLvoid -> void

**No fixed catalogue could contain these.** The token is unguessable — it is
this project's macro, this project's typedef, this project's typo. But the
SHAPE is completely learnable, and that is the whole argument: you show it one
worked example and it repairs that family forever, deriving the specific value
from your own source rather than from a list someone shipped.

That is what "high-entropy" means here. The entropy is in the VALUE, which
fluidfix mines from your repository. The SHAPE is low-entropy, and the shape is
what a class captures.

## Caveat, stated plainly
The substitution table above is counted across ALL commits, not only fix
commits, so it is dominated by refactors and migrations rather than bugs. It is
shown to make the point about *entropy and shape*, not as a defect frequency.
The percentage columns ARE gated on fix-worded commits.

## What it does not change
It does not change the pricing arithmetic much. raylib's 13.3% is ~13 single-
line fixes a year, not 130. The licence threshold still sits far above what
these three repos produce, and the pilot is still the honest first step.
