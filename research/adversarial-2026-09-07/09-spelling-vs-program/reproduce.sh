#!/bin/sh
# Reproduce the 09-spelling-vs-program matrix.  One fixture at a time, niced,
# each under a hard perl-alarm timeout.  Nothing outside this directory is touched.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
mkdir -p "$HERE/work" "$HERE/logs"

for f in A1-same-set-one-program A2-cross-set-one-program \
         B1-same-set-two-programs B2-cross-set-two-programs; do
  echo "=============================== $f"
  rm -rf "$HERE/work/$f"
  cp -R "$HERE/fixtures/$f" "$HERE/work/$f"
  cp "$HERE/work/$f/mod.py" "$HERE/work/$f/mod.py.pristine"
  "$HERE/run.sh" 300 "$FF" repair "$HERE/work/$f" --file mod.py \
      --python "$PY" --json > "$HERE/logs/$f.json" 2> "$HERE/logs/$f.err"
  echo "exit=$?"
  cat "$HERE/logs/$f.json"
  echo "--- mod.py after the run ---"
  diff -u "$HERE/work/$f/mod.py.pristine" "$HERE/work/$f/mod.py" \
      && echo "(file unchanged)"
done
