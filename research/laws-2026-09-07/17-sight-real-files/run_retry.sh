#!/bin/bash
# Second round, strictly after run_all.sh: alternates for green files, then
# re-measure early red records that predate per-file byte persistence.
D="$(cd "$(dirname "$0")" && pwd)"
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
until grep -q "ALL DONE" "$D/measure.log"; do sleep 2; done
$PY "$D/pick_alt.py" > "$D/pick_alt.out" 2>&1
for rel in $($PY -c "import json;print(' '.join(json.load(open('$D/alt_defects.json'))))"); do
  echo "=== retry $rel $(date +%H:%M:%S)" >> "$D/measure.log"
  nice -n 15 "$D/bin/timeout" 300 $PY "$D/measure.py" --retry "$rel" >> "$D/measure.stdout" 2>&1
  echo "=== slice rc=$? $(date +%H:%M:%S)" >> "$D/measure.log"
  (cd "$D/box2d" && git checkout -- src include >/dev/null 2>&1)
done
echo "=== fill $(date +%H:%M:%S)" >> "$D/measure.log"
nice -n 15 "$D/bin/timeout" 300 $PY "$D/measure.py" --fill >> "$D/measure.stdout" 2>&1
echo "=== slice rc=$? $(date +%H:%M:%S)" >> "$D/measure.log"
(cd "$D/box2d" && git checkout -- src include >/dev/null 2>&1)
echo "=== RETRY DONE $(date +%H:%M:%S)" >> "$D/measure.log"
