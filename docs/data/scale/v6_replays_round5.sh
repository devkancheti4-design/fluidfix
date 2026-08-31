#!/bin/bash
# Round 5 — release-gate sweep on frozen code: depth-first scheduler +
# line-affinity ranking + all five adversarial-review fixes (AMB-proof
# atomicity, filter-drop=CAPPED, full-sight skip, half-budget per file,
# no observer calls past deadline). All four v0.5 miss sites, byte-faithful,
# default 600s budget; 1800s fallback only where 600 refuses.
C=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/34cbaa43-33b4-47bf-8eee-059bc310d9d7/scratchpad/complex
FX=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix

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
  git commit -aqm "v6 replay5: $rel:$lineno $tok->$newtok"
  local T0=$(date +%s)
  "$FX" guard . --commit --python "$py" --escalate-budget "$budget"
  local rc=$?
  echo "REPLAY5[$name/$rel:$lineno budget=$budget] exit=$rc in $(($(date +%s)-T0))s"
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
replay click 36baa15 src/click/termui.py 744 23 '033' '034' 600
replay click 36baa15 src/click/_textwrap.py 18 9 '<=' '<' 600
if ! replay click 36baa15 src/click/utils.py 70 25 '1' '2' 600; then
  echo "utils @600 refused — raising to 1800"
  replay click 36baa15 src/click/utils.py 70 25 '1' '2' 1800
fi
echo V6_REPLAYS5_DONE
