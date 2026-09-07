#!/bin/sh
# Direct demonstration: the SAME source edit, judged twice — once built in the
# same wall-clock second as the previous object file, once a second later.
D=/Users/kanchetidevieswar/neo/fluidfix/research/adversarial-2026-09-07/06-compensating-two-site
for mode in same-second one-second-later; do
  R="$D/run/ST-$mode"; rm -rf "$R"; cp -R "$D/fixture/billing-C" "$R"; cd "$R"
  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1
  cmake --build build -j4 >/dev/null 2>&1
  [ "$mode" = one-second-later ] && perl -e 'select undef,undef,undef,1.2'
  sed -i '' 's/units \* 8/units * 7/' src/fee.c
  cmake --build build -j4 >/dev/null 2>&1
  echo "$mode: source says '$(grep -o 'units \* .' src/fee.c)' -> suite says: $(./build/tests | tail -1)"
  cd "$D"; rm -rf "$R"
done
