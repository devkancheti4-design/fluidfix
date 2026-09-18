# Taught at the memory's own level, from one worked example.
#
#   WAVE1_CLASSES = 1     <- shipped: wave 1 carries one class fewer than it should
#   WAVE1_CLASSES = 2     <- the fix
#
# The shipped literal class only decrements ("a literal exactly one greater than correct"), so a cap that
# is one too SMALL is outside it. One example teaches the other direction, and the head's memory then
# remembers which class repairs a memory.

def _raise_cap(line, o):
    return [re.sub(r"(?<![\w.])(\d+)(?![\w.])", lambda m: str(int(m.group(1)) + 1), line, count=1)]


register(4, "literal-one-too-small",
         "a numeric literal on the line is exactly one less than correct",
         re.compile(r"^[A-Z][A-Z0-9_]* = \d+$"),
         _raise_cap)
