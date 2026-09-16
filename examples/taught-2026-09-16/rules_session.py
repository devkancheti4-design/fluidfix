# rules_session.py — four fault classes met in the 2026-09-16 real-repo study, each taught from ONE
# worked example (the click incident), by hand, no model. A user dictionary owns kinds 4..7; the
# fifth class of the study (range start) is in rules_session_b.py because the slots ran out.
# Every applier returns CANDIDATES; the target's own suite judges every one, byte-exact rollback on rejection.

# kind 4 — incident: zsh completion printed "_" for the wrong items (click shell_completion.py:467)
#   help_ = item.help and "_"      <- shipped
#   help_ = item.help or "_"       <- the fix
# The class: one boolean operator on the line is the wrong one. Every `and`<->`or` flip on the line
# is a candidate; the suite picks (the direction differs per incident).
def _flip_andor(line, o):
    out = []
    for m in re.finditer(r"\b(and|or)\b", line):
        other = "or" if m.group(1) == "and" else "and"
        out.append(line[:m.start()] + other + line[m.end():])
    return out or [line]

register(4, "flipped-boolean-operator",
         "an `and` where an `or` belongs on the line, or the reverse; the condition is wrong for the boundary case",
         re.compile(r"\b(and|or)\b"),
         _flip_andor)

# kind 5 — incident: LESS unset, None reached a str parameter (click _termui_impl.py:579)
#   less_env = os.environ.get("LESS")         <- shipped
#   less_env = os.environ.get("LESS", "")     <- the fix
# The class: a `.get(key)` with no default. The default is the neutral value of the type the caller
# expects: "" for text, 0 for a number — both are candidates for every such .get on the line.
def _get_default(line, o):
    out = []
    for m in re.finditer(r"\.get\(\s*((?:\"[^\"]*\"|'[^']*'))\s*\)", line):
        for d in ('""', "0"):
            out.append(line[:m.start()] + f".get({m.group(1)}, {d})" + line[m.end():])
    return out or [line]

register(5, "get-without-default",
         "a .get(key) with no default, so a missing key yields None where a value of the key's type is expected",
         re.compile(r"\.get\(\s*(?:\"[^\"]*\"|'[^']*')\s*\)"),
         _get_default)

# kind 6 — incident: an emptiness guard inverted, empty value fell through to value[0] (click shell_completion.py:664)
#   if value:          <- shipped
#   if not value:      <- the fix
# The class: a bare-name condition `if X:` / `elif X:` / `while X:` whose sense is inverted.
def _negate_guard(line, o):
    m = re.match(r"^(\s*)(if|elif|while) (\w+):\s*$", line)
    if not m:
        return [line]
    ind, kw, name = m.groups()
    return [f"{ind}{kw} not {name}:"]

register(6, "inverted-bare-guard",
         "a bare-name guard `if X:` that should read `if not X:`, so the empty/None case takes the wrong branch",
         re.compile(r"^\s*(?:if|elif|while) \w+:\s*$"),
         _negate_guard)

# kind 7 — incident: last index computed as len(words), one past the end (click utils.py:84)
#   last_index = len(words)          <- shipped
#   last_index = len(words) - 1      <- the fix
# The class: a `len(x)` used as a last position with the `- 1` missing. Every `len(...)` on the line
# that is not already part of an arithmetic expression gets a `- 1` candidate.
def _len_minus_one(line, o):
    out = []
    for m in re.finditer(r"\blen\([\w.\[\]]+\)(?!\s*[-+*/%])", line):
        out.append(line[:m.end()] + " - 1" + line[m.end():])
    return out or [line]

register(7, "len-as-last-index",
         "a len(x) standing where the last valid index len(x) - 1 belongs",
         re.compile(r"\blen\([\w.\[\]]+\)(?!\s*[-+*/%])"),
         _len_minus_one)
