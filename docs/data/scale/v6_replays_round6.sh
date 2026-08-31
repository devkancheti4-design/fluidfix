#!/bin/bash
# Round 6 — arrow alone, on a VERIFIED-clean environment (the orphaned probe
# process that was concurrently writing candidates into arrow/repo during
# rounds 4 and 5 is dead; file stability confirmed). Waits for round 5's
# click replays to finish first. This is the publishable arrow verdict.
C=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/34cbaa43-33b4-47bf-8eee-059bc310d9d7/scratchpad/complex
FX=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix

while kill -0 58809 2>/dev/null; do sleep 30; done

replay() {
  local name=$1 base=$2 rel=$3 lineno=$4 col=$5 tok=$6 newtok=$7 budget=$8
  local repo=$C/$name/repo py=$C/$name/venv/bin/python
  cd "$repo" || exit 1
  git reset -q --hard "$base" && git clean -fdq
  python3 - "$repo" "$rel" "$lineno" "$col" "$tok" "$newtok" << 'PYEOF'
import sys
repo, rel, lineno, col, tok, newtok = sys.argv[1:7]
lineno, col = int(lineno), int(col)
p = f"{repo}/{rel}"
src = open(p, encoding="utf-8", newline="").read()
lines = src.split("\n")
line = lines[lineno - 1]
assert line[col:col + len(tok)] == tok, \
    f"PRE-INJECTION MISMATCH {rel}:{lineno} col {col}: {line!r}"
lines[lineno - 1] = line[:col] + newtok + line[col + len(tok):]
open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
print(f"injected {rel}:{lineno}: {lines[lineno-1].strip()[:78]}")
PYEOF
  [ $? -ne 0 ] && { echo "INJECTION FAILED $name/$rel — aborting"; exit 1; }
  git commit -aqm "v6 replay6: $rel:$lineno $tok->$newtok"
  local T0=$(date +%s)
  "$FX" guard . --commit --python "$py" --escalate-budget "$budget"
  local rc=$?
  echo "REPLAY6[$name/$rel:$lineno budget=$budget] exit=$rc in $(($(date +%s)-T0))s"
  echo "  final line: $(sed -n "${lineno}p" "$rel")"
  echo "  baseline  : $(git show "$base:$rel" | sed -n "${lineno}p")"
  git reset -q --hard "$base" && git clean -fdq
  echo "============================================="
  return $rc
}

if ! replay arrow 2224255 arrow/locales.py 5468 13 '>' '>=' 600; then
  echo "arrow @600 refused — raising to 1800"
  replay arrow 2224255 arrow/locales.py 5468 13 '>' '>=' 1800
fi
echo V6_REPLAYS6_DONE
