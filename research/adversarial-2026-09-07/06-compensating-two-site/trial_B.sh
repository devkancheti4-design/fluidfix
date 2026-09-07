#!/bin/sh
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/06-compensating-two-site
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
FIX=${2:-billing-B}
N=${1:-5}; i=1
while [ $i -le $N ]; do
  R="$D/run/B$i"; rm -rf "$R"; cp -R "$D/fixture/$FIX" "$R"; cd "$R"
  "$D/ffto" 120 cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1
  "$D/ffto" 120 cmake --build build -j4 >/dev/null 2>&1
  OUT=$("$D/ffto" 600 "$FF" cguard . --test-cmd ./build/tests --budget 300 2>&1)
  echo "trial $i: $(echo "$OUT" | grep -E 'repaired|REFUSED|AMBIG' | head -1 | cut -c1-200)"
  rm -rf "$R/build" "$R/covbuild"
  i=$((i+1))
done
