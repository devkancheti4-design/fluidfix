#!/bin/bash
# Replay one repo's refused out-of-vocabulary cases through the ladder with each local author,
# then collect my (file-author) packets. Runs on the ladder copies, one job at a time.
#   ./ladder_chain.sh <repos_ladder-dir> <repo>            -> ladder_<repo>.log
set -u; L=$1; R=$2; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
OOV=andor,getdef,notdrop,rangestart,lenm1
for m in qwen3.5:4b phi4-mini gemma3:4b; do echo "== ladder $R OOV: $m =="; python3 ladder.py "$L" --backend ollama --model "$m" --classes $OOV --only "$R/"; done
echo "== ladder $R OOV: file author collect (fable-5.1) =="; python3 ladder.py "$L" --backend file --label fable-5.1 --stage collect --classes $OOV --only "$R/"
echo "CHAIN_DONE $R"
