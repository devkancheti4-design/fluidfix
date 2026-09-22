# rules.py — teaching fluidnet. A class is a SIGNAL, a REWRITE, and a PROPERTY.
# Written once, beside the code it maintains. The suite judges every candidate;
# the property refuses wrong ones before the suite ever runs.
import tokenize, io
from fluidfix.place import insert_token

# kind 4 — a wrong attribute on a receiver; the right one is a SIBLING this file uses
_ATTR = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b(?!\s*=[^=])")

def sibling(line, o):
    text = "\n".join(getattr(o, "all_lines", None) or [])
    out = []
    for m in _ATTR.finditer(line):
        recv, wrong = m.group(1), m.group(2)
        pool = set(re.findall(r"\b" + re.escape(recv) + r"\.(\w+)", text)) - {wrong}
        out += [line[:m.start(2)] + c + line[m.end(2):] for c in sorted(pool)]
    return out or [line]

register(4, "wrong-attribute-sibling", "an attribute by the wrong name; the right one is a sibling",
         _ATTR, sibling)

def one_attribute_only(orig, cand):
    tk = lambda s: [t.string for t in tokenize.generate_tokens(io.StringIO(s.strip()).readline)]
    a, b = tk(orig), tk(cand)
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(a) != len(b) or len(diff) != 1:
        return False, "more than one token moved", len(a)
    if diff[0] == 0 or a[diff[0] - 1] != ".":
        return False, "the changed token is not an attribute", len(a)
    return True, "", len(a)

teach_property(4, "exactly one token changes, it is an attribute after a dot, nothing else moves",
               one_attribute_only)

# kind 7 — len(x) standing where the last index len(x) - 1 belongs. WHERE the token goes
# is not this file's call: insert_token measures the operators and the PLACEMENT LAW rules.
_LEN = re.compile(r"\blen\(\w+\)(?!\s*-\s*1\b)")

register(7, "len-as-last-index", "a len(x) standing where the last valid index len(x) - 1 belongs",
         _LEN, lambda line, o: [insert_token(line, m.start(), m.end(), " - 1") for m in _LEN.finditer(line)])

def placement_preserves_value(orig, cand):
    o, c = propcheck.rhs(orig), propcheck.rhs(cand)
    intended = re.sub(r"\blen\(\w+\)", "(__L - 1)", o, count=1)
    actual = re.sub(r"\blen\(\w+\)", "__L", c, count=1)
    return propcheck.agree_over(intended, actual, grid=(1, 2, 3, 5, 8))

teach_property(7, "the candidate equals the original with len(x) -> (len(x) - 1), for every length",
               placement_preserves_value)
