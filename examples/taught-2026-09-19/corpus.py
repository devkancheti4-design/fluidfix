# The taught vocabulary for the real-repo corpus, with every class in its post-audit state.
#
# A user dictionary owns kinds 4..7 — four slots — and there are now six taught classes competing for
# them. The earlier "combined" file spent slots 4 and 5 on the two classes learned from model-written
# bugs (mutating-call, missing-separator) and thereby DROPPED flipped-boolean-operator and
# get-without-default, which are exactly what this corpus needs. The net then hit its node budget on
# click/andor-1 without ever holding the class that repairs it — a harness failure that looks like a
# refusal, which is the same mistake this project keeps having to catch.
#
#   4  flipped-boolean-operator   from the 2026-09-16 session, unchanged
#   5  get-without-default        from the 2026-09-16 session, unchanged
#   6  inverted-bare-guard        unchanged (audited 2026-09-19: sound)
#   7  len-as-last-index          FIXED: signal widened, and the PLACEMENT LAW rules where the token goes

from fluidfix.place import insert_token


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


# kind 7 — the class the 2026-09-19 audit rewrote. The old signal refused `len(x) * 2` outright, and the
# old applier trailed ` - 1` after the call, which is (k*len) - 1 rather than k*(len - 1). The law decides
# placement now, which the byte-exact criterion requires: always bracketing is semantically correct and
# scores 0 of 4 against this corpus, where every lenm1 original is unparenthesised.
_LEN = re.compile(r"\blen\([\w.\[\]]+\)(?!\s*-\s*1\b)")


def _len_minus_one(line, o):
    return [insert_token(line, m.start(), m.end(), " - 1") for m in _LEN.finditer(line)] or [line]


register(7, "len-as-last-index",
         "a len(x) standing where the last valid index len(x) - 1 belongs",
         _LEN,
         _len_minus_one)
