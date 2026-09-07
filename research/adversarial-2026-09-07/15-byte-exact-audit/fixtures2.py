# Round-2 fixtures: the awkward-byte cases the first round pointed at.
# Same shape as fixtures.py; `audit2.py` runs these.
F = []


def fx(name, pristine, test, defect, note, mode=0o644, enc="utf-8"):
    F.append(dict(name=name, note=note, mode=mode,
                  pristine=pristine.encode(enc) if isinstance(pristine, str) else pristine,
                  test=test.encode("utf-8") if isinstance(test, str) else test,
                  defect=defect.encode(enc) if isinstance(defect, str) else defect))


# ------------------------------------ 17 classic-Mac CR-only line endings
# src.split("\n") sees the WHOLE FILE as line 1, so every observation lands
# on "line 1" and an act rewrites the first match anywhere in the file.
fx("17-cr-only-eol",
   "def count_above(xs, t):\r    n = 0\r    for x in xs:\r"
   "        if x > t:\r            n += 1\r    return n\r",
   "from mod import count_above\n\ndef test_c():\n"
   "    assert count_above([1, 5, 5, 9], 5) == 1\n",
   "def count_above(xs, t):\r    n = 0\r    for x in xs:\r"
   "        if x >= t:\r            n += 1\r    return n\r",
   "CR-only (classic Mac) line endings — the whole file is one line to "
   "src.split('\\n')")

# ------------------- 18 trailing whitespace ON the defect line, kind 0 act
fx("18-strictness-trailing-ws",
   "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
   "        if x > t:  \n            n += 1\n    return n\n",
   "from mod import count_above\n\ndef test_c():\n"
   "    assert count_above([1, 5, 5, 9], 5) == 1\n",
   "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
   "        if x >= t:  \n            n += 1\n    return n\n",
   "trailing whitespace ON the repaired line, kind 0 (slice-based act)")

# ------------------- 19 swapped-return-operands with a trailing comment
# _swap_return_operands' last group is `(.*)$` — everything after the
# operator, COMMENT INCLUDED — and it is moved to the LEFT of the operator.
fx("19-swapret-trailing-comment",
   "def delta(a, b):\n    return a - b  # signed difference\n",
   "from mod import delta\n\ndef test_zero_b():\n"
   "    assert delta(5, 0) == 5\n",
   "def delta(a, b):\n    return b - a  # signed difference\n",
   "kind 2 with a trailing comment: the act moves the comment across the "
   "operator, commenting out the rest of the expression")

# ------------------- 20 CRLF where the repaired line is the LAST line
fx("20-crlf-last-line",
   "def gap(a, b):\r\n    return b - a\r\n",
   "from mod import gap\n\ndef test_g():\n    assert gap(2, 9) == 7\n",
   "def gap(a, b):\r\n    return a - b\r\n",
   "CRLF, kind 11 reversed-minus on the final line")
