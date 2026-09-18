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


# A second class, taught at the memory's own level from one worked example. This is the fault the loop
# actually found underneath itself (see RESULT.md, "the third direction"):
#
#   for k in remembered[:WAVE1_CLASSES]:    <- ranks: carries only the most recent few
#   for k in remembered:                    <- covers: carries every class it remembers
#
# No literal value repairs the first form, because the bound that would be correct grows with every class
# learned. The fault is the SLICE, not the number in it. That is §2 of the lake result arrived at from
# underneath — a fan-out must cover, not rank — and it is a single-line rewrite, so one example teaches it.

def _drop_the_rank(line, o):
    return [re.sub(r"\[\s*:\s*[A-Za-z_][\w.]*\s*\]", "", line, count=1)]


register(5, "ranks-where-it-must-cover",
         "a collection is cut to a bounded prefix on a line whose property is coverage",
         re.compile(r"for\s+\w+\s+in\s+\w+\[\s*:\s*[A-Za-z_][\w.]*\s*\]\s*:"),
         _drop_the_rank)
