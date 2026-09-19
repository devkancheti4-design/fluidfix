# How big are real bug fixes? — 552 commits, no size cap

Every earlier figure here was drawn from fixes that **ship a regression test**, and those are systematically
larger (24% one-line, against 45% for fixes without one). That biased my own framing pessimistic: I had been
saying "only 11 of 57 judged fixes were one-line", which is 19%, and treating it as the addressable surface.

This is the whole population — every commit whose subject says it fixes something and which touches exactly
one non-test source file, across click, arrow, rich and sortedcontainers, **with no cap on diff size**.

| lines changed | n | share | cumulative |
|---|---|---|---|
| **1** | 204 | **37%** | 37% |
| 2 | 79 | 14% | 51% |
| 3–5 | 101 | 18% | 70% |
| 6–10 | 65 | 12% | 81% |
| 11–20 | 51 | 9% | 91% |
| 21–40 | 34 | 6% | 97% |
| over 40 | 18 | 3% | 100% |

## What the boundaries mean

**37% of real fixes replace exactly one line.** That is the surface a line-replacement vocabulary can
address — not 19%. My earlier number was an artefact of the tested-fix subset.

**91% are under twenty lines.** True, and higher than expected — but twenty lines is not the boundary that
matters. A five-line fix is well under twenty and still outside a vocabulary that replaces one line.

**The step that matters is one line to five: 37% → 70%.** Nearly double the surface, for a vocabulary that
could express a small contiguous edit rather than a single replacement. That is a concrete direction, and
the largest single gain available on this evidence — larger than harvesting values (3/11 → 5/11) and larger
than any number of extra dictionary slots.

## What is not claimed

- Four mature open-source libraries. A team's application code has a different distribution, and this
  question is exactly what a week of their CI in report-only mode answers.
- The filter is a subject line matching fix/bug/regression and one non-test source file. Fixes that say
  nothing, and fixes spread over several files, are absent — and multi-file fixes are certainly larger, so
  the true one-line share across *all* fixes is lower than 37%.
- Size is `max(added, removed)` from `--numstat`, so a pure insertion of three lines counts as three.
- **Reachable is not repaired.** 37% is what a one-line vocabulary could *express*; what it has been taught
  covers far less, and the suite still decides every candidate.
