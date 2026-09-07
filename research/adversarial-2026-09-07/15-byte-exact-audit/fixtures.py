# Byte-exact audit fixtures.
#
# Each fixture is (name, mode, pristine_module_bytes, test_bytes,
#                  defect_bytes, note)
# `pristine` is the CORRECT program as the user had it on disk, byte for byte.
# `defect` is the same file with ONE mechanical fault injected and NOTHING
# else changed. A byte-exact repair must reproduce `pristine` exactly.
#
# Deliberately awkward inputs are included: CRLF, no final newline, tabs, a
# UTF-8 BOM, non-ASCII identifiers/strings, trailing whitespace, an
# executable file mode, and a latin-1 encoded source.

F = []


def fx(name, pristine, test, defect, note, mode=0o644, enc="utf-8"):
    F.append(dict(name=name, note=note, mode=mode,
                  pristine=pristine.encode(enc) if isinstance(pristine, str) else pristine,
                  test=test.encode("utf-8") if isinstance(test, str) else test,
                  defect=defect.encode(enc) if isinstance(defect, str) else defect))


# ---------------------------------------------------------------- 01 control
fx("01-strictness-lf",
   "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
   "        if x > t:\n            n += 1\n    return n\n",
   "from mod import count_above\n\ndef test_c():\n"
   "    assert count_above([1, 5, 5, 9], 5) == 1\n",
   "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
   "        if x >= t:\n            n += 1\n    return n\n",
   "control: plain LF, kind 0 strictness")

# ------------------------------------------------------------------- 02 CRLF
fx("02-additive-crlf",
   "def join2(a, b):\r\n    return a + b\r\n",
   "from mod import join2\n\ndef test_j():\n"
   "    assert join2('x', 'y') == 'xy'\n",
   "def join2(a, b):\r\n    return a - b\r\n",
   "CRLF line endings throughout, kind 3 flipped-additive")

# ------------------------------- 03 swapped return operands + trailing spaces
fx("03-swapret-trailing-ws",
   "def join2(a, b):\n    return a + b  \n",
   "from mod import join2\n\ndef test_j():\n"
   "    assert join2('x', 'y') == 'xy'\n",
   "def join2(a, b):\n    return b + a  \n",
   "kind 2 swapped-return-operands on a line with TWO trailing spaces")

# ------------------------------------------------------- 04 no final newline
fx("04-literal-no-final-nl",
   "def take(xs):\n    return xs[1:]",
   "from mod import take\n\ndef test_t():\n"
   "    assert take([1, 2, 3]) == [2, 3]\n",
   "def take(xs):\n    return xs[2:]",
   "no trailing newline at EOF, kind 1 literal-off-by-one")

# ------------------------------------------------------------------- 05 tabs
fx("05-minmax-tabs",
   "def clamp_hi(v, hi):\n\treturn min(v, hi)\n",
   "from mod import clamp_hi\n\ndef test_c():\n"
   "    assert clamp_hi(9, 4) == 4\n",
   "def clamp_hi(v, hi):\n\treturn max(v, hi)\n",
   "TAB indentation, kind 8 minmax-swap")

# -------------------------------------------------------------- 06 UTF-8 BOM
fx("06-strictness-bom",
   "\ufeffdef count_above(xs, t):\n    n = 0\n    for x in xs:\n"
   "        if x > t:\n            n += 1\n    return n\n",
   "from mod import count_above\n\ndef test_c():\n"
   "    assert count_above([1, 5, 5, 9], 5) == 1\n",
   "\ufeffdef count_above(xs, t):\n    n = 0\n    for x in xs:\n"
   "        if x >= t:\n            n += 1\n    return n\n",
   "UTF-8 BOM as the first three bytes, kind 0 strictness")

# -------------------------------------------- 07 non-ASCII identifier/string
fx("07-nonascii-ident",
   "GRÜSSE = 'héllo — wörld'\n\n\ndef größe(xs, t):\n"
   "    return len([x for x in xs if x > t])\n",
   "from mod import größe, GRÜSSE\n\ndef test_g():\n"
   "    assert GRÜSSE == 'héllo — wörld'\n"
   "    assert größe([1, 5, 5, 9], 5) == 1\n",
   "GRÜSSE = 'héllo — wörld'\n\n\ndef größe(xs, t):\n"
   "    return len([x for x in xs if x >= t])\n",
   "non-ASCII identifier + em-dash/umlaut string literal, kind 0")

# ------------------------------------------------------ 08 augmented assign
# (a `while k:` body was the first draft; flipping its `k -= 1` gives a
#  non-terminating candidate that costs the full --suite-timeout. That is
#  fluidfix behaving correctly — a bounded candidate — but it is 300s of
#  clock unrelated to byte-exactness, so the loop is bounded here instead.)
fx("08-augmented-assign",
   "def drain(n, k):\n    for _ in range(k):\n        n -= 1\n"
   "    return n\n",
   "from mod import drain\n\ndef test_d():\n"
   "    assert drain(10, 3) == 7\n",
   "def drain(n, k):\n    for _ in range(k):\n        n += 1\n"
   "    return n\n",
   "kind 9 flipped-augmented-assign")

# ------------------------------------------------- 09 comparison direction
fx("09-comparison-direction",
   "def below(xs, t):\n    return [x for x in xs if x < t]\n",
   "from mod import below\n\ndef test_b():\n"
   "    assert below([1, 5, 9], 5) == [1]\n",
   "def below(xs, t):\n    return [x for x in xs if x > t]\n",
   "kind 10 flipped-comparison-direction")

# --------------------------------------------------------------- 10 boolean
fx("10-boolean-flip",
   "def is_ready(n):\n    if n > 3:\n        return True\n"
   "    return False\n",
   "from mod import is_ready\n\ndef test_r():\n"
   "    assert is_ready(9) is True\n    assert is_ready(1) is False\n",
   "def is_ready(n):\n    if n > 3:\n        return False\n"
   "    return False\n",
   "kind 12 flipped-boolean")

# ---------------------------------- 11 reversed minus operands + trailing ws
fx("11-revminus-trailing-ws",
   "def gap(a, b):\n    return b - a   \n",
   "from mod import gap\n\ndef test_g():\n    assert gap(2, 9) == 7\n",
   "def gap(a, b):\n    return a - b   \n",
   "kind 11 reversed-minus-operands, THREE trailing spaces on the line")

# ----------------------------------------------- 12 CRLF + no final newline
fx("12-crlf-no-final-nl",
   "def take(xs):\r\n    return xs[1:]",
   "from mod import take\n\ndef test_t():\n"
   "    assert take([1, 2, 3]) == [2, 3]\n",
   "def take(xs):\r\n    return xs[2:]",
   "CRLF AND no trailing newline, kind 1")

# --------------------------------------------------- 13 executable file mode
fx("13-exec-mode",
   "def join2(a, b):\n    return a + b\n",
   "from mod import join2\n\ndef test_j():\n"
   "    assert join2(2, 3) == 5\n",
   "def join2(a, b):\n    return a - b\n",
   "file mode 0o755 (an executable module), kind 3", mode=0o755)

# ----------------------------------------- 14 zero-padded literal in a string
fx("14-zero-padded-escape",
   "BOLD = '\\033[1m'\n\n\ndef bold(s):\n    return BOLD + s\n",
   "from mod import bold\n\ndef test_b():\n"
   "    assert bold('x') == '\\x1b[1mx'\n",
   "BOLD = '\\034[1m'\n\n\ndef bold(s):\n    return BOLD + s\n",
   "zero-padded octal escape inside a string, kind 1")

# ------------------------------------------------- 15 latin-1 encoded source
fx("15-latin1-source",
   b"# -*- coding: latin-1 -*-\nGREET = 'caf\xe9'\n\n\ndef above(xs, t):\n"
   b"    return len([x for x in xs if x > t])\n",
   "from mod import above, GREET\n\ndef test_a():\n"
   "    assert GREET == 'caf\\xe9'\n    assert above([1, 5, 9], 5) == 1\n",
   b"# -*- coding: latin-1 -*-\nGREET = 'caf\xe9'\n\n\ndef above(xs, t):\n"
   b"    return len([x for x in xs if x >= t])\n",
   "latin-1 declared source with a non-UTF-8 byte, kind 0")

# --------------------------- 16 trailing whitespace on an untouched neighbour
fx("16-neighbour-trailing-ws",
   "def count_above(xs, t):   \n    n = 0\t\n    for x in xs:\n"
   "        if x > t:\n            n += 1  \n    return n\n\n",
   "from mod import count_above\n\ndef test_c():\n"
   "    assert count_above([1, 5, 5, 9], 5) == 1\n",
   "def count_above(xs, t):   \n    n = 0\t\n    for x in xs:\n"
   "        if x >= t:\n            n += 1  \n    return n\n\n",
   "trailing whitespace on neighbouring lines + a blank final line, kind 0")
