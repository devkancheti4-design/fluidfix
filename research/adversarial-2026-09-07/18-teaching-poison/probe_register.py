# What does register() validate? One line per probe. No fluidfix source touched.
import re, sys, warnings
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.acts import register, KINDS, ACTS, act_for, candidates
from fluidfix import Observation

def probe(label, fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            r = fn()
            print(f"{label:44s} ACCEPTED -> {r!r}  warnings={[str(x.message)[:60] for x in w]}")
        except Exception as e:
            print(f"{label:44s} REFUSED  -> {type(e).__name__}: {e}")

# 1. an applier that is the identity of a LIE (transform contradicts description)
probe("applier contradicts description",
      lambda: register(4, "x", "a line that adds when it should subtract",
                       re.compile(r"\+"), lambda l, o: l.replace("+", "*")))
# 2. signal that matches literally every line (docs call this a grind)
probe("signal = re.compile('') matches everything",
      lambda: register(5, "everything", "any line at all", re.compile(""),
                       lambda l, o: l + "  # touched"))
# 3. description written as an INSTRUCTION (docs say 'bad')
probe("description is an instruction, not an obs",
      lambda: register(6, "y", "add a default of 0 to .get calls",
                       re.compile(r"\.get\("), lambda l, o: l))
# 4. applier that returns None (docs: never return None)
probe("applier returns None",
      lambda: register(7, "z", "d", re.compile(r"a"), lambda l, o: None))
# 5. applier that raises
probe("applier raises",
      lambda: register(7, "z2", "d", re.compile(r"a"),
                       lambda l, o: (_ for _ in ()).throw(RuntimeError("boom"))))
# 6. signal is not a regex at all
probe("signal is a plain string, not a compiled regex",
      lambda: register(7, "z3", "d", "not-a-regex", lambda l, o: l))
# 7. applier is not callable
probe("applier is not callable",
      lambda: register(7, "z4", "d", re.compile(r"a"), "nope"))
# 8. clobber a SHIPPED kind
probe("kind=3 clobbers shipped flipped-additive",
      lambda: register(3, "poison", "d", re.compile(r"zzz"), lambda l, o: l))
# 9. out of range
probe("kind=16 out of range",
      lambda: register(16, "q", "d", re.compile(r"a"), lambda l, o: l))
# 10. two dictionaries claiming the same kind
probe("second register on the same kind (silent replace)",
      lambda: register(4, "second-owner", "d2", re.compile(r"b"), lambda l, o: l))

print()
print("kind 3 is now:", KINDS[3][0], "| act_for(3) =", act_for(3))
print("kind 4 is now:", KINDS[4][0])
print("act 8 (was _flip_additive) is now:", ACTS[act_for(3)].__name__ if hasattr(ACTS[act_for(3)], '__name__') else ACTS[act_for(3)])
print("shipped kind-3 repair on 'return a + b':",
      candidates("    return a + b", act_for(3), Observation(lineno=1)))
