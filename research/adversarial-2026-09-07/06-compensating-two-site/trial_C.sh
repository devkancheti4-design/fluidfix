#!/bin/sh
# 10 sequential trials of the pinned-suite control. Same fixture, same
# command each time. Prints the verdict of each.
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/06-compensating-two-site
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix
N=${1:-10}
i=1
while [ $i -le $N ]; do
  R="$D/run/T$i"
  rm -rf "$R"; cp -R "$D/fixture/billing-C" "$R"
  cd "$R"
  "$D/ffto" 120 cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1
  "$D/ffto" 120 cmake --build build -j4 >/dev/null 2>&1
  OUT=$("$D/ffto" 600 "$FF" cguard . --test-cmd ./build/tests --budget 300 2>&1)
  V=$(echo "$OUT" | grep -E 'repaired|REFUSED' | head -1 | cut -c1-110)
  echo "trial $i: $V"
  rm -rf "$R/build" "$R/covbuild"
  i=$((i+1))
done
