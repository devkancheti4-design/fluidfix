#!/usr/bin/env python3
"""Novel instances of the sibling-attribute shape: names, values, and — the axis that matters —
syntactic POSITION all vary. None of these lines was ever shown to the class. Judged by the suite."""
import random, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "src")); sys.path.insert(0, str(R / "research/life-fluidfix-2026-09-18"))
from life_fluidfix import shapes_repair, run_test
DICT = str(R / "examples/taught-2026-09-22/sibling_attribute.py")
rng = random.Random(2026_09_22)
CLASSES = ["Bag", "Tray", "Queue", "Ledger", "Basket", "Deck", "Shelf", "Pool"]
RECV = ["b", "box", "store", "q", "items_", "self_box", "ledger", "tray"]
NAMES = ["head", "tail", "count", "first", "last", "size", "top", "bottom", "length", "front", "back", "total"]
ITEMS = [5, 1, 2, 7]                                 # first 5, last 7, size 4, min 1, all distinct

def instance(form, seed):
    r = random.Random(seed)
    cls = r.choice(CLASSES); recv = r.choice(RECV)
    a, b, c, d = r.sample(NAMES, 4)                 # a: items[0]  b: items[-1]  c: len  d: sum (decoy)
    # the function needs the "last" behaviour (b) but calls a wrong sibling
    wrong = r.choice([a, c, d]); right = b
    K = r.randint(1, 3)
    klass = (f"class {cls}:\n    def __init__(self, items): self.items = list(items)\n"
             f"    def {a}(self): return self.items[0]\n    def {b}(self): return self.items[-1]\n"
             f"    def {c}(self): return len(self.items)\n    def {d}(self): return min(self.items)\n")
    helper = "def twice(x): return x * 2\n"
    bodies = {
     1: (f"def f({recv}):\n    return {recv}.WRONG()\n",                      f"assert f({cls}({ITEMS})) == 7"),
     2: (f"def f({recv}):\n    v = {recv}.WRONG() + {K}\n    return v\n",     f"assert f({cls}({ITEMS})) == {7+K}"),
     3: (f"def f({recv}):\n    return twice({recv}.WRONG())\n",               f"assert f({cls}({ITEMS})) == 14"),
     4: (f"def f({recv}):\n    out = []\n    out.append({recv}.WRONG())\n    return out\n", f"assert f({cls}({ITEMS})) == [7]"),
     5: (f"def f({recv}):\n    if {recv}.WRONG() > 6:\n        return 'big'\n    return 'small'\n", f"assert f({cls}({ITEMS})) == 'big'"),
     6: (f"def f({recv}):\n    return {{'v': {recv}.WRONG()}}\n",              f"assert f({cls}({ITEMS})) == {{'v': 7}}"),
     7: (f"class Use:\n    def __init__(self, items): self.items = list(items)\n"
         f"    def {a}(self): return self.items[0]\n    def {b}(self): return self.items[-1]\n"
         f"    def {c}(self): return len(self.items)\n    def {d}(self): return min(self.items)\n    def go(self):\n        return self.WRONG()\n",
         f"assert Use({ITEMS}).go() == 7"),
    }
    body, test = bodies[form]
    code = (klass + helper if form != 7 else helper) + body
    owner = cls if form != 7 else "Use"
    siblings = "\n".join(f"assert {owner}({ITEMS}).{n}() == {v}" for n, v in ((a, 5), (b, 7), (c, 4), (d, 1)))
    return code.replace("WRONG", wrong), code.replace("WRONG", right), test + "\n" + siblings

def main():
    FORMS = {1: "return recv.m()", 2: "v = recv.m() + k", 3: "twice(recv.m())", 4: "out.append(recv.m())",
             5: "if recv.m() > k:", 6: "{'v': recv.m()}", 7: "self.m() inside a class"}
    N = 12
    print(f"{'position (never taught)':28} {'repaired':>9} {'exact fix':>10} {'suite runs':>10}")
    tot = ok = exact = runs = 0
    for form, label in FORMS.items():
        rep = ex = rr = 0
        for k in range(N):
            buggy, fixed, test = instance(form, form * 1000 + k)
            assert not run_test(buggy, test), f"form {form} #{k} is not red before repair"
            got = shapes_repair(buggy, test, DICT)
            tot += 1
            if got:
                rep += 1; rr += got["tests_run"]
                if got["code"].strip() == fixed.strip(): ex += 1
        ok += rep; exact += ex; runs += rr
        print(f"{label:28} {rep:>6}/{N} {ex:>7}/{N} {rr/max(1,rep):>10.1f}")
    print("-" * 62)
    print(f"{'all seven positions':28} {ok:>6}/{tot} {exact:>7}/{tot} {runs/max(1,ok):>10.1f}")

    # negative control: a DIFFERENT fault (off-by-one index) in files full of dotted attributes.
    # the class fires — every recv.m() matches its signal — and must accept nothing.
    print("\nnegative control: 12 files whose bug is an off-by-one, not a wrong attribute")
    bad_accept = fired = 0
    for k in range(12):
        r = random.Random(500 + k); cls = r.choice(CLASSES); recv = r.choice(RECV); a, b = r.sample(NAMES, 2)
        code = (f"class {cls}:\n    def __init__(self, items): self.items = list(items)\n"
                f"    def {a}(self): return self.items[0]\n    def {b}(self): return self.items[-1]\n"
                f"def f({recv}):\n    i = len({recv}.items)\n    return {recv}.items[i]\n")
        got = shapes_repair(code, f"assert f({cls}({ITEMS})) == 7", DICT)
        if got: bad_accept += 1
    print(f"  wrong accepts: {bad_accept}/12   (the suite rejected every sibling candidate)")

if __name__ == '__main__':
    main()
