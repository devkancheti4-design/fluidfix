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

## Is the choice a stable signature, or a coin flip? (`latent.py`)

If a writer's resolution of an undefined input were read out of something shared and structured, the **same**
writers would keep agreeing with each other across different ambiguous inputs. If it were a local per-task
choice, the grouping would shuffle. That distinction is testable from behaviour alone.

46 undefined inputs over 8 specifications (41 split the writers two ways, 5 split them three ways). For each
pair, the fraction of inputs where they gave the same answer, against a null that **shuffles writer labels
independently per input** — preserving how many writers agree on each input and destroying only *who*.
50,000 permutations, two-sided, Bonferroni-corrected for six pairs (α = 0.0083):

| pair | n | observed | null | p | |
|---|---|---|---|---|---|
| gemma3:4b / haiku | 33 | **61%** | 37% | **0.0069** | significant |
| haiku / qwen3.5:4b | 41 | **12%** | 30% | 0.0101 | misses correction |
| gemma3:4b / phi4-mini | 21 | 57% | 39% | 0.1222 | no |
| phi4-mini / qwen3.5:4b | 21 | 57% | 39% | 0.1214 | no |
| gemma3:4b / qwen3.5:4b | 33 | 21% | 37% | 0.0752 | no |
| haiku / phi4-mini | 26 | 19% | 31% | 0.2094 | no |

**One pair of six survives correction, barely.** A second is a systematic *dis*agreement that just misses it.
Counting who is the odd one out when exactly one writer stands alone: qwen3.5:4b 19 times, haiku 10,
gemma3:4b 3, phi4-mini 2 — qwen carries a visibly different convention prior.

So the choices are **not pure noise**: there is weak, detectable structure in who agrees with whom. Two
things keep that from being a result. It is one significant pair out of six at n = 46, which is a
hypothesis, not a finding. And the structure does not follow scale or family — the pair that agrees most is
a 4B local model and Haiku, while the three 4B models do not group together, which is the opposite of what
a simple story about model lineage would predict.

**What this cannot be called is a claim about latent space.** Nothing here measures a representation: no
weights, no activations, no logprobs. Behaviour is downstream of representation and many-to-one — different
internal computations can produce identical outputs — so an output pattern constrains hypotheses about
internals without revealing them, and this pattern is equally explained by overlapping training data,
instruction-tuning conventions, or documentation both writers saw. The experiment that would earn the
stronger claim is a different one: sample each writer many times at temperature above zero, or read
logprobs over the competing conventions, and compare the **distributions** rather than one greedy answer.
That turns 46 binary choices into a far richer signal, and it is the honest next step.

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
