# A literal off by one in EITHER direction. The shipped class only decrements — it was taught from an
# incident where a literal was one too large — so `return 0` -> `return 1` is outside it for no reason
# other than the direction of the example it came from. This is the same defect shape the audit found
# twice: the signal generalises, the applier carries its example's assumption.
def _literal_either_way(line, o):
    out = []
    for m in re.finditer(r"(?<![A-Za-z_\d.])(\d+)(?![A-Za-z_\d.])", line):
        for delta in (1, -1):
            v = int(m.group(1)) + delta
            if v >= 0:
                out.append(line[:m.start(1)] + str(v) + line[m.end(1):])
    return out


register(4, "literal-off-by-one-either-way",
         "a numeric literal one away from correct, in either direction",
         re.compile(r"(?<![A-Za-z_\d.])\d+(?![A-Za-z_\d.])"),
         _literal_either_way)
