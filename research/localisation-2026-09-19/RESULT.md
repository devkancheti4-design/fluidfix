# Does the localisation earn its tokens? On the case where it should matter most, no.

The cost split — 0 tokens for the search, ~96,000 for the model — has been quoted several times, always with
the caveat that it shows the two halves cost *different amounts*, not that the cheap half makes the expensive
half cheaper. This tests that, and the test never got as far as a model.

## The right case

The localisation can only be worth anything when the failure does **not** already name the faulty file. A
raising error prints `file.py:line` for free; only an *assertion* failure hides the cause. `click/cmp-1` is
exactly that shape:

```
>       assert actual == expected
E       AssertionError: assert '  Lorem ipsu...iscing elit\n' == '  Lorem ipsu...iscing elit\n'
tests/test_formatting.py:436: AssertionError
FAILED tests/test_formatting.py::test_help_formatter_write_text
```

The failure names `test_formatting.py`. The fault is in `src/click/_textwrap.py:111`.

## What the localisation actually produces

Coverage of the failing test, ranked by the guard, over the whole package:

| rank | file | ranked lines |
|---|---|---|
| 1 | `src/click/core.py` | 107 |
| 2 | `src/click/types.py` | 62 |
| 3 | `src/click/_compat.py` | 35 |
| 4 | `src/click/termui.py` | 29 |
| 5 | `src/click/testing.py` | 26 |
| 6 | `src/click/utils.py` | 22 |
| **7** | **`src/click/_textwrap.py`** | **the fault** |

**Seventh of fourteen.** Middle of the pack, because the ranking counts ranked lines and big files have
more of them. Handing that to a model would point it at `core.py` first.

So the A/B was not run. There is no point measuring whether a model is cheaper when given an artefact that,
on this case, is worse than no artefact at all.

## What this settles

**The token-saving claim is not supported**, and this is the second reason it fails rather than the first.
Earlier it could not be tested because the failure already named the file — a *raising* fault localises
itself for free, so the guard adds nothing. Now, on an *assertion* fault where the guard is the only thing
that could localise, it ranks the guilty file seventh.

Between those two cases the claim has nowhere left to stand:

- the failure names the file → the localisation is redundant
- the failure does not name the file → the localisation does not find it either

What the guard does produce, and it is not nothing, is a **refusal that names every class it eliminated and
the test that killed each candidate**. That is a different artefact and its value to a model is also
unmeasured.

## Three harness defects found while setting this up, all previously recorded, all repeated

- **A copied venv keeps an absolute `.pth`.** `cp -a` of a tree containing `.venv` produced two worlds that
  both imported click from the *template*, so every mutation applied to them was inert and the suite stayed
  green. Fixed by building each world's venv in place.
- **A concurrent run mutating the shared template.** A liveness check reported 7 of 7 cases RED while its
  own mutations were inert — it was reading the template, which a `sequence.sh` net run was mutating during
  its survey. The 7/7 was another process's fault, not the cases'.
- **`pytest-cov` missing, for the third time.** Without it `build_packet` returns no executed lines and the
  localisation comes back empty, which looks exactly like "nothing to localise".

Each of these produces a plausible-looking number. None of them is a result.
