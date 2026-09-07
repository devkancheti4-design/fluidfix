#!/bin/sh
# The same two headline cells through the PRODUCT surface (`fluidfix guard`,
# the commit-and-forget entry point), not just `fluidfix repair`.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
mkdir -p "$HERE/work" "$HERE/logs"
for f in A1-same-set-one-program B2-cross-set-two-programs; do
  echo "=============================== guard: $f"
  rm -rf "$HERE/work/guard-$f"
  cp -R "$HERE/fixtures/$f" "$HERE/work/guard-$f"
  cp "$HERE/work/guard-$f/mod.py" "$HERE/work/guard-$f/mod.py.pristine"
  "$HERE/run.sh" 300 "$FF" guard "$HERE/work/guard-$f" --python "$PY" \
      > "$HERE/logs/guard-$f.txt" 2>&1
  echo "exit=$?"
  cat "$HERE/logs/guard-$f.txt"
  echo "--- mod.py after the guard pass ---"
  diff -u "$HERE/work/guard-$f/mod.py.pristine" "$HERE/work/guard-$f/mod.py" \
      && echo "(file unchanged)"
done
