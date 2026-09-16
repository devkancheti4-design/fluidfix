#!/bin/bash
# Judge the Haiku-authored answers (file author, label haiku-4.5) after every other measurement job is done.
#   ./haiku_lane.sh <repos_ladder-dir> <repo>   -> appends to haiku_lane.log; a case awaiting tier 2 prints "awaiting author"
set -u; L=$1; R=$2; cd "$(dirname "$0")"; export PYTHONPATH=/Users/kanchetidevieswar/neo/fluidfix/src
until grep -q AFTER_CLEAN_DONE after_clean.log 2>/dev/null; do sleep 60; done
echo "== haiku-4.5 answers judged: $R =="; python3 ladder.py "$L" --backend file --label haiku-4.5 --stage run --classes andor,getdef,notdrop,rangestart,lenm1 --only "$R/"
echo "HAIKU_LANE_DONE $R"
