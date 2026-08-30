# fluidfix

**Zero-token repair decisions for mechanical single-line bugs.** A
machine-authored four-instruction kernel decides which repair to try, your
test suite judges it, and a language model — when you use one at all — is only
ever the eyes. Every output is either a repair your suite accepts — measured
byte-exact in 26 of 26 accepted repairs on the benchmark — or an explicit
refusal. There is no "plausible fix" branch.

```
pip install fluidfix            # core: zero runtime dependencies
pip install "fluidfix[llm]"     # adds the Claude Opus 5 observer
```

```bash
# commit-and-forget: watch the suite, restore what breaks, refuse what is novel
fluidfix guard path/to/project --python path/to/venv/bin/python --interval 900 --commit

# or one-shot on a known defect file
fluidfix repair path/to/project --file pkg/module.py --python path/to/venv/bin/python
```

```python
from fluidfix import Oracle, build_packet, MechanicalObserver, repair

oracle = Oracle("path/to/project", python="path/to/venv/bin/python")
packet = build_packet(oracle, "pkg/module.py")          # mechanical, 0 tokens
observations = MechanicalObserver().observe([packet])[0]
print(repair(oracle, "pkg/module.py", observations).summary())
```

## Measured, not promised

All numbers below are from a live benchmark on 33 injected single-line bugs in
five real PyPI libraries (humanize, inflection, natsort, parse, wcwidth), each
library's own suite as the oracle, run 2026-08-30. Per-bug data and
methodology ship with this package in [docs/BENCHMARK.md](docs/BENCHMARK.md);
the corpus, injector, and recorded baselines are from
[fluid-router](https://github.com/devkancheti4-design/fluid-router)
`benchmark/`.

|                             | fluidfix (Claude Opus 5 as eyes) | full Claude Opus 5 debugging |
|-----------------------------|-----------------------------------|------------------------------|
| in-vocabulary byte-exact    | **26/27**                         | 22/27 (5 green-only)         |
| out-of-vocabulary           | 6/6 refused honestly              | 5/6 exact                    |
| silently wrong repairs      | **0**                             | —                            |
| tokens¹                     | **125,402 total (3,800/bug)**     | 1,322,802 (40,084/bug)       |
| decision cost after that    | **0 tokens²**                     | ~40k tokens each time        |

- The observer named the correct defective line **33/33** from lean packets
  averaging ~1,060 tokens.
- The mechanical localiser (no model at all) put the true defective line in
  the packet for **33/33** bugs, at zero tokens.
- The kernel's decisions are invariant under all 16 renumberings of the act
  vocabulary: **432/432** live decisions correct; a frozen lookup table
  scores 27/432 on the same test.
- With no model anywhere, fluid-router's recorded blind-search kernel scores
  17/27 byte-exact at zero tokens — without the localisation this package
  adds. fluidfix's mechanical mode is validated end-to-end but not yet
  corpus-scored; see [docs/BENCHMARK.md](docs/BENCHMARK.md).

¹ Fleet-level harness measurement, all agent context included; the two token
columns use different accounting and support the ~10× ratio, not a precise
figure. Provenance: `docs/data/lean_arm_tokens.json`.
² fluid-router2's C verifier measures its kernels at 1.55 ns/decision; this
package's pure-Python reference is ~0.6 µs. Either way: no tokens.

## The guard: deploy, commit, forget

Most deployed software is not being actively developed — it is being kept
alive. `fluidfix guard` is built for exactly that. It needs no defect file:
when the suite goes red it finds the fault file mechanically (traceback
frames, else failing-test coverage ranking), repairs it, and — with
`--commit` — records the restoration:

```
$ fluidfix guard . --commit
[16:43:06] billing.py: repaired line 2 in 4 suite runs (0.7s):
  - return p * (1 - rate)
  + return p * (1 + rate)
  committed
```

Run it one-shot in CI (exit 0 green/repaired, exit 2 refused), or under cron
with `--interval`. Green suite: it touches nothing. Novel fault class: it
refuses, leaves the tree byte-identical, and writes
`.fluidfix/last_refusal.json` — the teach-me signal for `register()` below.

## How it works

```
suite fails ──► localise (frames ∪ failing-test coverage ∪ AST spans; 0 tokens)
            ──► observe (mechanical regexes, or one batched Claude call)
            ──► EMIT names the fault      m & (-m)
            ──► route() picks the act     15 & ((x>>4)+((x>>8)-x))   ◄ the brain
            ──► apply & run the suite     green → HALT
            ──► ADVANCE and try the next  m - (m & (-m))
            ──► empty mask → refuse, never guess
```

The routing expression was authored by a program-synthesis engine and is
vendored verbatim from [fluid-router](https://github.com/devkancheti4-design/fluid-router)
(verdict: `minimal in D∩I`); the loop discipline is
[fluid-router2](https://github.com/devkancheti4-design/fluid-router2)'s
EMIT/ADVANCE/HALT, exhaustively verified on all 256 mask states. Run the
proofs yourself, offline, in seconds:

```bash
fluidfix selfcheck
```

## Safety properties

- **Refuses on a green suite.** Searching without a failing test has been
  measured to corrupt working code while reporting success; `repair()` checks
  first and returns "nothing to repair".
- **Refuses outside its vocabulary.** and/or confusion, flipped booleans,
  `*`/`/` swaps have no act — the mask comes back empty and fluidfix says so,
  loudly, instead of guessing.
- **Restores byte-exactly on failure.** Every rejected candidate is rolled
  back; a refused repair leaves the tree untouched.
- **Bounded candidates.** A candidate that will not terminate is a failed
  candidate, not a hung pipeline.
- **The oracle is defended.** Stale-bytecode, plugin-collision,
  exit-first-swallows-coverage, and truncated-node-id failure classes are all
  encoded in `oracle.py`, each one a scar from a measured harness defect.

## Teaching it new classes — the maintenance loop

The four shipped acts are a starter dictionary, not a ceiling. A fault class
is teachable the moment its repair can be expressed as a mechanical transform
of the defective line:

```python
import re
from fluidfix import register

register(4, "logic-flip", 'an "and" that should be "or", or vice versa',
         re.compile(r"\b(?:and|or)\b"),
         lambda line, obs: (line.replace(" or ", " and ", 1) if " or " in line
                            else line.replace(" and ", " or ", 1)))
```

One registration, once — the router is never edited: it infers the new
class's act code from the same single worked example
(`tests/test_regressions.py` shows an and/or bug going from refused to
repaired with exactly this snippet). That is the deployment story fluidfix is
built for: ship it on a maintained codebase, let the known classes repair
themselves for free, and when an update introduces a novel fault class, hand
that class to fluidfix once and maintenance is free again.

The honest boundary: classes whose repair needs information absent from the
defective line — a wrong variable, a missing guard, a different algorithm —
are not transforms, and are refused rather than attempted. (Measured share of
real one-line fixes that are single-token substitutions: ~16%; see
fluid-router's `benchmark/domain/`.) The refusal is your signal to spend a
frontier model exactly once, on the class, never again on its instances.

## Licensing

AGPL-3.0-or-later. Section 13 (network use) applies. If AGPL does not suit
your use — proprietary products, SaaS without source offer — commercial
licenses are available: see [COMMERCIAL.md](COMMERCIAL.md).
