from pathlib import Path

p = Path("/Users/kanchetidevieswar/neo/fluidfix/research/kindof-2026-09-18/kindof.py")
s = p.read_text()

FUNC = '''def structure_preserving(broken: str, fixed: str) -> tuple[bool, str]:
    """Is this a one-line fix a vocabulary could ever be TAUGHT, or does it just game the budget?

    "Exactly one line replaced" turns out to be gameable, and the model answering level 1 found the hole at
    once: replace a function's DOCSTRING with `return list(range(start, 0, -1))` and leave the entire
    original body underneath as dead code. That is one line by the diff, and nothing any vocabulary of line
    transforms would ever propose. So the budget is measured here, not merely counted.

    Two disqualifications, both decided from the text and the AST:
      * the replaced line was a docstring or a comment -- not a line the failing test ever executed
      * the edit leaves statements that can never run, an unconditional return/raise now preceding them
    """
    import ast as _ast
    a, b = broken.split("\\n"), fixed.split("\\n")
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal" or i1 >= len(a):
            continue
        old = a[i1].strip()
        if old[:1] in {"#", chr(34), chr(39)}:
            return False, "replaced a docstring or comment, not a line the test executed"
    try:
        tree = _ast.parse(fixed)
    except SyntaxError:
        return False, "does not parse"
    for node in _ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for st in body[:-1]:
            if isinstance(st, (_ast.Return, _ast.Raise)):
                return False, "leaves dead code after an unconditional return"
    return True, ""


'''

anchor = "def obeys(level: int, s: dict) -> bool:"
assert anchor in s and "structure_preserving" not in s
s = s.replace(anchor, FUNC + anchor, 1)

old_keep = '''            st["rows"][cid].update({"kind": LEVELS[a.level], "level": a.level, "edit": s, "patch": patch})
            kept += 1
            print(f"{c['fault']:16} {c['writer']:16} {shape:>22}  {LEVELS[a.level]}")'''
new_keep = '''            ok, why = structure_preserving(c["code"], patch) if a.level == 1 else (True, "")
            st["rows"][cid].update({"kind": LEVELS[a.level], "level": a.level, "edit": s,
                                    "patch": patch, "structure_preserving": ok, "caveat": why})
            kept += 1
            note = "" if ok else "   [GAMES THE BUDGET: " + why + "]"
            print(f"{c['fault']:16} {c['writer']:16} {shape:>22}  {LEVELS[a.level]}{note}")'''
assert old_keep in s
s = s.replace(old_keep, new_keep, 1)

old_rep = """        for k, v in t.most_common():
            print(f"{k:22} {v:>3}   {meaning.get(k, '')}")"""
new_rep = """        for k, v in t.most_common():
            print(f"{k:22} {v:>3}   {meaning.get(k, '')}")
        gamed = [v for v in st["rows"].values() if v.get("structure_preserving") is False]
        real = [v for v in st["rows"].values() if v.get("structure_preserving") is True]
        if gamed or real:
            print(f"\\nof the ONE-LINE verdicts: {len(real)} structure-preserving (a vocabulary could be "
                  f"taught them), {len(gamed)} game the budget:")
            for v in gamed:
                print(f"    {v['fault']:16} {v['writer']:16} {v['caveat']}")"""
assert old_rep in s
s = s.replace(old_rep, new_rep, 1)

p.write_text(s)
print("patched")
