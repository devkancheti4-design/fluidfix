#!/usr/bin/env python3
"""Does a class taught from ONE example repair NOVEL members of the same shape?

Builds a small repo (4 modules, a suite that pins values), teaches four classes
from one worked example each (rules.py), then injects novel members one at a
time — different files, names, positions, an assignment instead of a return, a
two-line shape — runs the guard exactly as maintenance would, and compares the
file to the PRISTINE bytes. A decoy line matches the taught pattern but is
correct; one member sits deliberately outside the example's pattern.

  PYTHONPATH=<fluidfix>/src python3 run.py
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

PRISTINE = {
"money.py": '''RATE = 0.029


def fee(amount):
    total = amount * RATE + 0.3
    return round(total, 2)


def vat(gross):
    taxed = gross * 0.19
    amount = round(taxed, 2)
    return amount


def net_price(price, qty):
    return round(price * qty, 2)


def whole(x):
    return round(x)
''',
"ledger.py": '''def owed(inv):
    return inv["amount"] + inv.get("tax", 0)


def credit(acct):
    balance = acct.get("balance", 0)
    return balance - acct.get("hold", 0)
''',
"parse.py": '''def fields(row):
    return row.split(",")


def header(line):
    cols = line.split(",")
    return [c.strip() for c in cols]
''',
"totals.py": '''def bill(subtotal, surcharge):
    total = subtotal + surcharge
    total = round(total)
    return total


def settle(base, tip):
    if tip:
        amount = base + tip
        amount = round(amount)
        return amount
    return round(base)
''',
"test_all.py": '''from money import fee, vat, net_price, whole
from ledger import owed, credit
from parse import fields, header
from totals import bill, settle


def test_money():
    assert fee(100) == 3.2
    assert vat(10) == 1.9
    assert net_price(19.99, 3) == 59.97
    assert whole(2.7) == 3          # a correct round(x): the decoy


def test_ledger():
    assert owed({"amount": 5}) == 5
    assert owed({"amount": 5, "tax": 1}) == 6
    assert credit({"balance": 10}) == 10
    assert credit({"balance": 10, "hold": 4}) == 6


def test_parse():
    assert fields("a,b") == ["a", "b"]
    assert header("x, y") == ["x", "y"]


def test_totals():
    assert bill(2.5, 0.4) == 3
    assert settle(1.5, 0.2) == 2
    assert settle(2.5, 0) == 2
''',
}

# (id, description, file, [(pristine line, defective line), ...], expectation, dictionary)
CASES = [
    ("T1", "the taught example itself: return round(x, 2) -> round(x)", "money.py",
     [("    return round(total, 2)", "    return round(total)")], "repair", "rules.py"),
    ("N1", "novel: assignment form, other name, other file position", "money.py",
     [("    amount = round(taxed, 2)", "    amount = round(taxed)")], "repair", "rules.py"),
    ("N2", "novel, OUTSIDE the example's pattern: expression argument", "money.py",
     [("    return round(price * qty, 2)", "    return round(price * qty)")], "refuse", "rules.py"),
    ("N2w", "same member, example rewritten with a wider pattern", "money.py",
     [("    return round(price * qty, 2)", "    return round(price * qty)")], "repair", "rules_wide.py"),
    ("N3", "novel .get() default lost: other key, inside addition", "ledger.py",
     [('    return inv["amount"] + inv.get("tax", 0)', '    return inv["amount"] + inv.get("tax")')], "repair", "rules.py"),
    ("N4", "novel .get() default lost: inside a subtraction, other file position", "ledger.py",
     [('    return balance - acct.get("hold", 0)', '    return balance - acct.get("hold")')], "repair", "rules.py"),
    ("N5", "novel split() lost separator: return form", "parse.py",
     [('    return row.split(",")', "    return row.split()")], "repair", "rules.py"),
    ("N6", "novel split() lost separator: assignment, other name", "parse.py",
     [('    cols = line.split(",")', "    cols = line.split()")], "repair", "rules.py"),
    ("N7", "two lines wrong together (SpanEdit): the taught shape, novel names", "totals.py",
     [("    total = subtotal + surcharge", "    total = round(subtotal)"), ("    total = round(total)", "    total = total + surcharge")], "repair", "rules.py"),
    ("N8", "two lines wrong together: novel names, deeper indentation, inside an if", "totals.py",
     [("        amount = base + tip", "        amount = round(base)"), ("        amount = round(amount)", "        amount = amount + tip")], "repair", "rules.py"),
]


def sh(cmd, cwd, env=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def write_repo(root: Path):
    for name, body in PRISTINE.items():
        (root / name).write_text(body)
    (root / "pyproject.toml").write_text('[project]\nname = "genrepo"\nversion = "0.1"\n\n[tool.pytest.ini_options]\npythonpath = ["."]\n')
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n.fluidfix/\n")


def reset(root: Path):
    for p in root.glob("__pycache__"): shutil.rmtree(p, ignore_errors=True)
    sh(["git", "checkout", "-q", "--", "."], root)
    sh(["git", "clean", "-qfd", "-e", ".fluidfix"], root)
    for name, body in PRISTINE.items():
        (root / name).write_text(body)


def inject(root: Path, file, edits):
    t = (root / file).read_text()
    for old, new in edits:
        assert t.count(old) == 1, (file, old)
        t = t.replace(old, new)
    (root / file).write_text(t)


def main():
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(HERE.parents[1] / "src"))
    work = Path(tempfile.mkdtemp(prefix="genrepo-"))
    root = work / "repo"; root.mkdir(); write_repo(root)
    for d in ("rules.py", "rules_wide.py"):          # versioned next to the code, as TEACHING.md says
        shutil.copy(HERE / d, root / d)
    sh(["git", "init", "-q", "-b", "main"], root)
    sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], root)
    sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "green"], root)
    green = sh([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], root)
    assert green.returncode == 0, green.stdout[-800:]
    results = []
    for cid, desc, file, edits, expect, dic in CASES:
        reset(root); inject(root, file, edits)
        red = sh([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], root)
        assert red.returncode != 0, f"{cid}: the defect is invisible to the suite"
        sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", f"ship {cid}"], root)
        shutil.rmtree(root / ".fluidfix", ignore_errors=True)
        t0 = time.time()
        g = sh([PY, "-c", "from fluidfix.cli import main; raise SystemExit(main())",
                "guard", ".", "--commit", "--dictionary", dic], root, env=env)
        wall = time.time() - t0
        after = (root / file).read_text()
        byte_exact = after == PRISTINE[file]
        untouched = after == "".join(PRISTINE[file]) if False else None
        others_clean = all((root / n).read_text() == PRISTINE[n] for n in PRISTINE if n != file)
        m = re.search(r"repaired line (\d+) in (\d+) suite runs \(([\d.]+)s\)", g.stdout)
        if g.returncode == 0 and byte_exact and expect == "repair": verdict = "REPAIRED byte-exact"
        elif g.returncode == 0 and not byte_exact: verdict = "WRONG REPAIR"
        elif g.returncode == 2 and expect == "refuse": verdict = "REFUSED as expected"
        elif g.returncode == 2: verdict = "MISS (refused)"
        else: verdict = f"exit {g.returncode}"
        hint = next((l.strip() for l in g.stdout.splitlines() if "hint:" in l), "") or g.stderr.strip().splitlines()[-1:] and g.stderr.strip().splitlines()[-1]
        results.append(dict(id=cid, desc=desc, file=file, dictionary=dic, expect=expect, exit=g.returncode,
                            byte_exact=byte_exact, other_files_untouched=others_clean, verdict=verdict,
                            suite_runs=int(m.group(2)) if m else None, reported_s=float(m.group(3)) if m else None,
                            wall_s=round(wall, 1), hint=hint[:200]))
        print(f"{cid:4} {verdict:22} runs={m.group(2) if m else '-':>2} {wall:5.1f}s  {desc}", flush=True)
        if hint and g.returncode == 2: print(f"     {hint[:150]}")
    (HERE / "results.json").write_text(json.dumps(results, indent=1))
    tally = {}
    for r in results: tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print("TALLY", tally); print("work dir", work)


if __name__ == "__main__":
    main()
