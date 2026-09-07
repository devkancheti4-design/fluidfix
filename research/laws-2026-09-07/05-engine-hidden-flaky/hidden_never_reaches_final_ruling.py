"""The HIDDEN bit is measured per candidate but is never carried into the
situation the law is asked at the END of a search.

Shows (a) the bits each final-ruling call site actually passes, read from the
source, and (b) what the law would rule if HIDDEN were included.
Run: .venv/bin/python hidden_never_reaches_final_ruling.py
"""
import ast, re
from fluidfix.engine import decide, situation

SRC = {"loop.py": "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/loop.py",
       "guard.py": "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix/guard.py"}

print("every situation(...) the body builds, with the bits it passes:")
for name, path in SRC.items():
    tree = ast.parse(open(path).read(), path)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "situation":
            bits = [k.arg for k in n.keywords]
            print(f"  {name}:{n.lineno}  situation({', '.join(bits)})"
                  f"{'   <-- HIDDEN' if 'HIDDEN' in bits else ''}")

print("\nwhat the law rules for the two situations a rejected-by-re-check "
      "search could be described by:")
print("  REFUTED alone            ->", decide(situation(REFUTED=True)),
      "   (what guard.py:612/618 asks today)")
print("  REFUTED+HIDDEN           ->", decide(situation(REFUTED=True, HIDDEN=True)),
      "   (the situation as measured)")
print("  BUILT+HIDDEN             ->", decide(situation(BUILT=True, HIDDEN=True)))
print("  BUILT alone              ->", decide(situation(BUILT=True)),
      "   (what loop.py:217 asks when a coarse green survives)")
