#!/bin/sh
# Reproduce every result in ATTACK.md. ~40s total. One build/suite run at a time.
# Usage: sh reproduce.sh
set -e
D=$(cd "$(dirname "$0")" && pwd)
V=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin
T="$D/tmo"          # this host has no coreutils `timeout`; tmo kills the group

run() {                       # run <name> <srcdir> <extra fluidfix args...>
    name=$1; src=$2; shift 2
    rm -rf "$D/$name"; cp -R "$D/fixture/$src" "$D/$name"
    echo "=== $name: pristine suite ==="
    ( cd "$D/$name" && nice -n 15 "$T" 120 ./build.sh && nice -n 15 "$T" 60 ./build/tests ) || true
    echo "=== $name: fluidfix cguard ==="
    nice -n 15 "$T" 900 "$V/fluidfix" cguard "$D/$name" \
        --build-cmd ./build.sh --test-cmd ./build/tests --budget 600 "$@" || true
    echo "=== $name: what fluidfix wrote ==="
    diff -ru "$D/fixture/$src" "$D/$name" || true
    echo "=== $name: suite after the 'repair' ==="
    ( cd "$D/$name" && nice -n 15 "$T" 120 ./build.sh && nice -n 15 "$T" 60 ./build/tests ) \
        && echo "  exit 0 -- fluidfix calls this repaired" || echo "  exit non-zero"
    echo
}

# A1  harness in unittest/ (dir filter misses it) -> loop disabled, S1
run runA pristine
# A2  control: identical fixture, harness in test/ (dir filter catches it)
rm -rf "$D/runB"; cp -R "$D/fixture/pristine" "$D/runB"
mv "$D/runB/unittest" "$D/runB/test"
sed -i '' 's|unittest/main.c|test/main.c|g' "$D/runB/test/main.c" "$D/runB/build.sh"
echo "=== runB (control, harness in test/): fluidfix cguard ==="
nice -n 15 "$T" 900 "$V/fluidfix" cguard "$D/runB" --build-cmd ./build.sh \
    --test-cmd ./build/tests --budget 600 || true
diff -u "$D/fixture/pristine/src/geom.c" "$D/runB/src/geom.c" || true
echo
# A3  root-level check.c, TAP output -> counter neutered, S1
run runC pristine-tap --suite-timeout 30

# Independent proof the library is still wrong after runA's "repair"
echo "=== runA: is the library actually fixed? ==="
nice -n 15 "$T" 60 cc -O0 -o "$D/runA/prove" "$D/runA/src/geom.c" "$D/fixture/prove.c"
"$D/runA/prove"
