#!/bin/bash
# Does the net get cheaper as it FAILS? Seven faults in sequence, two arms.
#   A  net_reveal.py --cold        nothing persists between cases
#   B  net_learns.py --forget-shapes   only the refusal ledger persists; what success taught is dropped
SP=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad
FF=/Users/kanchetidevieswar/neo/fluidfix
DICT=$FF/examples/taught-2026-09-19/corpus.py
CASES="lenm1-1 andor-1 getdef-1 notdrop-1 cmp-1 lit-1 lit-1b"
rm -f net_memory.json
echo "### ARM A — nothing persists"
for c in $CASES; do
  PYTHONPATH=$FF/src python3 net_reveal.py "$SP/fairclones" "click/$c" --template "$SP/tmpl_click" \
      --dictionary "$DICT" --max-nodes 40 --width 6 --cold 2>&1 | grep -E "^\[click.*\|" \
    | sed "s/^/A  /"
done
rm -f net_memory.json
echo "### ARM B — only refusals persist"
for c in $CASES; do
  PYTHONPATH=$FF/src python3 net_learns.py "$SP/fairclones" "click/$c" --template "$SP/tmpl_click" \
      --dictionary "$DICT" --max-nodes 40 --width 6 --forget-shapes 2>&1 | grep -E "^\[click.*\||remembered for" \
    | sed "s/^/B  /"
done
