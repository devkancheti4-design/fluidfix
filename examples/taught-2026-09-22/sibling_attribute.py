# sibling_attribute.py — ONE fault class, taught 2026-09-22 from ONE worked example, by hand, no model.
#
# kind 4 — incident: click dce3b868, parser.py
#     self.fail('no such option: %s' % opt)      <- shipped
#     self.error('no such option: %s' % opt)     <- the fix
# The class: an attribute is looked up on a receiver, and the name is wrong — the right name is a SIBLING,
# something the receiver actually has. `kwargs.get` where `.pop` was meant; `term.partition` for
# `.rpartition`; `cls.fromdate` for `.fromdatetime`; `triplet.css` for `.hex`. The code around it is
# already right; one identifier after a dot is not.
#
# Where do the candidates come from? Not from a guess. Three places the file itself can vouch for:
#   1. other attributes used on the SAME receiver anywhere in the file       term.rpartition, seen at line 80
#   2. functions defined in the file, when the wrong name is one of them or  def error(self, ...) is right
#      the receiver is self/cls                                                  there in the class
#   3. the wrong name's own builtin family: if it is a dict method, the other  .get -> .pop, .setdefault ...
#      dict methods are its siblings; same for str, list, set
# Ranked by string similarity to the wrong name, capped, and the SUITE picks. Nothing is accepted on
# resemblance; every candidate is one suite run, byte-exact rollback on rejection.
#
# Held out for the real-shape test: arrow f872d7a5, arrow 877cd149, arrow 16cd686b, rich e1c105b8,
# rich 87528364 — none of them consulted while writing this.

import difflib

# recv.name — or call().name / x[i].name, where the receiver is not a bare name. Not an assignment target.
_ATTR = re.compile(r"(?:\b([A-Za-z_]\w*)|[\)\]])\.([A-Za-z_]\w*)\b(?!\s*=[^=])")
_FAMILIES = {t: {n for n in dir(t) if not n.startswith("_") and callable(getattr(t, n))}
             for t in (dict, str, list, set)}
_CAP = 32


def _pools(recv, name, body):
    """Two pools, by how much the file vouches for them. FILE: names this file defines or uses on this very
    receiver. FAMILY: the wrong name's builtin siblings — a guess the file does not confirm."""
    text = "\n".join(body)
    defs = {d for d in re.findall(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", text, re.M) if not d.startswith("__")}
    file_pool = set()
    if recv:
        file_pool |= {a for a in re.findall(r"\b" + re.escape(recv) + r"\.([A-Za-z_]\w*)", text)
                      if not a.startswith("__")}                                       # 1. same receiver
    if name in defs or recv in ("self", "cls"):
        file_pool |= defs                                                              # 2. same file
    family = set()
    for fam in _FAMILIES.values():
        if name in fam:
            family |= fam                                                              # 3. builtin family
    file_pool.discard(name); family.discard(name); family -= file_pool
    return file_pool, family


def _sibling(line, o):
    """Candidates in two tiers — every attribute's FILE-evidenced siblings first, then every attribute's
    FAMILY guesses — interleaved across the attributes on the line, so no one attribute's long list can
    starve another's under a candidate cap. Measured 2026-09-22: emitting `out.append`'s ten list
    siblings before `ledger.length`'s file-defined ones put the correct fix at position 12, and the
    harness cap was 8. Ordering by evidence, not by position on the line, is the body measuring."""
    body = getattr(o, "all_lines", None) or []
    per_attr = []
    for m in _ATTR.finditer(line):
        recv, name = m.group(1), m.group(2)
        file_pool, family = _pools(recv, name, body)
        rank = lambda pool: sorted(pool, key=lambda c: -difflib.SequenceMatcher(None, name, c).ratio())
        mk = lambda c: line[:m.start(2)] + c + line[m.end(2):]
        per_attr.append(([mk(c) for c in rank(file_pool)], [mk(c) for c in rank(family)]))
    out, seen = [], set()
    for tier in (0, 1):
        lists = [pa[tier] for pa in per_attr]
        for i in range(max((len(l) for l in lists), default=0)):
            for l in lists:
                if i < len(l) and l[i] not in seen and l[i] != line:
                    seen.add(l[i]); out.append(l[i])
    return out[:_CAP] or [line]


register(4, "wrong-attribute-sibling",
         "an attribute looked up on a receiver by the wrong name, where the right name is a sibling the "
         "receiver actually has",
         _ATTR,
         _sibling)


# ---------------------------------------------------------------- the property
# "The rewrite changes exactly one token; that token is an attribute name after a dot; nothing else on the
#  line moves." This is what a wrong-name applier most often gets wrong — a regex that replaces the name
#  everywhere it appears (`get` inside `getattr`, the receiver as well as the attribute). Structural, needs
#  no execution, and it refuses those for free.
import tokenize as _tk, io as _io


def _toks(s):
    try:
        return [(t.type, t.string) for t in _tk.generate_tokens(_io.StringIO(s.strip()).readline)
                if t.type not in (_tk.NEWLINE, _tk.NL, _tk.ENDMARKER, _tk.INDENT, _tk.DEDENT)]
    except Exception:
        return None


def _prop_one_attribute(orig, cand):
    a, b = _toks(orig), _toks(cand)
    if a is None or b is None:
        return None, "could not tokenise", 0
    if len(a) != len(b):
        return False, f"token count changed {len(a)} -> {len(b)}: more than a name moved", len(a)
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(diff) != 1:
        return False, f"{len(diff)} tokens differ; exactly one attribute name may", len(a)
    i = diff[0]
    if a[i][0] != _tk.NAME or b[i][0] != _tk.NAME:
        return False, "the changed token is not a name", len(a)
    if i == 0 or a[i - 1][1] != ".":
        return False, "the changed name is not an attribute (no dot before it)", len(a)
    return True, "", len(a)


teach_property(4, "the rewrite changes exactly one token, that token is an attribute name after a dot, "
                  "and nothing else on the line moves",
               _prop_one_attribute)
