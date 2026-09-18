# Two classes taught from the edit-budget ladder's own output (research/kindof-2026-09-18).
#
# The ladder found, by search rather than by opinion, that 11 of 14 real model-written faults have a
# one-line replacement the suite accepts. Nine of those look like RECURRING shapes rather than one-off
# cleverness. A shape is only worth teaching if it recurs, so these are the two that appeared twice each,
# in code written by different models.
#
# A class is nothing more than:
#     a SIGNAL   a regex saying which lines could possibly exhibit this fault
#     an APPLIER a function proposing the replacement line(s)
# and nothing about it is trusted: the target project's own suite judges every candidate, and anything it
# rejects is rolled back byte-exact. Teaching cannot make the tool wrong, only wider.


# ---------------------------------------------------------------- class 4: the missing separator
#
#   gemma3:4b   truncate_words:  return truncated + '...'          -> + ' ...'
#   qwen3.5:4b  truncate_words:  truncated = ' '.join(...) + '...' -> + ' ...'
#
# A token is appended to a joined string and the separator that joins it is forgotten. The spec said "as a
# separate word"; the code said "glued to the last one". Two different models, same slip.

def _add_separator(line, o):
    out = []
    for q in ("'", '"'):
        # the literal appended at the end of the line, when it does not already begin with a space
        m = re.search(r"\+\s*" + q + r"(?! )([^" + q + r"]*)" + q + r"\s*$", line)
        if m:
            out.append(line[: m.start(1)] + " " + line[m.start(1):])
    return out


register(4, "missing-separator-before-appended-token",
         "a token is concatenated onto a joined string without the separator that joins the rest",
         re.compile(r"\+\s*['\"][^'\"]*['\"]\s*$"),
         _add_separator)


# ---------------------------------------------------------------- class 5: the mutating call's result
#
#   gemma3:4b   insert_sorted:  items.insert(index, value)  -> return items.insert(index, value) or items
#   qwen3.5:4b  insert_sorted:  items.insert(index, value)  -> return items.insert(index, value) or items
#
# The function mutates a collection in place and ends without returning it, so the caller gets None. The
# shipped vocabulary cannot express "add a return" — every act transforms a line that is already there —
# but the mutation line itself can BECOME the return, because a mutating method answers None and `or`
# then yields the collection. Two different models, same slip, and the ladder found this exact form.

def _return_the_mutated(line, o):
    m = re.match(r"^(\s*)([A-Za-z_]\w*)\.(\w+)\((.*)\)\s*$", line)
    if not m:
        return []
    indent, receiver, _meth, _args = m.groups()
    return [f"{indent}return {line.strip()} or {receiver}"]


register(5, "mutating-call-whose-result-is-dropped",
         "a collection is mutated in place on the last line and never returned, so the caller gets None",
         re.compile(r"^\s*[A-Za-z_]\w*\.\w+\(.*\)\s*$"),
         _return_the_mutated)
