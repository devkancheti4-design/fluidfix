# fluidnet — the organs fused, and the loop measured working (2026-09-18)

Everything measured separately today is one mechanism. `fluidnet.py` runs it as one: a single incident
enters a repository, and every organ that touches it is the same organ at a different scale.

The world is eight real modules with their own tests (correct implementations from
`../model-bugs-2026-09-18`), 23 (territory, class) pairs, and one real fault from the shipped vocabulary.
Nothing is judged by anything but the suite.

## What one run does

| organ | what it is |
|---|---|
| **SURVEY** | which territories can exhibit which classes — fluidfix's own signals, read off the code |
| **DISPATCH** | the memory (`../closed-loop-2026-09-18/memory/dispatch.py`) says what wave 1 carries |
| **GROW** | one small fluidfix per node; the node's **ruling** decides what the net spawns next |
| **CERTIFY** | a green is not a repair: red before, green on the full suite, stable on re-check, byte-exact rollback otherwise |
| **LEARN** | the answering class → the lake's memory; the class that repaired a memory → the head's |

and the third direction, which is what makes it a loop rather than a search:

> **MISDIRECTED** — the memory *remembered* the answering class and wave 1 dropped it. Wider and deeper both
> search a repository that was never the problem. Go **down**: the memory file becomes the territory, the
> incident becomes a test, and a fluidfix repairs the memory.

## Measured

| run | memory holds | nodes of 23 | wall | certificate | byte-exact |
|---|---|---|---|---|---|
| cold | nothing | 22 | 19.3 s | CERTIFIED | yes |
| warm | `[10]` | **5** | 5.2 s | CERTIFIED | yes |
| warm | `[0, 10, 3]`, answer carried | 10 | 9.7 s | CERTIFIED | yes |
| warm | `[10, 0, 3]`, **answer dropped** | 14 | 13.6 s | CERTIFIED | yes |

The memory turns a 22-node crawl into 5. And on the last run the loop closed on itself:

```
DISPATCH  memory knows [10, 0, 3] -> wave 1 is 10 node(s)
RULING    MISDIRECTED — it knew this class and wave 1 dropped it -> DOWN into the memory
          repaired by class 4 after 10 tried
          wave 1 now 14 node(s); carries the answer: True
GROW      node 14: pkg/windows.py class 3 -> SHIP (the first green stops the net)
CERTIFY   CERTIFIED — red before, green on the full suite, stable on re-check
          restored the original line byte-for-byte: True
LEARN     the lake remembers kind:3; the head remembers {'kind:4': 1}
```

**A fluidfix repaired the memory that was misdirecting the fluidfixes**, judged by the memory's own suite,
and the head now remembers which class repairs a memory — so the next descent starts with one fluidfix
instead of ten.

## The loop only works because a class was taught

`../closed-loop-2026-09-18` measured 17 descents and **0 repairs**: the memory's fault was
`remembered[:WAVE1_CLASSES]`, a *slice*, and no literal value fixes it because the correct bound grows with
every class learned. Teaching one class from one worked example — `ranks-where-it-must-cover`, drop the
bound and keep the collection — turned that run into **1 descent, 1 repair, and 17 misdirections became 1**,
because the fault never recurred. That is the only step a human still takes.

## Two honest notes

**It took the weaker of the two repairs available.** The descent above was answered by class 4 (bump the cap
2 → 3), not class 5 (drop the slice). Cap 3 satisfies every test the memory currently has, so the engine
accepted the first candidate the suite accepted — and it will misdirect again when a fourth class arrives.
*A suite that does not pin a property cannot defend it*, which is the same lesson the cap break taught.

**Two defects found while building this, both in my own harness:**
- The first warm run reported that a planted fault *had not turned the suite red*. `<` for `>` is a
  **same-size rewrite**, and CPython validates a `.pyc` on whole-second mtime plus size, so the stale
  bytecode was re-imported. `oracle.py` carries this exact scar; calling `pytest` directly threw it away.
  Judging goes through the `Oracle` now.
- `--kind 0` silently planted class 10, because the filter read `if only else MUTATIONS` and **class 0 is
  falsy** — precisely the mechanical slip this tool exists to repair.

## Not claimed

- Eight modules of one function each. The territory dimension is real but small, and nothing here is a
  repository-scale measurement.
- One fault at a time, planted from the shipped vocabulary, so the net is being asked a question it can
  answer. The refusal behaviour on faults outside the vocabulary is measured elsewhere, not here.
- The AMB → witness-search organ (`../model-divergence-2026-09-18/witness_net.py`) is **not** wired into
  this driver: no run produced two distinct greens, so there was nothing to separate. It stays a separate
  measurement until an incident forces it.

---

# The handoff: it refuses, a model writes, it certifies (`handoff.py`)

This is the loop the whole body of work points at, run end to end on a fault fluidfix has already been
measured unable to author: a **real implementation a model actually wrote**, which its own hidden tests
reject (`../model-bugs-2026-09-18`, gemma3:4b on `percentile`). The world is the same eight modules.

## 1 — REFUSE, and the refusal is the artefact

```
suite says: NameError: name 'ceil' is not defined

RULING    REFUTED — 24 nodes, 6 of them real searches, 13 suite runs, 22.2 s
          every class in the vocabulary was tried and the suite rejected every candidate
          the failure points at: pkg/percentile.py
          classes ruled out in percentile: [0, 1, 2, 3, 10, 11]
```

**Zero tokens.** A refusal that names the territory out of eight, lists every class eliminated there, and
carries the suite's own message is not a shrug — it is a localisation, and it is what gets handed onward.

## 2 — WRITE

Two models, working independently from the failing test, the file, and that refusal. Nothing else. Both
reached for the same thing the vocabulary cannot express — **a line that is not there**:

```python
+ from math import ceil
```

and both added a `rank < 1` guard the original lacked, spelled differently:

| | fix A | fix B |
|---|---|---|
| guard | `if rank < 1: return values[0]` | `if rank < 1: rank = 1` |
| tail | folded the redundant `rank == n` branch away | kept it |

**~48,000 tokens each.**

## 3 — CERTIFY, by destination

```
CERTIFY   fix_a.py: CERTIFIED — red before, green on the full suite, stable on re-check (3 suite runs)
CERTIFY   fix_b.py: CERTIFIED — red before, green on the full suite, stable on re-check (3 suite runs)
```

Neither patch resembles anything the vocabulary produces; both are whole-file rewrites with an inserted
import. The judge does not ask who wrote it or how it is spelled. **Zero tokens, three suite runs each,
byte-exact rollback between them.**

## 4 — SEPARATE: two greens, and the right refusal to make

```
RULING    AMB — 2 different programs both pass this suite. The suite cannot tell them apart,
                so it is not entitled to pick one.
SEPARATE  no input in the 76-input pool tells them apart — they may be one program spelled twice,
          which is NOT ambiguity. Certified.
```

And that conclusion is **provable, not merely unfalsified**. For a non-empty list, `n >= 1` on every
reachable path; when `rank == n`, `values[-1]` *is* `values[rank - 1]`; when `rank < 1`, B's `rank = 1`
falls through to `values[0]`, which is A's answer. Exhaustively over `n` in 1..8 and rank in −4..12: **zero
disagreements.** The pool did not fall short — the two are one program spelled twice, which is precisely
the case `differ` exists to *not* call ambiguous.

## What this run actually shows

**Destination, not path, is the unit of identity.** Every organ here decides on where a program arrives:

- the vocabulary's refusal is a statement about destinations it could not reach, not about text it could
  not write
- the certificate is granted to a whole-file rewrite it could never have authored, because it lands in the
  right place
- the ambiguity ruling fires on *two programs*, and is withdrawn on *one program spelled twice* — the
  distinction is behavioural and nothing else

**And the two halves cost different things.** fluidfix's half — searching 24 nodes, localising to one file
of eight, eliminating six classes, then certifying two patches — cost **0 tokens and 19 suite runs**. The
model's half cost **~96,000 tokens** across two writers. The refusal is the cheap half, and it is the half
that tells the expensive half where to look.

## Not claimed

- One fault, one module, two writers. A demonstration of the loop, not a benchmark of it.
- The two fixes turned out behaviourally identical, so **AMB has still never been exercised on genuinely
  different programs inside fluidnet** — the ruling fired and was correctly withdrawn. The case where it
  refuses two real rivals remains measured only in `../certify-2026-09-18`, where a rival was constructed.
- The models were given the refusal. Whether the refusal actually *helps* a model — against the same model
  with no localisation — is not measured here, and it is the obvious next experiment.
- A defect found while building this, recorded rather than hidden: the AMB branch read `ast.parse(code)
  .body[0]` for the function, which after the model's fix is the new `from math import ceil` — the very
  insertion the vocabulary could not make. Found by name now.
