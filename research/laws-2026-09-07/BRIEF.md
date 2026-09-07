# Research brief: testing and researching the six authored laws of fluidfix

You are one of 50 agents. Each agent has ONE target from TARGETS.md. Do only your target.

## What fluidfix is, in three sentences
fluidfix repairs one-token/one-line defects with the target repo's own test suite as the oracle. Every DECISION comes from a machine-authored, branchless integer law: a byte of measured observations in, a ruling out. The body (loop.py, guard.py, acts.py, oracle.py, coracle.py) MEASURES the situation and ACTUATES the ruling; it is not supposed to decide anything itself.

## The six laws (read the module docstrings first — they are the specification)
- engine law    src/fluidfix/engine.py   decide(situation(**bits)) -> act name. BITS BUILT/AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED/SELF; ACTS SHIP/ADD_STATE/ADD_MATERIAL/RESHAPE/CHANGE_GRANULARITY/RAISE_BUDGET/HARVEST_COUNTEREXAMPLE/AUTHOR_SUCCESSOR. Actuation table in src/fluidfix/acts.py. Called from src/fluidfix/loop.py.
- ranking law   src/fluidfix/rank.py     rank(byte) -> priority of a candidate class; RETRIED is a veto. Tests: tests/test_rank_law.py
- SIGHT law     src/fluidfix/sight.py    which FILE to look at first, two tiers. Authored C: docs/laws/sight.c. Tests: tests/test_sight_law.py
- PAIR law      src/fluidfix/pair.py     whether to attempt more than one edit after a single-edit search fails. Authored C: docs/laws/pair.c. Prompt: docs/PAIR_LAW_PROMPT.md. Tests: tests/test_pair_law.py. Fused, NOT actuated yet.
- fluid-router  src/fluidfix/router.py   route(F1,A1,Fq). Tests: tests/test_router_law.py
- lanes         src/fluidfix/lanes.py    EMIT/ADVANCE/HALT. Tests: tests/test_lanes.py
Also: `.venv/bin/fluidfix selfcheck` re-derives all six exhaustively. tests/test_law_never_ruled_wrong.py audits every recorded incident (nine) against where the defect lived: observation, actuation, wording, or the ruling itself (zero so far).

## The standing principle you must apply
The law rules on the SITUATION it is given. Every wrong repair this project has ever recorded lived in the measurement of a bit, in the actuation of a ruling, or in the wording of a report — never in a ruling. If you find a wrong outcome, your job is to locate WHICH of those it is, with evidence. Do not propose "add an if-statement that decides". Do propose: which bit was mismeasured, which actuation was missing, or which lane the law already has that the body never consults.

## Truth rules (non-negotiable)
- No claim without the exact command or script that shows it, and an excerpt of its output, in your REPORT.md.
- Say "unmeasured" in those words for anything you did not measure. Never estimate a number and print it as if measured.
- A refusal is not a failure. Before calling any outcome wrong, state what the law ruled and on which observation byte.
- Neither overstate nor understate. If a lane is unreachable today, say so and say what observation would make it reachable.

## Hard limits (50 agents share one machine)
- Write ONLY inside your own directory: research/laws-2026-09-07/NN-slug/ (create it). Never edit src/, tests/, docs/, or any other agent's directory. Never run git commands that change state (no add/commit/checkout/stash/reset/clean). Read-only git is fine.
- Any build or suite run: prefix with `nice -n 15`, wrap with `timeout 300`, and run ONE at a time. Prefer exhaustive 256-input analysis and reading code. Real-repo runs only if your target says so. Repos: Box2D at /private/tmp/claude-501/-Users-kanchetidevieswar-neo/a9bf7d26-7aef-4c1e-a919-68bc40ac2e97/scratchpad/box2d and cglm at .../scratchpad/cglm — COPY a repo into your own directory before injecting defects (cp -R), never mutate the shared clone.
- Use /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python and .venv/bin/fluidfix. Do not pip install anything.
- If a fixture your target names does not exist, build a minimal one inside your directory and say so in the report.
- Stop after roughly 45 minutes of work. A partial report with measured findings beats a complete one with guesses.

## Deliverable: REPORT.md in your directory, exactly these sections
1. Target — one line.
2. Method — what you ran/read, with paths.
3. Findings — numbered. Each: the claim, the command/script, an output excerpt.
4. Lanes — for the law(s) you studied: which lanes/rulings your work reached, which it never reached, and why.
5. Potential — what an unexercised lane or unbuilt actuation would be worth, with a measured number where you have one and "unmeasured" where you do not.
6. Defects — any wrong outcome found, classified as observation / actuation / wording / ruling, with the evidence. "None found" is a valid entry.
7. Verdict — ONE line, precise, neither over- nor under-stated.
Keep scripts you wrote next to the report so a human can rerun them.

## Your final message to the coordinator (max 120 words)
The verdict line, your single most important finding with its number, and the path to your REPORT.md. Nothing else.
