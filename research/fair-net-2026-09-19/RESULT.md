# The net, tested fairly — never told the file

Every earlier real-history number came from **one guard on a file I handed it**. This is the net doing its
own job: survey the territories, dispatch, grow by ruling, stop on the first green, and then be judged on
whether the line it produced equals the **original bytes**. On the real-repo corpus behind "7 of 22", with
the taught classes in their post-audit state.

## It works cold

```
[click/lenm1-1] survey: 13 territories; memory knows nothing; every (territory, class) pair would be 36
  round 1: core.py:1   round 2: core.py:0, types.py:1   …   round 9: utils.py:7
    green: src/click/utils.py class 7 (4 suite runs) — the net stops growing
[click/lenm1-1] EXACT | 26 nodes of 36 | 108 suite runs | 277s
```

Not told the file. Found it. **Byte-exact.**

## Teaching plus memory is what makes it cheap

The same fault, the same corpus, the only difference being whether the shape is remembered:

| | nodes | suite runs | wall | verdict |
|---|---|---|---|---|
| cold | 26 of 36 | 108 | 327 s | EXACT |
| **warm — the shape known** | **1** | **4** | **41 s** | EXACT |

**26 nodes become 1.** Most of the 41 seconds is the survey.

## And most of the cold cost was self-inflicted

The survey ordered territories by **most-executed lines first**, which front-loads the biggest, most
travelled files: on click it opened `core.py`, `types.py` and `testing.py` before reaching `utils.py`,
where the fault was. Meanwhile the failing test run was already saying where to look.

**Measured across the click corpus: the failure names the faulty file in 4 of 7 cases** — a traceback
frame names it, or the failing test's own path does. That information arrives before the net opens
anything, and the ordering was discarding it.

`net_reveal.py` scores each territory before the search starts — 2 if a traceback frame names it, 1 if a
component of the failing test's path matches its stem, 0 otherwise — and falls back to executed lines
inside each band. Nothing else changes.

| `click/lenm1-1`, cold | nodes | suite runs | wall |
|---|---|---|---|
| ordered by executed lines | 26 of 36 | 108 | 277 s |
| **ordered by what the failure says** | **16** | **47** | **208 s** |

Round 1 opens `utils.py` instead of `core.py`. **38% fewer nodes, 57% fewer suite runs**, from information
that was free and already on screen.

## Two harness defects found while building this, both of which looked like results

- **A dictionary that dropped two taught classes.** The "combined" file spent slots 4 and 5 on the classes
  learned from model-written bugs and thereby dropped `flipped-boolean-operator` and `get-without-default`
  — exactly what this corpus needs. The net then exhausted its budget on `click/andor-1` **without ever
  holding the class that repairs it**. A user dictionary owns four slots and there are now six taught
  classes competing for them; that is a real constraint, not an accident.
- **A probe that ran after the tree was reset.** The failure-ordering prior read the suite *after*
  `git reset --hard`, so it saw a green suite, found no failing tests, and silently fell back to the old
  ordering while reporting "the failure points at nothing". It looked like the idea not working.

With the corpus-matched dictionary, the taught classes restore the original bytes on **15 of 15** of their
own corpus cases.

## Not claimed

- One repository. The click corpus is 7 cases; arrow, rich and sortedcontainers have 25 more and the
  template clones for them are not built.
- The cold/warm pair is one fault shape. The collapse to a single node is what memory does when the
  remembered class is *scarce*; a class matching many territories saves far less, which is measured
  elsewhere.
- The failure-ordering prior is measured on one case end to end (26 → 16) and on 4-of-7 for the underlying
  signal. The full seven-case comparison is running.
- `net_reveal.py` is a copy of `net.py` with the ordering changed. It is not merged into the product.
