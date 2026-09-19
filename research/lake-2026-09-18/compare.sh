#!/bin/bash
# The same corpus, cold, never told the file, under two territory orderings:
#   net.py         most-executed lines first
#   net_reveal.py  what the failing test run already says first
SP=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad
FF=/Users/kanchetidevieswar/neo/fluidfix
DICT=$FF/examples/taught-2026-09-19/corpus.py
for c in "$@"; do
  for prog in net.py net_reveal.py; do
    out=$(PYTHONPATH=$FF/src python3 $prog "$SP/fairclones" "click/$c" --template "$SP/tmpl_click" \
          --dictionary "$DICT" --max-nodes 40 --width 6 --cold 2>&1)
    echo "$(printf '%-14s %-14s' "$c" "$prog") $(echo "$out" | grep -E '^\[click.*\|' | sed 's/.*\] //')"
  done
done
