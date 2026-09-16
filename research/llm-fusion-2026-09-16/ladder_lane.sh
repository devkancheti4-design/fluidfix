#!/bin/bash
# The ladder lane: one job at a time, after my click file-author run. Packet v3 (full sight) for everything below.
set -u; L=$1; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src; OOV=andor,getdef,notdrop,rangestart,lenm1
until grep -q LADDER_DONE ladder_click_fable.log 2>/dev/null; do sleep 15; done
echo "== click/notdrop-1 redo with packet v3 (the v2 packet lacked the defect line) =="
for m in qwen3.5:4b phi4-mini gemma3:4b; do python3 ladder.py "$L" --backend ollama --model "$m" --classes notdrop --only click/notdrop-1; done
./ladder_chain.sh "$L" arrow
./ladder_chain.sh "$L" python-sortedcontainers
echo "== waiting for the clean chain (rich refusals must be post-fix) =="
until grep -q CLEAN_CHAIN_DONE clean_chain.log 2>/dev/null; do sleep 60; done
python3 - <<'PY'
import json, shutil
from pathlib import Path
for d in sorted(Path("cases/rich").glob("*/")):
    t0, rr = d / "refusal_tier0.json", d / "refusal_rerun300.json"
    if t0.exists() and rr.exists() and any(".venv" in c for c in json.load(open(t0)).get("candidates", [])):
        shutil.move(t0, d / "refusal_tier0_prefix1.json"); shutil.copy(rr, t0); print("rich", d.name, ": tier-0 refusal replaced by the post-fix replay's (pre-fix one kept as refusal_tier0_prefix1.json)")
PY
./ladder_chain.sh "$L" rich
echo LADDER_LANE_DONE
