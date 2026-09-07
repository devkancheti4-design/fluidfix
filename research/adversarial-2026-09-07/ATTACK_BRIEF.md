# Adversarial brief: break fluidfix

You are a RED TEAM agent. Your job is not to describe fluidfix. It is to make it fail,
with a reproducible artifact a human can rerun.

## What counts as a successful attack, in descending severity

    S1  WRONG REPAIR SHIPPED   fluidfix writes a change to disk, reports "repaired",
                               and the program is now wrong (or differently wrong).
                               This is the only outcome that damages a user.
    S2  CORRUPTION             the repo is left in a state the user did not have:
                               a mutation not rolled back, a deleted line, a broken
                               build after a refusal, a test file edited.
    S3  FALSE CONFIDENCE       a claim in the report that the run does not support
                               (says byte-exact when it is not, says unique when it
                               is not, names the wrong line).
    S4  DENIAL                 a defect fluidfix should repair, that it refuses or
                               never terminates on, when the suite genuinely pins it.

A refusal WITH a correct reason is NOT a successful attack. It is fluidfix working.
Do not report it as a finding. Neither is slowness alone.

## The rule that makes your finding useful

For every successful attack you MUST classify where the defect lives:

    ruling       the law was given a correct observation byte and ruled wrongly
    observation  the body measured a bit wrongly, or never measured/delivered it
    actuation    the law ruled correctly and the body did something else
    wording      the outcome was right and the report described it wrongly

State the observation byte you believe was passed, the act the law returned, and
what the law WOULD have ruled on the correct byte. Use:
    from fluidfix.engine import decide, situation, BITS, ACTS
No incident in this project's history has ever been a `ruling`. If you believe you
have the first, that is a major finding and needs the byte printed, not asserted.

## Known attack surface (from the law-research wave, already measured)

    A. SIGHT is never consulted on the C and Java paths. guard.py:146-150 returns
       the file named by the traceback before the law is asked; coracle.py and
       javaoracle.py never import sight. So on C/C++/C# the file choice is code,
       not law.
    B. A CAPPED measured at guard.py:508 is never delivered into the byte
       loop.py:217 hands the engine law. A search cut short can therefore ship its
       single green as BUILT -> SHIP. Carried, the byte BUILT+CAPPED rules
       RAISE_BUDGET.
    C. The AMB proxy in loop.py `_rule` is `set_amb or len(sites) > 1`. It measures
       WHERE greens came from, not WHETHER THEY ARE THE SAME PROGRAM. Two different
       programs reached by two acts at ONE site are shipped as one; one program
       spelled twice inside one set is refused as two.
These are starting points, not your whole job. An attack that only re-demonstrates
one of them is worth less than a new one.

## Hard rules

- Write ONLY inside your own directory: research/adversarial-2026-09-07/NN-slug/.
  Never edit src/, tests/, docs/, the law-research directories, or another agent's
  directory. Never run git commands that change state. Read-only git is fine.
- Build your victim repos INSIDE your directory. Copy, never mutate, any shared
  clone (Box2D and cglm live in the session scratchpad; `cp -R` first).
- Every build or suite run: `nice -n 15`, wrapped in a timeout, ONE at a time.
- Use /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python and .venv/bin/fluidfix.
  Do not pip install.
- You may NOT weaken fluidfix to make an attack land. No editing its source, no
  monkeypatching its laws, no FLUIDFIX_* env var that disables a defence unless
  your target explicitly says to measure that env var's effect — and then you must
  report the default behaviour too.
- Stop after roughly 45 minutes. A reproduced S1 beats a long list of theories.

## Deliverable: ATTACK.md in your directory

1. Target — one line.
2. Attack design — what property of fluidfix you are attacking and why it should work.
3. Attempts — numbered, INCLUDING the ones that failed. A defence that held is a
   result: say what stopped you and quote the refusal reason.
4. Outcome — for each success: severity (S1-S4), the exact reproduction command,
   the diff fluidfix wrote, and the classification (ruling/observation/actuation/wording)
   with the observation byte and the law's act.
5. What defended — the specific mechanism that blocked your other attempts.
6. Verdict — ONE line: did fluidfix hold, and where exactly did it not.

Keep every fixture and script so a human can rerun it. If you found nothing, say
"no successful attack" plainly and list what you tried — a failed attack against a
real defence is evidence FOR the tool and is wanted.

## Your final message to the coordinator (max 120 words)
Verdict line, highest severity achieved with its classification, path to ATTACK.md.
