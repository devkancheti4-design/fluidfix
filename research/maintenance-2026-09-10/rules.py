# rules.py — the three taught classes for the maintenance test. Each is written
# from ONE worked example. Kinds 4-7 are the user's; nothing here edits a law.
import ast


# kind 4 — a pure rule over the line
#   return round(amount)        <- money rounded to whole units
#   return round(amount, 2)     <- the fix
register(
    4, "round-lost-precision",
    "a round() on a money value with no ndigits, dropping the cents",
    re.compile(r"round\(\w+\)"),
    lambda line, o: re.sub(r"round\((\w+)\)", r"round(\1, 2)", line),
)


# kind 5 — a candidate SET mined from the repo (the right name is not on the line)
#   return item.name            <- wrong attribute; .sku exists elsewhere in the file
def _attrs_in_file(o):
    try:
        tree = ast.parse("\n".join(o.all_lines or []))
    except SyntaxError:
        return []
    return sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)})


register(
    5, "wrong-attribute",
    "a returned attribute that is the wrong one; the right name exists elsewhere in this file",
    re.compile(r"return \w+\.\w+"),
    lambda line, o: [re.sub(r"(return \w+)\.\w+", rf"\1.{a}", line) for a in _attrs_in_file(o)],
)


# kind 6 — two lines wrong TOGETHER: one atomic SpanEdit
#   total = round(subtotal)     <- rounds too early
#   total = total + surcharge
#   fix:  total = subtotal + surcharge / total = round(total)
def _round_last(line, o):
    m = re.match(r"^(\s*)(\w+) = round\((\w+)\)$", line)
    if not m:
        return [line]
    ind, acc, raw = m.groups()
    lines = o.all_lines or []
    nxt = lines[o.lineno] if o.lineno < len(lines) else ""
    m2 = re.match(rf"^\s*{acc} = {acc} \+ (\w+)$", nxt)
    if not m2:
        return [line]
    return [SpanEdit(o.lineno, o.lineno + 1,
                     f"{ind}{acc} = {raw} + {m2.group(1)}\n{ind}{acc} = round({acc})")]


register(
    6, "round-before-accumulate",
    "a round() applied before a following line adds to the rounded value; the two lines must swap roles together",
    re.compile(r"\w+ = round\(\w+\)"),
    _round_last,
)
