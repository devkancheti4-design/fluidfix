# The four taught classes in their state after the 2026-09-19 audit, in one file, because net.py loads
# exactly one dictionary. Nothing new is taught here; this is 4, 5, 6 and 7 as they now stand.
#
#   4  missing-separator-before-appended-token    unchanged (audited: narrow, never wrong)
#   5  mutating-call-whose-result-is-dropped      FIXED: the call's answer is discarded positionally,
#                                                 so a truthy pop() can never stand in for the collection
#   6  inverted-bare-guard                        unchanged (audited: sound)
#   7  len-as-last-index                          FIXED: the signal no longer refuses `len(x) * 2`, and
#                                                 the PLACEMENT LAW rules where the token goes, which the
#                                                 byte-exact criterion requires

from fluidfix.place import insert_token


def _add_separator(line, o):
    out = []
    for q in ("'", '"'):
        m = re.search(r"\+\s*" + q + r"(?! )([^" + q + r"]*)" + q + r"\s*$", line)
        if m:
            out.append(line[: m.start(1)] + " " + line[m.start(1):])
    return out


register(4, "missing-separator-before-appended-token",
         "a token is concatenated onto a joined string without the separator that joins the rest",
         re.compile(r"\+\s*['\"][^'\"]*['\"]\s*$"),
         _add_separator)


def _return_the_mutated(line, o):
    m = re.match(r"^(\s*)([A-Za-z_]\w*)\.(\w+)\((.*)\)\s*$", line)
    if not m:
        return []
    indent, receiver, _meth, _args = m.groups()
    return [f"{indent}return ({line.strip()}, {receiver})[-1]"]


register(5, "mutating-call-whose-result-is-dropped",
         "a collection is mutated in place on the last line and never returned, so the caller gets None",
         re.compile(r"^\s*[A-Za-z_]\w*\.\w+\(.*\)\s*$"),
         _return_the_mutated)


def _negate_guard(line, o):
    m = re.match(r"^(\s*)(if|elif|while) (\w+):\s*$", line)
    if not m:
        return [line]
    ind, kw, name = m.groups()
    return [f"{ind}{kw} not {name}:"]


register(6, "inverted-bare-guard",
         "a bare-name guard `if X:` that should read `if not X:`",
         re.compile(r"^\s*(?:if|elif|while) \w+:\s*$"),
         _negate_guard)


_LEN = re.compile(r"\blen\([\w.\[\]]+\)(?!\s*-\s*1\b)")


def _len_minus_one(line, o):
    return [insert_token(line, m.start(), m.end(), " - 1") for m in _LEN.finditer(line)] or [line]


register(7, "len-as-last-index",
         "a len(x) standing where the last valid index len(x) - 1 belongs",
         _LEN,
         _len_minus_one)
