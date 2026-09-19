# Classes that edit a SPAN, not a line.
#
# Every applier written before this returned one replacement line, and from that I had concluded — out
# loud, repeatedly — that "every act transforms a line that is already there, so an insertion is
# impossible". That was never true of the mechanism. A candidate is spliced in as a string, so a candidate
# containing a newline becomes several lines, and `loop._restored_original` already compares a SPAN
# (`new_line.split("\n")`). The limit was in the appliers, not the vocabulary.
#
# Measured motive: of 552 real single-file fix commits, 37% replace one line and 70% are five lines or
# fewer. Everything between those two numbers was unreachable for no reason but habit.

import re as _re


# ---- a collection is mutated in place and the function ends without returning it.
# Seen twice in the model-bug corpus (insert_sorted, two different writers) and once in the class audit.
def _mutate_then_return(line, o):
    m = _re.match(r"^(\s*)([A-Za-z_]\w*)\.(\w+)\((.*)\)\s*$", line)
    if not m:
        return []
    indent, receiver = m.group(1), m.group(2)
    return [f"{line}\n{indent}return {receiver}"]


register(4, "mutating-call-missing-its-return",
         "a collection is mutated in place and the function ends without returning it",
         re.compile(r"^\s*[A-Za-z_]\w*\.\w+\(.*\)\s*$"),
         _mutate_then_return)


# ---- a name is used that was never imported.
# Seen twice in the model-bug corpus (percentile, two different writers): `ceil(...)` with no import.
# The insertion has to land at the TOP of the file, so the signal matches the `def` line and the applier
# emits the import above it — the same splice, aimed at a different line.
_KNOWN = {
    "ceil": "from math import ceil", "floor": "from math import floor",
    "sqrt": "from math import sqrt", "math": "import math",
    "Counter": "from collections import Counter", "defaultdict": "from collections import defaultdict",
    "bisect": "import bisect", "deque": "from collections import deque",
    "reduce": "from functools import reduce", "datetime": "import datetime", "re": "import re",
}


def _add_missing_import(line, o):
    body = "\n".join(getattr(o, "all_lines", []) or [])
    out = []
    for name, stmt in _KNOWN.items():
        if stmt in body:
            continue
        if _re.search(r"(?<![\w.])" + _re.escape(name) + r"\s*\(", body) or \
           _re.search(r"(?<![\w.])" + _re.escape(name) + r"\.", body):
            out.append(f"{stmt}\n\n\n{line}")
    return out


register(5, "name-used-but-never-imported",
         "a name is called or dereferenced that no import in the file provides",
         re.compile(r"^def \w+\("),
         _add_missing_import)
