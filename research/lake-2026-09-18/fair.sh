#!/bin/bash
# The fair test, cold then warm. The net is never told which file. Cold wipes the memory; warm keeps what
# the cold run learned, so the pair measures what TEACHING plus MEMORY is worth on the same fault.
SP=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad
FF=/Users/kanchetidevieswar/neo/fluidfix
DICT=$FF/examples/taught-2026-09-19/corpus.py
for c in "$@"; do
  for mode in --cold ""; do
    tag=$([ -n "$mode" ] && echo COLD || echo WARM)
    line=$(PYTHONPATH=$FF/src python3 net.py "$SP/fairclones" "click/$c" \
        --template "$SP/tmpl_click" --dictionary "$DICT" --max-nodes 40 --width 6 $mode 2>&1 \
      | grep -E "^\[click")
    echo "$tag  $line"
  done
done
