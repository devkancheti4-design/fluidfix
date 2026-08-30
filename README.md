# fluidfix

**Zero-token repair decisions for mechanical single-line bugs.** A
machine-authored four-instruction kernel decides which repair to try, your
test suite judges it, and a language model — when you use one at all — is only
ever the eyes. Every output is either a byte-exact restoration your suite
accepts, or an explicit refusal. There is no "plausible fix" branch.

```
pip install fluidfix            # core: zero runtime dependencies
pip install "fluidfix[llm]"     # adds the Claude Opus 5 observer
```

```bash
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
library's own suite as the oracle, run 2026-08-30. Provenance and the full
harness: [fluid-router](https://github.com/devkancheti4-design/fluid-router)
`BENCHMARK.md`.

|                             | fluidfix (Claude Opus 5 as eyes) | full Claude Opus 5 debugging |
|-----------------------------|-----------------------------------|------------------------------|
| in-vocabulary byte-exact    | **26/27**                         | 22/27 (5 green-only)         |
| out-of-vocabulary           | 6/6 refused honestly              | 5/6 exact                    |
| silently wrong repairs      | **0**                             | —                            |
| tokens                      | **125,402 total (3,800/bug)**     | 1,322,802 (40,084/bug)       |
| decision cost after that    | **0 (1.55 ns/decision)**          | ~40k tokens each time        |

- The observer named the correct defective line **33/33** from lean packets
  averaging ~1,060 tokens.
- The mechanical localiser (no model at all) put the true defective line in
  the packet for **33/33** bugs, at zero tokens.
- The kernel's decisions are invariant under all 16 renumberings of the act
  vocabulary: **432/432** live decisions correct; a frozen lookup table
  scores 27/432 on the same test.
- With no model anywhere (mechanical observer), the same pipeline scores
  17/27 byte-exact — still zero tokens, still zero wrong repairs.

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

## What it will not do

Wrong variable passed, missing guard, wrong API call, misunderstood loop
intent: those are not single-token substitutions and no act dictionary reaches
them. The measured share of real one-line fixes that are single-token
substitutions is ~16% (see fluid-router's `benchmark/domain/`). fluidfix's
position: repair those mechanically for free, refuse the rest honestly, and
let a full model spend its 40k tokens only where the mask comes back empty.

## Licensing

AGPL-3.0-or-later. Section 13 (network use) applies. If AGPL does not suit
your use — proprietary products, SaaS without source offer — commercial
licenses are available: see [COMMERCIAL.md](COMMERCIAL.md).
