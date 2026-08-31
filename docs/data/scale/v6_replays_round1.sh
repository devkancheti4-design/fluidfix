#!/bin/bash
# v6 replays — byte-faithful re-runs of the four v0.5 bench misses under the
# engine-law-fused guard. Each replay hard-resets to the recorded BASELINE SHA
# and injects at the exact (line, col, token) the seeded bench used; a
# pre-injection assertion aborts on any content drift.
C=/private/tmp/claude-501/-Users-kanchetidevieswar-neo/34cbaa43-33b4-47bf-8eee-059bc310d9d7/scratchpad/complex
FX=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix

replay() {
  local name=$1 base=$2 rel=$3 lineno=$4 col=$5 tok=$6 newtok=$7
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
  git commit -aqm "v6 replay: $rel:$lineno $tok->$newtok"
  local T0=$(date +%s)
  "$FX" guard . --commit --python "$py"
  local rc=$?
  echo "REPLAY[$name/$rel:$lineno] exit=$rc in $(($(date +%s)-T0))s"
  echo "  final line: $(sed -n "${lineno}p" "$rel")"
  echo "  baseline  : $(git show "$base:$rel" | sed -n "${lineno}p")"
  git reset -q --hard "$base" && git clean -fdq
  echo "============================================="
}

# sites verified against docs/data/scale logs (seeded attempts 8/7/3/4);
# gates first: arrow CAPPED, then termui AMB, then the two bonus replays
replay arrow 2224255 arrow/locales.py       5468  13 '>'   '>='   # v0.5: REFUSED 765s  (CAPPED gate)
replay click 36baa15 src/click/termui.py     744  23 '033' '034'  # v0.5: GREEN-ONLY    (AMB gate)
replay click 36baa15 src/click/_textwrap.py   18   9 '<='  '<'    # v0.5: REFUSED 209s  (bonus)
replay click 36baa15 src/click/utils.py       70  25 '1'   '2'    # v0.5: REFUSED 814s  (bonus)
echo V6_REPLAYS_DONE
