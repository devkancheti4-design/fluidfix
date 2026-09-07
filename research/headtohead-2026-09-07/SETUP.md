# Token head-to-head, re-run with artifacts preserved

WHY THIS EXISTS. The claim "795 tokens over 3 suite runs vs 0 tokens over 126"
appears in CHANGELOG 0.14.0 and carries the whole head-to-head panel on the games
page. The truth audit (agent 50) found NO ARTIFACT for it anywhere on this
machine: grep for "795" outside .git/.venv/research returns one hit, the claim
itself, and the trial repo's .fluidfix/ directory is empty. Independently
confirmed by the coordinator. The number may well be right, but it is
UNREPRODUCIBLE, which under this project's own truth rules means it cannot stand.

This directory re-runs it so that every number has a file behind it.

DESIGN
  arm A  fluidfix, unattended. Tokens are zero BY CONSTRUCTION — no model is in
         the loop — so the measurement that matters is SUITE RUNS and WALL CLOCK,
         and the artifact is the preserved .fluidfix/ directory plus the guard's
         own stdout.
  arm B  an LLM agent given the same repo and the same failing suite, with NO
         access to fluidfix, asked to find and fix the defect. Its token usage is
         reported by the harness when it finishes, and that number is the artifact.

RULES
  - Both arms get the SAME repo at the SAME commit with the SAME injected defect.
  - Arm B must not be told where the defect is.
  - Preserve everything: .fluidfix/, stdout, the diff, and the agent's token count.
  - If the two arms are not comparable, SAY SO rather than printing a ratio.
