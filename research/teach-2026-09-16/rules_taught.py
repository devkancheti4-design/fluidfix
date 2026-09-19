# rules_taught.py — four fault classes the seeded real-repo bench (2026-09-16) refused, each taught by hand
# from ONE worked example (the click case), no model involved. Kinds 4-7 are the user slots; the fifth class
# of that bench (range start dropped) lives in rules_taught_rangestart.py because a dictionary has four slots.
# Every rule is a class over the line, as docs/TEACHING.md asks: the suite is the judge, a wrong candidate
# costs a suite run, never a wrong repair. The rules were frozen before the hold-out runs.


# --- kind 4: and/or flipped. Worked example: click src/click/shell_completion.py:467 -------------------------
#   help_ = item.help and "_"      <- suite red: the "_" fallback landed on the wrong items
#   help_ = item.help or "_"       <- the fix
def _flip_andor(line, o):
    out = []
    for m in re.finditer(r"\b(and|or)\b", line):
        other = "or" if m.group(1) == "and" else "and"
        out.append(line[:m.start()] + other + line[m.end():])
    return out or line

register(4, "and-or-flipped",
         'a boolean "and" that should be "or", or an "or" that should be "and"',
         re.compile(r"\b(and|or)\b"), _flip_andor)


# --- kind 5: .get(key) lost its default. Worked example: click src/click/_termui_impl.py:579 -----------------
#   less_env = os.environ.get("LESS")        <- suite red: None reached a str parameter
#   less_env = os.environ.get("LESS", "")    <- the fix
# The default's spelling is not on the line; the common typed defaults are a candidate SET (capped at 32).
_DEFAULTS = ['""', "0", "None", "False", "[]", "{}", "''", "0.0", "()"]

def _add_get_default(line, o):
    out = []
    for m in re.finditer(r"\.get\(\s*([^(),]+?)\s*\)", line):
        for d in _DEFAULTS:
            out.append(line[:m.start()] + ".get(" + m.group(1) + ", " + d + ")" + line[m.end():])
    return out or line

register(5, "get-without-default",
         "a .get(key) call with no default, whose None result reaches code that expects a value",
         re.compile(r"\.get\(\s*[^(),]+\s*\)"), _add_get_default)


# --- kind 6: a guard lost its "not". Worked example: click src/click/shell_completion.py:664 ----------------
#   if value:            <- suite red: the empty case fell through to value[0]
#   if not value:        <- the fix
# Taught as the bare-name guard the example shows: "if/elif/while <name>:" or "return <name>".
def _restore_not(line, o):
    m = re.match(r"^(\s*)(if|elif|while)\s+([A-Za-z_][\w.]*)\s*:\s*$", line)
    if m:
        return f"{m.group(1)}{m.group(2)} not {m.group(3)}:"
    m = re.match(r"^(\s*)return\s+([A-Za-z_][\w.]*)\s*$", line)
    if m:
        return f"{m.group(1)}return not {m.group(2)}"
    return line

register(6, "guard-not-dropped",
         'an "if"/"elif"/"while" on a bare name, or a "return" of one, whose leading "not" is missing: the branch fires on the opposite truth',
         re.compile(r"^\s*(?:(?:if|elif|while)\s+[A-Za-z_][\w.]*\s*:|return\s+[A-Za-z_][\w.]*)\s*$"), _restore_not)


# --- kind 7: len(x) lost its "- 1". Worked example: click src/click/utils.py:84 ------------------------------
#   last_index = len(words)          <- suite red: one past the end
#   last_index = len(words) - 1      <- the fix
def _restore_len_minus_one(line, o):
    out = []
    for m in re.finditer(r"len\([^()]+\)", line):
        tail = line[m.end():]
        if re.match(r"\s*-\s*1\b", tail):
            continue
        out.append(line[:m.end()] + " - 1" + tail)
    return out or line

register(7, "len-minus-one-dropped",
         'a len(x) used as a last index or position without its "- 1", pointing one past the end',
         re.compile(r"len\([^()]+\)(?!\s*-\s*1\b)"), _restore_len_minus_one)
