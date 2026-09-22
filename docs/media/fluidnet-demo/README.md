# fluidnet — the proof video

`fluidnet.mp4` — 3:52, 1920×1080. A real repository, a real terminal, the real tool. Every command runs
live while recording; nothing is generated, nothing is pre-repaired.

| file | what it is |
|---|---|
| `setup.sh <dir>` | rebuilds the demo repo to the exact starting state: green, plus one regression commit |
| `fluidnet.tape` | the VHS script; `vhs fluidnet.tape` re-records from a fresh `setup.sh` |
| `live.sh <dir>` | the same scenes, run live in any terminal, with banners |
| `rules.py` | what teaching looks like: two classes, each with a signal, a rewrite, and a **property** |
| `rules_naive.py` | the same, but `len-as-last-index` taught the naive way and without its property — for scene 8 |

## What the video shows, in order

1. `fluidfix selfcheck` — the six integer laws that decide everything, re-derived on this machine. No model.
2. A teammate's commit turned `(1 + VAT)` into `(1 - VAT)`. The suite goes red.
3. A **shipped** class repairs it — zero teaching, zero tokens — judged only by the repo's own tests, and commits.
4. A shape it was never taught (`sum` → `max`): **refused**, exit 2, `git status` clean, every attempt in the
   refusal report with the test that killed it.
5. Teaching: `rules.py`. A class is a signal, a rewrite, and a property — written once, beside the code.
6. The taught class repairs `ledger.first()` → `ledger.last()`, judged by the suite.
7. The same class in a different file, a position it was never shown: repaired, free.
8. **The proof.** The suite for `cut_at` only ever asks `k = 1`. The naive class proposes
   `int(k * len(text) - 1)` and the suite accepts it — `--dry-run` shows the diff, green. One line of
   Python shows it is wrong at `k = 2` (11, not 10). A suite alone would have shipped this. rich's did.
9. The **property** is typed live — nine lines: the candidate must equal the original with `len(x)` replaced
   by `(len(x) - 1)`, for every length. Run again: **REFUSED before any suite run**. The refusal report
   carries the refuting input.
10. `rules.py`, where the placement law decides where the token goes: `int(k * (len(text) - 1))`. Proven,
    then accepted by the suite, then committed.
11. The vocabulary: nine shipped classes, two taught.

## To re-record

```
zsh setup.sh /Users/kanchetidevieswar/neo/demo/ledgerly
vhs fluidnet.tape
```

The tape puts `fluidfix/.venv/bin` first on PATH so it runs the repository's source, not a global install.
