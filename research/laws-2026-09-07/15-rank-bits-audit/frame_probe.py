#!/usr/bin/env python
"""Show the EXACT text the body hands the ranking law (Oracle.failing_output,
which runs pytest -x --tb=long) and which FRAME / NAMED sources it carries.

Builds a 2-file fixture inside this directory, runs its 1-test suite once
through the body's own Oracle, then applies the body's own regexes from
guard.rank_observations to the output.

  nice -n 15 perl -e 'alarm 300; exec @ARGV' \
      /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python frame_probe.py
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap

sys.dont_write_bytecode = True
from fluidfix.guard import _ANSI, _name_tokens  # noqa: E402
from fluidfix.oracle import Oracle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "frame_fixture")
shutil.rmtree(FIX, ignore_errors=True)
os.makedirs(FIX)
open(os.path.join(FIX, "mod.py"), "w").write(textwrap.dedent("""\
    def ordinal_number(n):
        if n >= 10:          # defect: should be n > 10
            return "th"
        return "st"
"""))
open(os.path.join(FIX, "test_mod.py"), "w").write(textwrap.dedent("""\
    from mod import ordinal_number
    def test_ordinal_number():
        assert ordinal_number(10) == "st"
"""))

oracle = Oracle(FIX, python=sys.executable)
fails, out = oracle.failing_output()
clean = _ANSI.sub("", out)
print("== suite fails:", fails)
print("== failing_output (verbatim) ==")
print(clean)
print("== end ==")

# the body's FRAME regex, verbatim from guard.rank_observations
framed = {}
for m in re.finditer(r"([\w./\\-]+\.py)[\":,]+\s*(?:line\s+)?(\d+)", clean):
    framed.setdefault(os.path.basename(m.group(1)), set()).add(int(m.group(2)))
print("FRAME candidates by basename:", framed)
print("FRAME for rel='mod.py':", framed.get("mod.py", set()))

# the body's NAMED token source, verbatim
toks = set()
for m in re.finditer(r"^(?:FAILED|ERROR)\s+\S*?::(\S+)", clean, re.M):
    for part in m.group(1).split("::"):
        toks |= _name_tokens(part.split("[")[0])
print("NAMED tokens from FAILED/ERROR lines:", sorted(toks))
print("def-name tokens for 'ordinal_number':", sorted(_name_tokens("ordinal_number")))
shutil.rmtree(os.path.join(FIX, ".pytest_cache"), ignore_errors=True)
