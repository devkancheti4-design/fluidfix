# What fluidfix is worth, and what it should cost

Every number here is traceable to a measurement in this repository. Where a
number would need a customer's own data, it says so instead of guessing. Run
`./docs/verify.sh` to reproduce the capability claims on your own machine.

---

## 1. What is actually being sold

A guard that repairs a **narrow, recurring class of defect** — single-token
faults: a flipped comparison, an off-by-one index, a swapped operand, a wrong
literal — using **your own test suite as the only judge**, with **no model in
the loop and therefore no tokens, ever**.

Every decision it makes comes from six machine-authored integer kernels, each
re-derived exhaustively over its entire input space on every run
(`fluidfix selfcheck`). Across 63 recorded incidents — 33 historical, 30 found
by a 20-agent adversarial review on 2026-09-07 — **not one defect has ever
lived in a ruling**. That claim is mechanically checked: 29 of 29
byte-to-ruling pairs re-derive from the shipped law.

That is the product. It is not an autonomous engineer and it is not sold as one.

## 2. What is measured, and what is not

**Measured, reproducible from files in this repo:**

| claim | number | source |
|---|---|---|
| byte-exact repairs, 33-bug benchmark | 26 of 27 accepted | `docs/data/arm_a_full_results.json` |
| out-of-vocabulary faults refused, not guessed | 6 of 6 | same |
| localisation correct | 33 of 33 | same |
| across three real Python repos | 14 of 18 (78%) | `docs/data/*-after.log` |
| tokens per repair | 0 | no model is invoked |
| the six laws re-derive | 4096/4096 router, 256/256 each of five | `fluidfix selfcheck` |
| ambiguity now measured, not inferred | 12/12 separated, 6 wrong repairs → 0 | `research/laws-2026-09-07/41-*` |

**Not measured, and priced accordingly:**

- **Your recurrence rate.** How often *your* code produces this defect class is
  the single biggest driver of value and nobody knows it, including us. On two
  public C libraries we measured roughly **1.5 qualifying fixes per year**
  (Box2D, 17 years of history) — low. A live-service title patching weekly is
  plausibly far higher. **Plausibly is not measured.**
- **Compiled languages are weaker and we will not price them as if they are
  not.** On cglm's six real historical one-token fixes, end to end: **0 of 6
  repaired** — three defects the suite cannot see at all, one site no longer
  exists, and two refused because the C file-finder never nominated the defect
  file. The taught class itself was correct for 4 of the 6.
- **Uniqueness is not proven on C, C++, Java or C#.** The differential check
  that proves two candidates are the same program parses Python. On other
  languages a repair says so in its own reason.
- **Weak suites.** On deliberately loose suites, 15.4% of accepted repairs were
  a different program. The 0.15.0 ambiguity fix addresses this on Python; the
  rate has not been re-measured post-fix on a corpus.

## 3. The honest value calculation

For one qualifying defect, an engineer spends roughly **30–60 minutes**: read
the CI failure, find the line, fix, open a PR, wait. At a loaded senior rate of
**$100–150/hour** that is **$50–150 per defect**.

    annual value  =  your qualifying defects per year  x  $50-150
                     x  the fraction your suite actually catches

At a library's measured 1.5/year that is **$75–225 a year** — which does not
justify a licence, and we will say so rather than sell you one. At 50/year, the
rate a busy live-service codebase could plausibly hit, it is **$2,500–7,500**.
At 200/year it is **$10,000–30,000**.

**The multiplier nobody prices correctly is that a class is taught once.** A
class registered from a single worked example was measured emitting the
historically correct repair for **four separate cglm fixes spanning 2016 to
2023 across four different files**. Teaching is one-time; the guard is forever;
the marginal cost of the next instance is zero tokens and a few suite runs.

## 4. The price

**Free — AGPL-3.0, unlimited, self-hosted.**
Everything. All six laws, all language paths, no feature gate. The kernels are
the contribution and they stay public and verifiable. If your project is open
source, this is the whole product and it costs nothing.

**Measurement pilot — $5,000, six weeks, credited in full against a licence.**
This is the honest first step and the one we recommend. We run fluidfix against
**your** history and your suite and produce the number that does not exist yet:
how many of your regressions are in this class, how many your tests actually
catch, and what it would have saved. If the answer is small, you have a cheap
answer and we say so.

**Commercial licence — $12,000 / year.**
Removes the AGPL obligation for closed-source use. Up to 10 repositories, one
language path, CI integration, the hotspots report. Priced at roughly the value
of **100–200 qualifying defects a year** — i.e. it pays for itself on a
codebase producing about two a week, and does not on a quiet library.

**Studio — $40,000 / year.**
Unlimited repositories, all language paths, and the part that actually
generalises: **we author the fault classes for your codebase** from your own
worked examples, and maintain them. Includes the C/C++ localisation work the
audit identified, done against your repo rather than in the abstract.

**What we will not sell:** a per-seat subscription. It runs on your machine,
consumes no tokens, and costs us nothing per repair. Charging per developer
would be charging for nothing.

## 5. The ceiling, stated plainly

If your regressions are single-token faults and your suite catches them, this
guards that class **forever, at zero marginal cost, with a refusal instead of a
guess when it is unsure**. That is the full potential and it is real.

The bound is your suite. fluidfix cannot be right about code your tests are
wrong about, and on cglm three of six real defects were invisible to the
library's own tests. A tool judged by your suite inherits your suite's blind
spots exactly.

We would rather sell you the pilot and lose the licence than sell you a licence
against a number neither of us has measured.
