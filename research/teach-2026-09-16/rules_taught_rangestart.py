# rules_taught_rangestart.py — the fifth class of the seeded bench, taught by hand from ONE worked example
# (a dictionary holds four user kinds, 4-7; this one is loaded on its own).
# Worked example: python-sortedcontainers src/sortedcontainers/sortedlist.py:2465
#   for pos in range(len(self._keys)):        <- suite red: the loop must start at 1
#   for pos in range(1, len(self._keys)):     <- the fix
def _restore_range_start(line, o):
    out = []
    for m in re.finditer(r"\brange\(\s*(?!1\s*,)((?:[^(),]|\([^()]*\))+)\)", line):
        out.append(line[:m.start()] + "range(1, " + m.group(1).strip() + ")" + line[m.end():])
    return out or line

register(4, "range-start-dropped",
         "a range(n) whose loop must start at 1: range(1, n)",
         re.compile(r"\brange\(\s*(?!1\s*,)(?:[^(),]|\([^()]*\))+\)"), _restore_range_start)
