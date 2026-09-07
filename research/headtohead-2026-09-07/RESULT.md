# Head-to-head, measured 2026-09-07, both arms preserved

One repo, one single-token defect (`spend >= 250` -> `spend > 250` in
pkg/ledger.py:13). Two byte-identical copies. Neither arm told where it was.

| | fluidfix (armA) | an LLM agent, unaided (armB) |
|---|---|---|
| tokens | **0** | **43,006** |
| suite runs | 13 | 2 |
| wall clock | 6.3 s | 73.8 s |
| result | correct, byte-exact | correct |

Reproduce: `armA.log` is fluidfix's own output. armB was repaired by a general
agent with no access to fluidfix; its token count is the harness's own figure.

## This CORRECTS a published claim
The site and CHANGELOG said "795 tokens over 3 suite runs". A truth audit found
that number had **no artifact anywhere on the machine** — one grep hit, the
claim itself. Re-measured here it is **43,006**, about fifty times larger.

## What it honestly shows
The agent was NOT worse at this task. It reasoned to the line in 2 suite runs
where fluidfix searched in 13. It cost 43k tokens and ~12x the wall clock.

So the argument for the laws is NOT cost-per-defect: at 43k tokens, 200 defects
a year is under $100. The arguments that survive measurement are:
  * determinism — same input, same ruling, every time;
  * it REFUSES rather than producing something when it cannot prove the answer;
  * zero marginal cost, so it can run unattended on every push forever;
  * nothing leaves the machine.

The trade-off, equally real: an agent handles ANY defect. fluidfix handles only
classes it has been taught.
