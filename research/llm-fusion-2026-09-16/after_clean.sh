#!/bin/bash
# Runs after the clean chain: fix 4, fluidfix's own suite alone, then the ladder lane (resumes; finished cases skip), then the gemma redo.
set -u; L=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until grep -q CLEAN_CHAIN_DONE clean_chain.log 2>/dev/null; do sleep 60; done
echo "== fix 4 =="; python3 /private/tmp/claude-501/-Users-kanchetidevieswar-neo/a46159fc-099c-469d-86e6-efc9597842bd/scratchpad/fixes/apply_fix4_packet_sampler.py
echo "== fluidfix own suite, alone =="; (cd /Users/kanchetidevieswar/neo/fluidfix && /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest -q -p no:cacheprovider 2>&1 | tail -3; PYTHONPATH=src /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m fluidfix.cli selfcheck 2>&1 | tail -1)
echo "== ladder lane resumes =="; ./ladder_lane.sh "$L" >> ladder_lane.log 2>&1
echo "== gemma click/lenm1-1 redo =="; python3 ladder.py "$L" --backend ollama --model gemma3:4b --classes lenm1 --only click/lenm1-1
python3 report.py; echo AFTER_CLEAN_DONE
