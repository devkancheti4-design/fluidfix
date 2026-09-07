#!/bin/sh
# Agent 38 — run the guard on every Python fixture under tests/, logging every
# law consultation. One test file at a time, nice -n 15 + perl-alarm timeout.
# Usage: run_all.sh <file...>
D=/Users/kanchetidevieswar/neo/fluidfix/research/laws-2026-09-07/38-python-lane-log
R=/Users/kanchetidevieswar/neo/fluidfix
cd "$R" || exit 1
mkdir -p "$D/logs"
for f in "$@"; do
  b=$(basename "$f" .py)
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$D" LANELOG="$D/logs/$b.jsonl" \
    "$D/tmo.sh" 300 "$R/.venv/bin/python" -m pytest "tests/$b.py" \
      -q --no-header -p no:cacheprovider -p lanelog_plugin \
      > "$D/logs/$b.out" 2>&1
  echo "$b rc=$? $(tail -1 "$D/logs/$b.out")"
done
