# examples/company_rules.py — a complete repo fault-class dictionary:
# one pure rule, one repo-mined candidate set, one SpanEdit. Load it:
#
#   fluidfix guard . --commit --dictionary examples/company_rules.py
#
# or from Python:
#
#   from fluidfix.acts import load_dictionary
#   load_dictionary("examples/company_rules.py")     # -> 3
#
# Inside a dictionary file `register`, `re`, and `SpanEdit` are pre-bound;
# ordinary imports work. Kinds 4-7 are reserved for user dictionaries.
# Full contract: docs/TEACHING.md. Every class below is executed end-to-end
# by tests/test_teaching.py; version a file like this next to the code it
# maintains so CI and every teammate's guard share the same taught classes.

import ast


# --- kind 4: a pure rule — one candidate derived from the line alone --------
# Taught from ONE worked example (incident INC-2041):
#   due += inv["amount"] + inv.get("tax")      <- summed None, crashed
#   due += inv["amount"] + inv.get("tax", 0)   <- the fix
register(
    4,
    "missing-get-default",
    'a .get(key) with no default, letting None poison arithmetic',
    re.compile(r"\.get\((\"[^\"]+\"|'[^']+')\)"),
    lambda line, o: re.sub(r"\.get\((\"[^\"]+\"|'[^']+')\)",
                           r".get(\1, 0)", line),
)


# --- kind 5: a repo-mined candidate set -------------------------------------
# Taught from ONE worked example (incident INC-2213):
#   return user.name        <- wrong attribute; the right one (.id) already
#                              exists elsewhere in the same file
# The correct value is not on the line — it lives in the repo. Enumerate a
# candidate SET from obs.all_lines (capped at 32); the suite tries each in
# order and still refuses when none passes.

def _attrs_in_repo(o):
    """Every attribute name used anywhere in the defect file."""
    try:
        tree = ast.parse("\n".join(o.all_lines or []))
    except SyntaxError:
        return []
    return sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)})


register(
    5,
    "wrong-attribute",
    "a returned attribute that is the wrong one; the right name exists "
    "elsewhere in this file",
    re.compile(r"return \w+\.\w+"),
    lambda line, o: [re.sub(r"(return \w+)\.\w+", rf"\1.{a}", line)
                     for a in _attrs_in_repo(o)],
)


# --- kind 6: a SpanEdit — two lines wrong TOGETHER --------------------------
# Taught from ONE worked example (incident INC-2358): rounding moved ahead
# of the surcharge. Neither line's change alone can green the suite, so a
# single-line candidate cannot land:
#   total = round(subtotal)          <- rounds too early
#   total = total + surcharge
# the fix, one atomic SpanEdit:
#   total = subtotal + surcharge
#   total = round(total)

def _round_last(line, o):
    m = re.match(r"^(\s*)(\w+) = round\((\w+)\)$", line)
    if not m:
        return [line]                       # not this class: no progress
    ind, acc, raw = m.groups()
    lines = o.all_lines or []
    nxt = lines[o.lineno] if o.lineno < len(lines) else ""
    m2 = re.match(rf"^\s*{acc} = {acc} \+ (\w+)$", nxt)
    if not m2:
        return [line]
    return [SpanEdit(o.lineno, o.lineno + 1,
                     f"{ind}{acc} = {raw} + {m2.group(1)}\n"
                     f"{ind}{acc} = round({acc})")]


register(
    6,
    "round-before-accumulate",
    "a round() applied before a following line adds to the rounded value; "
    "the two lines must swap roles together",
    re.compile(r"\w+ = round\(\w+\)"),
    _round_last,
)
