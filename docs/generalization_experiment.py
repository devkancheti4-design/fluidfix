"""Does ONE example per class generalize to unseen bugs of that class?

For each class: teach fluidfix from exactly ONE worked example (a register()
transform written the way that one example would naturally imply), then test
on N DIFFERENT held-out bugs of the same class. Each held-out case is a real
tiny module + pytest test: inject the bug, confirm the suite catches it, run
fluidfix, check the suite goes green AND the line is byte-exact to intended.

The honest question this answers: for which classes is the repair a pure
function of the broken line (generalizes from one example) vs. one that needs
information the line doesn't carry (does not)?
"""
import os, re, shutil, sys, tempfile
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import Oracle, build_packet, MechanicalObserver, repair, KINDS, ACTS
from fluidfix.acts import register

PY = sys.executable

def run_case(kind, module_src, intended_line, buggy_line, test_src):
    """Return 'exact' | 'green-only' | 'refused' | 'setup-fail'."""
    d = tempfile.mkdtemp()
    try:
        fixed = module_src.replace("###LINE###", intended_line)
        broken = module_src.replace("###LINE###", buggy_line)
        open(os.path.join(d, "mod.py"), "w").write(broken)
        open(os.path.join(d, "test_mod.py"), "w").write(test_src)
        oracle = Oracle(d, python=PY)
        if oracle.green():                      # bug must actually break the suite
            return "setup-fail"
        packet = build_packet(oracle, "mod.py", coverage_target="mod")
        if packet is None:
            return "setup-fail"
        obs = MechanicalObserver().observe([packet])[0]
        res = repair(oracle, "mod.py", obs)
        if not res.repaired:
            return "refused"
        return "exact" if res.new_line.strip() == intended_line.strip() else "green-only"
    finally:
        shutil.rmtree(d, ignore_errors=True)

# Each class: (register args) + a list of held-out cases (module, intended, buggy, test)
def M(body):  # module template with a ###LINE### slot
    return body

CASES = {}

# ---- classes where the repair is a PURE FUNCTION OF THE LINE (should generalize)
CASES["cmp-strictness"] = (
    (0, "strictness", "a comparison with wrong strictness",
        re.compile(r"[<>]=?"),
        lambda l, o: (l.replace(">=", ">", 1) if ">=" in l else l.replace("<=", "<", 1)
                      if "<=" in l else l.replace(">", ">=", 1) if ">" in l
                      else l.replace("<", "<=", 1))),
    [
        ("def f(x, t):\n    ###LINE###\n        return 1\n    return 0\n",
         "if x > t:", "if x >= t:",
         "from mod import f\ndef test():\n    assert f(5, 5) == 0\n"),
        ("def g(a, b):\n    ###LINE###\n        return 'hi'\n    return 'lo'\n",
         "if a <= b:", "if a < b:",
         "from mod import g\ndef test():\n    assert g(5, 5) == 'hi'\n"),
        ("def h(n):\n    ###LINE###\n        return 'big'\n    return 'ok'\n",
         "if n > 100:", "if n >= 100:",
         "from mod import h\ndef test():\n    assert h(100) == 'ok'\n"),
    ])

CASES["additive-flip"] = (
    (1, "additive", "a + that should be - or vice versa",
        re.compile(r"\s[-+]\s"),
        lambda l, o: (l.replace(" + ", " - ", 1) if " + " in l else l.replace(" - ", " + ", 1))),
    [
        ("def f(a, b):\n    ###LINE###\n",
         "return a - b", "return a + b",
         "from mod import f\ndef test():\n    assert f(10, 3) == 7\n"),
        ("def tax(p, t):\n    ###LINE###\n",
         "return p + t", "return p - t",
         "from mod import tax\ndef test():\n    assert tax(100, 5) == 105\n"),
        ("def bal(s, w):\n    ###LINE###\n",
         "return s - w", "return s + w",
         "from mod import bal\ndef test():\n    assert bal(50, 20) == 30\n"),
    ])

CASES["get-default"] = (
    (2, "get-default", "a .get(key) missing its default",
        re.compile(r"\.get\((\"[^\"]+\"|'[^']+')\)"),
        lambda l, o: re.sub(r"\.get\((\"[^\"]+\"|'[^']+')\)", r".get(\1, 0)", l)),
    [
        ("def total(d):\n    ###LINE###\n",
         'return d.get("x", 0) + 1', 'return d.get("x") + 1',
         "from mod import total\ndef test():\n    assert total({}) == 1\n"),
        ("def s(cfg):\n    ###LINE###\n",
         'return cfg.get("n", 0) * 2', 'return cfg.get("n") * 2',
         "from mod import s\ndef test():\n    assert s({}) == 0\n"),
        ("def c(row):\n    ###LINE###\n",
         'return row.get("q", 0) - 1', 'return row.get("q") - 1',
         "from mod import c\ndef test():\n    assert c({}) == -1\n"),
    ])

CASES["swapped-return-operands"] = (
    (3, "swap", "return a OP b with operands swapped",
        re.compile(r"^\s*return\s+.*\s(?://|[-+*/])\s"),
        lambda l, o: (lambda m: l if not m else f"{m.group(1)}{m.group(4)}{m.group(3)}{m.group(2)}")(
            re.match(r"^(\s*return\s+)(.*?)(\s(?://|[-+*/])\s)(.*)$", l))),
    [
        ("def d(a, b):\n    ###LINE###\n",
         "return a / b", "return b / a",
         "from mod import d\ndef test():\n    assert d(10, 2) == 5\n"),
        ("def sub(x, y):\n    ###LINE###\n",
         "return x - y", "return y - x",
         "from mod import sub\ndef test():\n    assert sub(9, 4) == 5\n"),
    ])

# ---- classes where the fix needs info NOT ON THE LINE (should NOT generalize)
# taught from ONE example that implies a specific replacement:
CASES["wrong-variable"] = (
    # the example was: return self.name  ->  return self.email
    # so the most a single example teaches is "return .email instead"
    (4, "wrong-var", "the returned attribute is the wrong one",
        re.compile(r"return \w+\.\w+"),
        lambda l, o: re.sub(r"(return \w+)\.\w+", r"\1.email", l)),
    [
        # held-out bug #1: should be .id, not .email
        ("class U:\n    def __init__(s):\n        s.id=7; s.name='a'\ndef f(u):\n    ###LINE###\n",
         "return u.id", "return u.name",
         "from mod import U, f\ndef test():\n    assert f(U()) == 7\n"),
        # held-out bug #2: should be .total, not .email
        ("class R:\n    def __init__(s):\n        s.total=99; s.count=1\ndef g(r):\n    ###LINE###\n",
         "return r.total", "return r.count",
         "from mod import R, g\ndef test():\n    assert g(R()) == 99\n"),
    ])

CASES["wrong-constant"] = (
    # the example was: timeout = 30 -> timeout = 60. One example implies "= 60".
    (5, "wrong-const", "a constant set to the wrong value",
        re.compile(r"=\s*\d+\s*$"),
        lambda l, o: re.sub(r"=\s*\d+\s*$", "= 60", l)),
    [
        ("def f():\n    ###LINE###\n    return retries\n",
         "retries = 5", "retries = 3",
         "from mod import f\ndef test():\n    assert f() == 5\n"),
        ("def g():\n    ###LINE###\n    return size\n",
         "size = 1024", "size = 512",
         "from mod import g\ndef test():\n    assert g() == 1024\n"),
    ])

CASES["missing-guard"] = (
    # example: a function needed `if n == 0: return 0` before dividing.
    # one example implies inserting that specific guard.
    (6, "missing-guard", "a division needs a zero-guard",
        re.compile(r"return .+ / \w+\s*$"),
        lambda l, o: (lambda ind: f"{ind}if n == 0:\n{ind}    return 0\n{l}")(
            l[:len(l) - len(l.lstrip())])),
    [
        # held-out: the denominator is 'count', not 'n' — the taught guard checks the wrong name
        ("def rate(total, count):\n    ###LINE###\n",
         "    if count == 0:\n        return 0\n    return total / count",
         "    return total / count",
         "from mod import rate\ndef test():\n    assert rate(10, 0) == 0 and rate(10, 2) == 5\n"),
    ])

if __name__ == "__main__":
    print(f"{'class':26s} {'held-out':9s} {'exact':6s} {'green':6s} {'refused':8s}  verdict")
    print("-" * 78)
    for name, (reg, cases) in CASES.items():
        # reset registry to shipped state, then teach THIS class from its one example
        for k in list(KINDS):
            if k >= 4: KINDS.pop(k, None)
        for a in list(ACTS):
            if a >= 9: ACTS.pop(a, None)
        register(*reg)
        outcomes = [run_case(name, m, intended, buggy, t) for (m, intended, buggy, t) in cases]
        ex = outcomes.count("exact"); gr = outcomes.count("green-only")
        rf = outcomes.count("refused") + outcomes.count("setup-fail")
        n = len(outcomes)
        verdict = "GENERALIZES" if ex == n else ("partial" if ex + gr > 0 else "does NOT generalize")
        print(f"{name:26s} {n:<9d} {ex:<6d} {gr:<6d} {rf:<8d}  {verdict}")
