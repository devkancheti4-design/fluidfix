#!/bin/zsh
# Rerun every attempt in ATTACK.md, one at a time, nice'd and time-boxed.
#   ./reproduce.sh            all
#   ./reproduce.sh f13 f14    just those
set -u
D=${0:A:h}
PY=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python
FF=/Users/kanchetidevieswar/neo/fluidfix/.venv/bin/fluidfix

rm -rf "$D/fixtures" "$D/pristine"
"$D/rt" 60 "$PY" "$D/make_fixtures.py" "$D/fixtures" >/dev/null
cp -R "$D/fixtures" "$D/pristine"

SEL_ALL=("$@")
sel() {
  [ ${#SEL_ALL[@]} -eq 0 ] && return 0
  for s in "${SEL_ALL[@]}"; do [[ "$1" == *"$s"* ]] && return 0; done
  return 1
}

for f in f01-plain f02-no-eol f03-crlf f04-bom f05-readonly f06-mode755 \
         f07-hardlink f08-symlink-in f10-future-mtime f11-mixed-eol f12-latin1; do
  sel "$f" || continue
  "$D/run_one.sh" "$f" "$D/fixtures/$f"
done
sel f09 && "$D/run_one.sh" f09-symlink-out "$D/fixtures/f09-symlink-out/repo"

# --- S2-a: repair written OUTSIDE the root through a symlink ---------------
if sel f13; then
  R="$D/fixtures/f13-symlink-out-tb"
  rm -rf "$R"; mkdir -p "$R/repo/pkg" "$R/repo/tests" "$R/outside"
  : > "$R/repo/pkg/__init__.py"
  printf '[tool.pytest.ini_options]\npythonpath = ["."]\n' > "$R/repo/pyproject.toml"
  cat > "$R/outside/geom.py" <<'EOF'
def second(xs):
    return xs[2]


def scale(v, k):
    return v * k
EOF
  ln -s ../../outside/geom.py "$R/repo/pkg/geom.py"
  cat > "$R/repo/tests/test_geom.py" <<'EOF'
import pkg.geom as g


def test_second():
    assert g.second([10, 20]) == 20


def test_scale():
    assert g.scale(2, 3) == 6
EOF
  cp "$R/outside/geom.py" "$R/outside-BEFORE.py"
  echo "=== S2-a: guard on $R/repo (root does NOT contain outside/) ==="
  "$D/rt" 240 "$FF" guard "$R/repo" --python "$PY"
  echo "--- diff of the file OUTSIDE the root: ---"
  diff "$R/outside-BEFORE.py" "$R/outside/geom.py" && echo "(unchanged)"
fi

# --- S2-b: CRLF line endings corrupted by a taught multi-line SpanEdit -----
if sel f14; then
  R="$D/fixtures/f14-crlf-span"
  rm -rf "$R"; mkdir -p "$R/pkg" "$R/tests"
  : > "$R/pkg/__init__.py"
  printf '[tool.pytest.ini_options]\npythonpath = ["."]\n' > "$R/pyproject.toml"
  "$PY" -c "open('$R/pkg/geom.py','wb').write(b'def add(a, b):\r\n    t = a - b\r\n    return -t\r\n\r\n\r\ndef scale(v, k):\r\n    return v * k\r\n')"
  cat > "$R/tests/test_geom.py" <<'EOF'
import pkg.geom as g


def test_add():
    assert g.add(2, 3) == 5


def test_scale():
    assert g.scale(2, 3) == 6
EOF
  "$PY" -c "print('BEFORE', repr(open('$R/pkg/geom.py','rb').read()))"
  "$D/rt" 240 "$FF" guard "$R" --python "$PY" --dictionary "$D/dict_span.py"
  "$PY" -c "print('AFTER ', repr(open('$R/pkg/geom.py','rb').read()))"
fi

# --- S4: stale_binary() ---------------------------------------------------
sel f15 && "$D/rt" 120 "$PY" "$D/probe_stale.py"
# --- the journal escapes the root too -------------------------------------
sel f16 && "$D/rt" 60 "$PY" "$D/probe_recover.py"
# --- the engine bytes -----------------------------------------------------
sel bytes && "$D/rt" 60 "$PY" "$D/probe_bytes.py"
