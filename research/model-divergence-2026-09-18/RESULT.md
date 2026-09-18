# Pointing the judge across authors instead of across candidates — measured 2026-09-18

`differ` exists to answer one question for the engine law: *are two green candidates two different
programs?* Point the same machinery across **authors** and it answers another: given one English
specification, what did each model actually implement?

Eighty implementations, four writers, thirty-two specifications, each answered independently from prose
alone. For every spec, inputs are harvested from the suite's own literals, mutated and bisected, and every
implementation is run over the same pool. Where two implementations that **both pass the tests** disagree,
the disagreeing input is the artefact. **4.3 seconds for the whole corpus.**

## What came out

**8 of 32 specifications are ambiguous** — implementations that all pass their tests and still disagree,
22 disagreeing pairs, each with a concrete witness:

| specification | witness | what the writers decided |
|---|---|---|
| `page_count(10, -5)` | a negative page size | gemma3:4b `-2`, haiku/qwen `-1`, phi4-mini `0` |
| `clip_exclusive(7, 0)` | a zero-length sequence | gemma3:4b/haiku `0`, phi4-mini/qwen `-1` |
| `nth_from_end([2,3], 3)` | n past the end | gemma3:4b/phi4-mini `None`, qwen `3` |
| `progress(3, 2, 10)` | more done than total | gemma3:4b/haiku `15`, qwen clamps to `10` |
| `truncate_words('a b c d', 0)` | a zero word limit | haiku `' ...'`, phi4-mini `'...'` |
| `percentile([], 50)` | an empty list | haiku `IndexError`, qwen `ValueError` |
| `parse_duration('s54')` | a malformed duration | haiku `0`, qwen `ValueError` |
| `columns([1,2,3,4,5], -2)` | negative column count | three writers `IndexError`, qwen `[]` |

**Every one of the 22 is an input the prose never defined.** Not one is a disagreement about specified
behaviour — 77% carry an empty, zero or negative argument outright, and the other five (n past the end,
done exceeding total, a malformed string) are equally outside what the spec pinned down.

## Why that is a theorem, not a limitation

Two correct implementations of a fully specified function **are behaviourally identical** on every input the
spec defines. So a black-box probe can only ever find differences where the specification is silent. This is
the ceiling of the technique, and it is a mathematical one, not an engineering one.

Which means the honest name for what this does is not *reverse-engineering the model*. It is:

> **an ambiguity detector for specifications, that also records how each writer's prior filled each gap.**

That is worth something on its own — hand it N implementations of one spec, from N models or N contractors,
and it names the exact inputs your prose failed to pin down, in seconds, with no ground truth.

## Separating a hard spec from a weak writer

The same corpus decomposes failure without any judgement call:

| broken by | specification | reading |
|---|---|---|
| 3 of 3 local writers | `insert_sorted` | the **spec** is hard — "AFTER any equal values" is `bisect_right` |
| 2 | `percentile`, `trim_to_fit`, `truncate_words` | mostly the spec |
| exactly 1 | `backoff`, `countdown` (gemma3:4b); `progress`, `windows` (phi4-mini); `clip_index` (qwen3.5:4b) | that **writer** slipped |

## Structure: what the behaviour cannot show

Algorithmic differences — `bisect` versus a loop, integer arithmetic versus `math.ceil` — are invisible to a
behavioural probe by construction, so they need the AST instead. Measured across every spec each writer
answered:

| writer | comprehension | math module | guard clause | median body lines |
|---|---|---|---|---|
| haiku | 12% | **0%** | 44% | 5 |
| phi4-mini | 12% | 6% | 56% | 6 |
| gemma3:4b | 6% | 6% | 62% | 6 |
| qwen3.5:4b | 9% | 3% | 62% | 6 |

Directionally Haiku writes shorter, flatter code and never reached for the math module — and at 32 samples
per writer **none of these gaps is significant**. 44% against 62% is 14 specs against 20. This table is
reported because it was measured, not because it separates the models. It does not.

## So, honestly

**Yes, and the subject is the specification, not the model.** With no access to weights, training data or
logits, the judge's own machinery recovers which specs are ambiguous, exactly where, and how each writer
resolved each gap — mechanically, in seconds.

**No, it does not tell you how a model works.** Behaviour outside a spec reveals a convention, not a
mechanism; structure inside 32 samples does not separate these four writers at all. Nothing here is
interpretability, and calling it that would not survive the first question from someone who does it.

## Not claimed

- Four writers, thirty-two specs, one pool per spec. A probe, not a benchmark.
- The pool is harvested from the tests' own literals, then mutated and bisected, so a divergence far from
  anything the tests mention is unreachable by construction — measured separately at 0 of 14
  (`../certify-2026-09-18`). The 8 ambiguous specs are a **lower bound**; there may be more.
- Ambiguity here is measured *between writers*. A spec all four resolve the same way is not thereby
  unambiguous — they may share a prior.
- The AST features are hand-chosen and shallow. A negative result on them is not a negative result on
  structural fingerprinting in general.
- Nothing here changes the product. It is `differ.harvest_seeds`/`build_pool`/`evaluate`, unmodified.
