#!/bin/sh
# Reproduce every measurement in ATTACK.md. Sequential, nice -n 15, timeout-wrapped.
#   sh reproduce.sh            # all
#   sh reproduce.sh r5         # one case
set -e
D="$(cd "$(dirname "$0")" && pwd)"
R="$D/repos"
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
ONLY="${1:-all}"

t()  { S=$(python3 -c 'import time;print(time.time())'); "$@"; \
       E=$(python3 -c 'import time;print(time.time())'); \
       python3 -c "print('WALL_CLOCK_SECONDS = %.2f' % ($E-$S))"; }

want() { [ "$ONLY" = all ] || [ "$ONLY" = "$1" ]; }

# --- F1: estimate's band vs an actual in-vocabulary repair (r5 / r6) --------
if want r5; then
  echo "########## F1  r5_many: hard localisation, in-vocabulary defect ##########"
  rm -rf "$R/r5_shim"; cp -R "$R/r5_many" "$R/r5_shim"
  sed -i '' 's/^    return x + 17$/    return x - 17/' "$R/r5_shim/lib/mod17.py"
  echo "--- estimate on the GREEN repo ---"
  "$D/run.sh" 300 "$FF" estimate "$R/r5_many"
  echo "--- estimate on the SAME repo, RED (its 'realistic number') ---"
  "$D/run.sh" 300 "$FF" estimate "$R/r5_shim"
  echo "--- the actual guard run ---"
  FLUIDFIX_SHIM_LOG="$D/logs/repro_r5.log"; export FLUIDFIX_SHIM_LOG; : > "$FLUIDFIX_SHIM_LOG"
  t "$D/run.sh" 900 "$FF" guard "$R/r5_shim" --python "$D/pyshim.sh"
  echo "actual pytest suite runs : $(grep -c -- '-m pytest' "$FLUIDFIX_SHIM_LOG")"
  echo "  of which --cov runs    : $(grep -c -- '--cov' "$FLUIDFIX_SHIM_LOG")"
fi

# --- F2: estimate refuses a C repo cguard repairs --------------------------
if want r3; then
  echo "########## F2  r3_c: C/CMake project ##########"
  rm -rf "$R/r3_shim"; cp -R "$R/r3_c" "$R/r3_shim"; rm -rf "$R/r3_shim/build"
  sed -i '' 's/    return amount > limit;/    return amount >= limit;/' "$R/r3_shim/src/clamp.c"
  (cd "$R/r3_shim" && "$D/run.sh" 180 cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug >/dev/null \
                   && "$D/run.sh" 180 cmake --build build -j4 >/dev/null)
  echo "--- estimate (refuses) ---"
  "$D/run.sh" 300 "$FF" estimate "$R/r3_shim" || true
  echo "--- cguard on the identical tree (repairs) ---"
  t "$D/run.sh" 600 "$FF" cguard "$R/r3_shim"
fi

# --- F3: follow estimate's own advice, get a number for an unrepairable repo -
if want r7; then
  echo "########## F3  r7_smoke: estimate -> fluidfix init -> estimate ##########"
  rm -rf "$R/r7_shim"; cp -R "$R/r7_smoke" "$R/r7_shim"
  echo "--- estimate before init (refuses, tells you to run init) ---"
  "$D/run.sh" 300 "$FF" estimate "$R/r7_shim" || true
  "$D/run.sh" 300 "$FF" init "$R/r7_shim"
  echo "--- estimate after init (prints a number + a sales line) ---"
  "$D/run.sh" 300 "$FF" estimate "$R/r7_shim"
  echo "--- now inject an IN-VOCABULARY kind-0 defect and guard ---"
  sed -i '' 's/    if total > threshold:/    if total >= threshold:/' "$R/r7_shim/app/invoice.py"
  t "$D/run.sh" 600 "$FF" guard "$R/r7_shim"
fi

# --- controls: r1 (fast, in-vocab), r2 (slow), r4 (out of vocabulary) ------
for c in r1 r2 r4; do
  want $c || continue
  case $c in
    r1) SRC=r1_fast; SED='s/return amount > limit/return amount >= limit/'; F=pkg/billing.py;;
    r2) SRC=r2_slow; SED='s/return amount > limit/return amount >= limit/'; F=pkg/billing.py;;
    r4) SRC=r4_oov;  SED='s/        total += v \* w/        total += v/';   F=pkg/stats.py;;
  esac
  echo "########## control $c ($SRC) ##########"
  rm -rf "$R/${c}_shim"; cp -R "$R/$SRC" "$R/${c}_shim"
  sed -i '' "$SED" "$R/${c}_shim/$F"
  "$D/run.sh" 300 "$FF" estimate "$R/$SRC"
  FLUIDFIX_SHIM_LOG="$D/logs/repro_$c.log"; export FLUIDFIX_SHIM_LOG; : > "$FLUIDFIX_SHIM_LOG"
  t "$D/run.sh" 900 "$FF" guard "$R/${c}_shim" --python "$D/pyshim.sh" || true
  echo "actual pytest suite runs : $(grep -c -- '-m pytest' "$FLUIDFIX_SHIM_LOG")"
done
