#!/bin/bash
# Drive measure.py over defects.json in slices of 3, each slice under
# nice -n 15 and bin/timeout 300, strictly one at a time.
D="$(cd "$(dirname "$0")" && pwd)"
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
i=0
while :; do
  n=$($PY -c "import json;print(len(json.load(open('$D/defects.json'))))")
  [ "$i" -ge "$n" ] && break
  j=$((i+3))
  echo "=== slice $i..$j  $(date +%H:%M:%S)" >> "$D/measure.log"
  nice -n 15 "$D/bin/timeout" 300 $PY "$D/measure.py" $i $j >> "$D/measure.stdout" 2>&1
  echo "=== slice rc=$? $(date +%H:%M:%S)" >> "$D/measure.log"
  # restore any file a killed slice left mutated
  (cd "$D/box2d" && git checkout -- src include >/dev/null 2>&1)
  i=$j
done
echo "=== ALL DONE $(date +%H:%M:%S)" >> "$D/measure.log"
