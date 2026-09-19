#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Record the survey each incident produces, so ordering policies can be certified WITHOUT running them.

Choosing how the net orders its territories is a policy, and I had started guessing at one — deprioritise
territories that were refuted before — and then spending an hour of suite runs per guess. That is the wrong
shape of work. The policy is code with a spec, and the recorded incidents can decide between candidates
offline, in milliseconds, before anything runs live.

This captures the input a policy sees: for each incident, the territories the failing test executed, their
executed-line counts, the classes each can exhibit, what the failure output names — and the answer.
"""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recursive import SURVEY, CASES, SRC, sh, apply_mutation           # noqa: E402

SP = Path("/private/tmp/claude-501/-Users-kanchetidevieswar-neo/"
          "7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad")
TMPL = SP / "tmpl_click"
DICT = HERE.parents[1] / "examples" / "taught-2026-09-19" / "corpus.py"
CLS = {"andor": 4, "getdef": 5, "notdrop": 6, "lenm1": 7,
       "lit": 1, "cmp": 10, "add": 3, "rangestart": 1}

env = dict(os.environ); env["PYTHONPATH"] = str(SRC)
out = []
for cid in ["lenm1-1", "andor-1", "getdef-1", "notdrop-1", "cmp-1", "lit-1", "lit-1b"]:
    mut = json.load(open(CASES / "click" / cid / "mutation.json"))
    apply_mutation(TMPL, mut, commit=False)
    r = sh([str(TMPL / ".venv" / "bin" / "python"), "-c", SURVEY, str(SRC), str(DICT)],
           cwd=TMPL, env=env, timeout=900)
    survey = json.loads(r.stdout.strip().splitlines()[-1])
    f = sh([str(TMPL / ".venv" / "bin" / "python"), "-c",
            f"import sys; sys.path.insert(0, {str(SRC)!r})\n"
            "from fluidfix import Oracle\n"
            "print(Oracle('.', python=sys.executable).failing_output()[1])"],
           cwd=TMPL, env=env, timeout=900)
    sh(["git", "reset", "-q", "--hard", mut["base"]], cwd=TMPL)
    rec = {"case": cid, "answer_file": mut["file"], "answer_class": CLS[cid.split("-")[0]],
           "failing_output": (f.stdout or "")[-3000:],
           "files": {rel: {"executed": i["executed"], "kinds": [int(k) for k in i["kinds"]]}
                     for rel, i in survey["files"].items()}}
    out.append(rec)
    print(f"{cid:12} {len(rec['files']):>3} territories  answer {mut['file']} class {rec['answer_class']}",
          flush=True)

(HERE / "surveys_click.json").write_text(json.dumps(out, indent=1))
print("recorded -> surveys_click.json")
