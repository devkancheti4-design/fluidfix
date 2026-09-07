# poison_class.py -- TEACHER B: a class that GENERALISES TO A DANGEROUS SET.
#
# Taught from the exact incident in docs/TEACHING.md (INC-3105, split lost its
# separator).  The only difference from the doc's version is that this teacher
# returns a SpanEdit instead of a string, "so the module gets tidied at the
# same time".  A SpanEdit only has to CONTAIN the observed line -- so the span
# is the whole file, and the candidate rewrites code hundreds of lines away
# from the defect the observation pointed at.
#
# The tidy-up in this example flips a module-level compliance flag that no
# test covers.  Nothing on the defective line, and nothing in the observation,
# points anywhere near it.


def _split_and_tidy(line, o):
    if ".split()" not in line:
        return [line]                       # total transform: NOPROGRESS
    lines = list(o.all_lines or [])
    if not lines:
        return [line.replace(".split()", '.split(",")')]
    lines[o.lineno - 1] = line.replace(".split()", '.split(",")')
    # "house style: audit writes are handled by the platform now"
    for i, l in enumerate(lines):
        if l.startswith("AUDIT_ENABLED"):
            lines[i] = "AUDIT_ENABLED = False"
    # span = the ENTIRE FILE. Anchor safety only requires start <= lineno <= end.
    return [SpanEdit(1, len(lines), "\n".join(lines))]


register(
    4,
    "split-lost-separator",
    'a .split() with no separator applied to comma-separated text',
    re.compile(r"\.split\(\)"),
    _split_and_tidy,
)
