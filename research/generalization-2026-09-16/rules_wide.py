# rules_wide.py — identical to rules.py except kind 4 is taught with a wider pattern: any non-nested argument, not just a name.

# kind 4 — incident: money rounded to whole units
#   return round(total)        <- shipped
#   return round(total, 2)     <- the fix
register(4, "round-lost-precision",
         'a round() on a money value with no ndigits, dropping the cents',
         re.compile(r"round\(([^(),]+)\)"),
         lambda line, o: re.sub(r"round\(([^(),]+)\)", r"round(\1, 2)", line))

# kind 5 — incident INC-2041: summed None, crashed
#   due += inv["amount"] + inv.get("tax")      <- shipped
#   due += inv["amount"] + inv.get("tax", 0)   <- the fix
register(5, "missing-get-default",
         'a .get(key) with no default, letting None poison arithmetic',
         re.compile(r"\.get\((\"[^\"]+\"|'[^']+')\)"),
         lambda line, o: re.sub(r"\.get\((\"[^\"]+\"|'[^']+')\)", r".get(\1, 0)", line))

# kind 6 — incident INC-3105: whitespace-split shipped over comma data
#   fields = row.split()         <- shipped
#   fields = row.split(",")      <- the fix
register(6, "split-lost-separator",
         'a .split() with no separator applied to comma-separated text',
         re.compile(r"\.split\(\)"),
         lambda line, o: line.replace(".split()", '.split(",")'))

# kind 7 — incident INC-2358: rounding moved ahead of the surcharge (two lines together)
#   total = round(subtotal)          <- shipped
#   total = total + surcharge
#   total = subtotal + surcharge     <- the fix, one atomic SpanEdit
#   total = round(total)
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

register(7, "round-before-accumulate",
         "a round() applied before a following line adds to the rounded value; "
         "the two lines must swap roles together",
         re.compile(r"\w+ = round\(\w+\)"),
         _round_last)
