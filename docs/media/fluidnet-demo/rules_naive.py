# rules.py — teaching fluidnet. A class is a SIGNAL, a REWRITE, and a PROPERTY.
# Written once, beside the code it maintains. The suite judges every candidate;
# the property refuses wrong ones before the suite ever runs.
import tokenize, io

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

# kind 7 — the NAIVE way: append " - 1" right after len(...). Correct where len(x) is the
# whole right-hand side, the shape it was taught on. Nothing here says where the token goes.
_LEN = re.compile(r"\blen\(\w+\)(?!\s*-\s*1\b)")

register(7, "len-as-last-index", "a len(x) standing where the last valid index len(x) - 1 belongs",
         _LEN, lambda line, o: [line[:m.end()] + " - 1" + line[m.end():] for m in _LEN.finditer(line)])
