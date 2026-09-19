# Auditing the taught classes — two of four had the same defect

Class 7's defect was found only because it shipped a wrong repair into rich. That is the wrong way to find
one. So every taught class was audited for the same failure shape:

> **The signal generalises and the semantics do not.** A class is taught from one worked example. Its regex
> correctly recognises every line that could carry the fault; its applier only produces a correct line for
> the shape of the example it came from.

Each class was run outside its teaching shape, with the suite judging, and — where it produced a repair —
the repaired program was then checked **on a second, independent input**. That last step is the one that
matters: a class that produces a line the suite rejects is merely narrow, while a class that produces a
line the suite *accepts* and that is wrong is a latent false accept.

## Findings

| class | outside its teaching shape | verdict |
|---|---|---|
| 4 `missing-separator-before-appended-token` | refuses on `,`-joined and `-`-joined strings | **narrow, never wrong** |
| 5 `mutating-call-whose-result-is-dropped` | `xs.pop()` → `return xs.pop() or xs` | **latent false accept** |
| 6 `inverted-bare-guard` | correct on `if` and on `while` | **sound** |
| 7 `len-as-last-index` | ` - 1` trailed outside the multiplication | **shipped wrong into rich** — fixed by the placement law |

**Two of four.** And both failed the same way.

## Class 5, demonstrated

The applier proposed `return CALL or RECEIVER`, which is correct only where `CALL` answers `None`. Its
signal matches *any* bare method call:

```
xs.append(v)   ->  return xs.append(v) or xs      correct   — append answers None
xs.pop()       ->  return xs.pop() or xs          WRONG     — pop answers the item
```

It is not merely narrow. It is a **wrong accept** waiting for the right test:

```
drop_last([1,2,0]) == [1,2]    passes — the popped 0 is falsy, so `or` reaches xs
drop_last([9,8,7])             returns 9, not [9,8]
```

The suite accepted a program that is wrong on almost every input, because the one input it was given
happened to pop a falsy value.

## The fix, and why it is not a special case

Whether a call answers `None` is not decidable from the line, so the applier must **stop needing to know**.
A tuple discards the result positionally:

```python
return (CALL, RECEIVER)[-1]
```

The call still happens, for its effect; its answer is never consulted. Measured across method kinds, with
the suite judging and each repair re-checked on a second input:

| case | before | after |
|---|---|---|
| `pop`, popped item truthy | refused | **correct** |
| `pop`, popped item falsy — the trap | **accepted but wrong** | **correct** |
| `setdefault` | correct *by luck of a falsy default* | correct |
| `append` — the taught shape | correct | correct |
| `sort` | correct | correct |

The re-authoring **removes a false accept and widens the class at the same time**: `pop` now repairs where
it previously refused.

## What this says about teaching from one example

Both defects are the same mistake, made twice, by whoever wrote the class — me. An example teaches what the
fault *looks like*; it does not teach what the fix must *mean*. The signal is the easy half and it
generalises for free. The applier is the hard half and it silently carries every assumption of its example:
that `len(...)` is the whole right-hand side, that the mutating method answers `None`.

**A class should be audited outside its teaching shape before it is taught, not after it ships something
wrong.** That audit is mechanical — vary the syntactic context, keep the suite as judge, and re-check every
accepted repair on an input the test did not use.

## Not claimed

- Four classes. Two more exist in the earlier session file that were not exercised here (`4` and `5` of
  `taught-2026-09-16`, which the later dictionary overrides).
- The second-input check is hand-written per case. Automating it is the same problem as the oracle problem
  and is not solved here.
- Class 4 is recorded as "never wrong" on three separator shapes, not proven so.
