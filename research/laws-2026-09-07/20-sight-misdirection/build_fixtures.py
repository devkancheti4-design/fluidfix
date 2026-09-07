#!/usr/bin/env python
"""Build the two misdirection fixtures (report-only; writes ONLY under this
directory). Rerun freely: it wipes and recreates fixtures/.

A  named/    the click shape.  tests/test_shell.py fails with a pure
             assertion (no source frame, no 2+-digit literal).  pkg/shell.py
             shares the token "shell" with the test module (NAMED) and is
             executed by that test only (FAILONLY, SMALL).  The defect is a
             strictness flip in pkg/types.py, which EVERY test executes
             (UBIQUITOUS).  Every shipped class signal matches every source
             file, so SCARCE cannot fire.
B  framed/   tests/test_api.py calls pkg/api.py which validates the value
             returned by pkg/core.py and RAISES.  The traceback frames api.py
             (FRAMED); the defect (flipped-additive) is in core.py, which has
             already returned and is in no frame.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

# --- shared "signal ballast": every shipped KINDS signal matches these
# lines, so in a repo where every file carries them no signal is SCARCE.
# (A real code base carries comparisons, digits, +/-, min/max, True/False in
# nearly every file; a tiny fixture must reproduce that or SCARCE lies.)
BALLAST = '''
DEFAULT_WIDTH = 80


def _bounded(n, lo, hi):
    """Clamp n into [lo, hi]."""
    if n < lo:
        return lo
    if n > hi:
        return hi
    return n


def _stats(xs):
    total = 0
    count = 0
    for x in xs:
        total += x
        count += 1
    spread = max(xs) - min(xs) if xs else 0
    return total, count, spread


def _pair(a, b, swap=False):
    if swap is True:
        return b + a
    return a + b
'''

PYTEST_INI = "[pytest]\npythonpath = .\ntestpaths = tests\n"


def _w(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text.lstrip("\n"))


def build_named(root):
    _w(root, "pytest.ini", PYTEST_INI)
    # click-shaped package: importing the package imports every module, so
    # the failing test EXECUTES every file (at least its def lines)
    _w(root, "pkg/__init__.py", "from . import types, core, parser, utils, shell  # noqa: F401\n")
    # the defect file: UBIQUITOUS (every test executes it), no token overlap
    # with tests/test_shell.py, the failing test executes only truncate().
    _w(root, "pkg/types.py", '''
"""Value coercion helpers shared by every entry point."""
''' + BALLAST + '''

def truncate(items, limit):
    """Keep at most `limit` items, in order."""
    out = []
    for item in items:
        if len(out) > limit:        # DEFECT: should be >=
            break
        out.append(item)
    return out


def coerce_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text == "":
        return default
    sign = 1
    if text[0] == "-":
        sign = -1
        text = text[1:]
    if not text.isdigit():
        return default
    return sign * int(text)


def coerce_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return bool(value)


def coerce_list(value, sep=","):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    parts = []
    for piece in str(value).split(sep):
        piece = piece.strip()
        if piece:
            parts.append(piece)
    return parts


def coerce_range(value):
    lo, hi = value.split("..")
    lo = coerce_int(lo)
    hi = coerce_int(hi)
    if lo > hi:
        lo, hi = hi, lo
    return list(range(lo, hi + 1))


def coerce_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if text == "":
        return default
    try:
        number = float(text)
    except ValueError:
        return default
    return _bounded(number, -1e9, 1e9)


def coerce_pair(value, sep=":"):
    left, _, right = str(value).partition(sep)
    a = coerce_int(left)
    b = coerce_int(right)
    total, count, spread = _stats([a, b])
    if spread > DEFAULT_WIDTH:
        return _pair(a, b, swap=True), total
    return _pair(a, b), total


def normalise_key(key):
    text = str(key).strip().lower()
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    while out and out[-1] == "_":
        out.pop()
    return "".join(out)


def coerce_choice(value, choices, default=None):
    text = str(value).strip().lower()
    for choice in choices:
        if text == str(choice).lower():
            return choice
    for choice in choices:
        if str(choice).lower().startswith(text) and text:
            return choice
    return default
''')
    # the NAMED decoy: shares "shell" with tests/test_shell.py, executed by
    # that test only.
    _w(root, "pkg/shell.py", '''
"""Shell-style rendering of item lists."""
from . import types
''' + BALLAST + '''

def render(items, limit):
    """Render up to `limit` items, space separated."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    kept = types.truncate(items, limit)
    return " ".join(str(k) for k in kept)
''')
    _w(root, "pkg/core.py", '''
"""Core arithmetic over coerced values."""
from . import types
''' + BALLAST + '''

def total(values):
    return sum(types.coerce_int(v) for v in values)


def average(values):
    ints = [types.coerce_int(v) for v in values]
    if not ints:
        return 0
    return sum(ints) / len(ints)
''')
    _w(root, "pkg/parser.py", '''
"""Key=value line parsing."""
from . import types
''' + BALLAST + '''

def parse(line):
    key, _, value = line.partition("=")
    return key.strip(), types.coerce_list(value)


def parse_flags(line):
    out = {}
    for piece in types.coerce_list(line, sep=" "):
        key, _, value = piece.partition("=")
        out[key] = types.coerce_bool(value if value else "true")
    return out
''')
    _w(root, "pkg/utils.py", '''
"""Small helpers."""
from . import types
''' + BALLAST + '''

def span(text):
    return types.coerce_range(text)


def width_of(items):
    return max(len(str(i)) for i in items) if items else 0
''')
    # tests: the failing one is a pure assertion on short strings
    _w(root, "tests/__init__.py", "")
    _w(root, "tests/test_shell.py", '''
from pkg import shell


def test_render_respects_limit():
    assert shell.render(["a", "b", "c", "d"], 3) == "a b c"
''')
    _w(root, "tests/test_core.py", '''
from pkg import core


def test_total():
    assert core.total(["1", "2", None, "x", "-4"]) == -1


def test_average():
    assert core.average(["2", "4"]) == 3.0
    assert core.average([]) == 0
''')
    _w(root, "tests/test_parser.py", '''
from pkg import parser


def test_parse():
    assert parser.parse("k = a, b ,c") == ("k", ["a", "b", "c"])


def test_flags():
    assert parser.parse_flags("v=yes q=off d") == {"v": True, "q": False, "d": True}
''')
    _w(root, "tests/test_types.py", '''
from pkg import types


def test_ints_and_floats():
    assert types.coerce_int(" -7 ") == -7
    assert types.coerce_int(True) == 1
    assert types.coerce_int("x", 9) == 9
    assert types.coerce_float("1,5") == 1.5
    assert types.coerce_float("nope", 2.0) == 2.0
    assert types.coerce_float(None) == 0.0


def test_pairs_and_keys():
    assert types.coerce_pair("3:4") == (7, 7)
    assert types.coerce_pair("1:200") == (201, 201)
    assert types.normalise_key("  Foo-Bar baz! ") == "foo_bar_baz"
    assert types.coerce_choice("re", ["red", "green"]) == "red"
    assert types.coerce_choice("zz", ["red"], "none") == "none"
    assert types.coerce_bool("off") is False
''')
    _w(root, "tests/test_utils.py", '''
from pkg import utils


def test_span():
    assert utils.span("5..2") == [2, 3, 4, 5]


def test_width():
    assert utils.width_of(["a", "bbb"]) == 3
    assert utils.width_of([]) == 0
''')


def build_framed(root):
    _w(root, "pytest.ini", PYTEST_INI)
    _w(root, "pkg/__init__.py", "")
    _w(root, "pkg/core.py", '''
"""Arithmetic core."""
''' + BALLAST + '''

def combine(a, b):
    """Sum of two non-negative quantities."""
    return a - b                    # DEFECT: should be a + b
''')
    _w(root, "pkg/api.py", '''
"""Public entry point; validates what core returns."""
from . import core
''' + BALLAST + '''

def total(a, b):
    value = core.combine(a, b)
    if value < 0:
        raise ValueError("total went negative: " + str(value))
    return value
''')
    _w(root, "tests/__init__.py", "")
    _w(root, "tests/test_api.py", '''
from pkg import api


def test_total():
    assert api.total(2, 5) == 7
''')


def main():
    if os.path.isdir(FIX):
        shutil.rmtree(FIX)
    build_named(os.path.join(FIX, "named"))
    build_framed(os.path.join(FIX, "framed"))
    print("built", FIX)


if __name__ == "__main__":
    sys.exit(main())
