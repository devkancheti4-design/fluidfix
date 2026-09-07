#!/bin/zsh
# run_one.sh <fixture-name> <repo-root> [extra fluidfix args...]
# Records the defect file's exact byte state BEFORE and AFTER one guard pass.
set -u
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/13-stale-and-symlink
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
NAME=$1; ROOT=$2; shift 2

state() {   # sha of CONTENT, plus mode/inode/links/symlink of the NAME
  local p=$1
  if [ -e "$p" ]; then
    printf '  content-sha256: %s\n' "$(shasum -a 256 "$p" | cut -d' ' -f1)"
    printf '  stat(name):     %s\n' "$(stat -f 'mode=%Sp inode=%i nlink=%l size=%z' "$p" 2>/dev/null)"
    printf '  lstat(name):    %s\n' "$(stat -f 'mode=%Sp type=%HT' -L /dev/null >/dev/null 2>&1; /usr/bin/stat -f 'mode=%Sp inode=%i' "$p")"
    if [ -L "$p" ]; then printf '  symlink -> %s\n' "$(readlink "$p")"; fi
  else
    printf '  MISSING\n'
  fi
}

LOG=$D/logs/$NAME.log
{
echo "=== fixture: $NAME"
echo "=== root:    $ROOT"
echo "=== extra:   $*"
for f in $(cd "$ROOT" && find . -name '*.py' -o -name '*.c' | sort); do
  echo "BEFORE $f"; state "$ROOT/$f"
done
echo "=== guard run ==="
} > "$LOG" 2>&1

"$D/rt" 240 "$FF" guard "$ROOT" --python "$PY" "$@" >> "$LOG" 2>&1
RC=$?
{
echo "=== guard exit: $RC ==="
for f in $(cd "$ROOT" && find . -name '*.py' -o -name '*.c' | sort); do
  echo "AFTER $f"; state "$ROOT/$f"
done
echo "=== leftovers in .fluidfix ==="
ls -la "$ROOT/.fluidfix" 2>/dev/null || echo "(none)"
} >> "$LOG" 2>&1
echo "$NAME rc=$RC  -> $LOG"
