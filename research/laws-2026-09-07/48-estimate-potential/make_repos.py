#!/usr/bin/env python3
"""Construct 12 small public-style repos under ./repos/ for `fluidfix estimate`.

Each repo is the smallest thing that still has the SHAPE of a real project a
prospective customer would point `fluidfix estimate` at. Nothing here is
generated at random; every shape is one that exists in the wild and is named
in the comment above it.

Rerun:  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python make_repos.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "repos")


def w(repo, rel, text):
    p = os.path.join(ROOT, repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def build():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(ROOT)

    # 01 the happy path: flat python package, pytest tests, suite green.
    w("01-py-flat-green", "calc.py",
      "def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n")
    w("01-py-flat-green", "test_calc.py",
      "from calc import add, mul\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\n"
      "def test_mul():\n    assert mul(2, 3) == 6\n")

    # 02 the same repo with one real regression (a red suite: fluidfix's
    #    actual working condition).
    w("02-py-flat-red", "calc.py",
      "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n")
    w("02-py-flat-red", "test_calc.py",
      "from calc import add, mul\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\n"
      "def test_mul():\n    assert mul(2, 3) == 6\n")

    # 03 src/ layout with a pyproject — the modern packaging default. The
    #    package is NOT installed, so the tests cannot import it.
    w("03-py-src-layout-uninstalled", "pyproject.toml",
      '[project]\nname = "widget"\nversion = "0.1.0"\n\n'
      '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n')
    w("03-py-src-layout-uninstalled", "src/widget/__init__.py", "from .core import scale\n")
    w("03-py-src-layout-uninstalled", "src/widget/core.py",
      "def scale(v, k):\n    return v * k\n")
    w("03-py-src-layout-uninstalled", "tests/test_core.py",
      "from widget import scale\n\n\ndef test_scale():\n    assert scale(2, 3) == 6\n")

    # 04 a library with no tests at all (the zero-tests on-ramp case that
    #    `fluidfix init` exists for).
    w("04-py-no-tests", "README.md", "# tinylib\n\nA tiny library.\n")
    w("04-py-no-tests", "tinylib.py", "def norm(s):\n    return s.strip().lower()\n")

    # 05 tests exist but do not match pytest's default python_files globs
    #    (unittest-era layout: `runtests.py` / `alltests.py`).
    w("05-py-unittest-nonglob", "shape.py",
      "def area(w, h):\n    return w * h\n")
    w("05-py-unittest-nonglob", "alltests.py",
      "import unittest\n\nfrom shape import area\n\n\n"
      "class AreaTests(unittest.TestCase):\n"
      "    def test_area(self):\n        self.assertEqual(area(2, 3), 6)\n\n\n"
      "if __name__ == '__main__':\n    unittest.main()\n")

    # 06 every test is skipped at collection (platform / optional-dependency
    #    gating: extremely common in cross-platform projects).
    w("06-py-all-skipped", "plat.py", "def sep():\n    return '/'\n")
    w("06-py-all-skipped", "test_plat.py",
      "import pytest\n\npytest.importorskip('numpy')\n\nfrom plat import sep\n\n\n"
      "def test_sep():\n    assert sep() == '/'\n")

    # 07 pytest configuration the interpreter cannot satisfy: an addopts
    #    referencing a plugin that is not installed (a usage error).
    w("07-py-bad-addopts", "pytest.ini",
      "[pytest]\naddopts = --cov=thing --cov-report=term --strict-markers "
      "--nonexistent-option\n")
    w("07-py-bad-addopts", "thing.py", "def one():\n    return 1\n")
    w("07-py-bad-addopts", "test_thing.py",
      "from thing import one\n\n\ndef test_one():\n    assert one() == 1\n")

    # 08 a suite slower than the default budget is exercised with a small
    #    --suite-timeout: the "your suite does not finish" lane.
    w("08-py-slow-suite", "slow.py", "def go():\n    return 42\n")
    w("08-py-slow-suite", "test_slow.py",
      "import time\n\nfrom slow import go\n\n\n"
      "def test_go():\n    time.sleep(20)\n    assert go() == 42\n")

    # 09 a JavaScript project (package.json + jest-style tests). A large
    #    share of public repos look like this.
    w("09-js-node", "package.json",
      '{\n  "name": "strutil",\n  "version": "1.0.0",\n'
      '  "scripts": {"test": "jest"}\n}\n')
    w("09-js-node", "src/strutil.js",
      "function slugify(s) {\n  return s.trim().toLowerCase();\n}\n"
      "module.exports = { slugify };\n")
    w("09-js-node", "test/strutil.test.js",
      "const { slugify } = require('../src/strutil');\n"
      "test('slugify', () => { expect(slugify(' Hi ')).toBe('hi'); });\n")

    # 10 a C/CMake project with a ctest suite — the shape `fluidfix cguard`
    #    is written for.
    w("10-c-cmake", "CMakeLists.txt",
      "cmake_minimum_required(VERSION 3.10)\nproject(vec C)\n"
      "add_library(vec vec.c)\nenable_testing()\n"
      "add_executable(test_vec test_vec.c)\ntarget_link_libraries(test_vec vec)\n"
      "add_test(NAME test_vec COMMAND test_vec)\n")
    w("10-c-cmake", "vec.c",
      "#include \"vec.h\"\nfloat vec_dot(float a[2], float b[2]) {\n"
      "    return a[0] * b[0] + a[1] * b[1];\n}\n")
    w("10-c-cmake", "vec.h", "float vec_dot(float a[2], float b[2]);\n")
    w("10-c-cmake", "test_vec.c",
      "#include <stdio.h>\n#include \"vec.h\"\nint main(void) {\n"
      "    float a[2] = {1, 2}, b[2] = {3, 4};\n"
      "    if (vec_dot(a, b) != 11.0f) { printf(\"test failed\\n\"); return 1; }\n"
      "    return 0;\n}\n")

    # 11 a Java/Maven project with JUnit — the shape `fluidfix jguard` is
    #    written for.
    w("11-java-maven", "pom.xml",
      '<project><modelVersion>4.0.0</modelVersion>\n'
      '<groupId>demo</groupId><artifactId>calc</artifactId><version>1.0</version>\n'
      '<dependencies><dependency><groupId>org.junit.jupiter</groupId>'
      '<artifactId>junit-jupiter</artifactId><version>5.10.0</version>'
      '<scope>test</scope></dependency></dependencies></project>\n')
    w("11-java-maven", "src/main/java/demo/Calc.java",
      "package demo;\npublic class Calc {\n"
      "    public static int add(int a, int b) { return a + b; }\n}\n")
    w("11-java-maven", "src/test/java/demo/CalcTest.java",
      "package demo;\nimport org.junit.jupiter.api.Test;\n"
      "import static org.junit.jupiter.api.Assertions.assertEquals;\n"
      "public class CalcTest {\n"
      "    @Test public void testAdd() { assertEquals(5, Calc.add(2, 3)); }\n}\n")

    # 12 a realistic mid-size python package: 6 modules, 40 tests, a
    #    conftest, a tests/ subpackage. The shape most paying customers have.
    w("12-py-midsize", "pyproject.toml",
      '[project]\nname = "ledger"\nversion = "0.3.0"\n')
    w("12-py-midsize", "ledger/__init__.py", "")
    for mod, body in (
        ("money", "def cents(x):\n    return int(round(x * 100))\n\n\n"
                  "def dollars(c):\n    return c / 100.0\n"),
        ("tax", "def vat(amount, rate=0.2):\n    return amount * rate\n"),
        ("fmt", "def money(c):\n    return f'${c / 100:.2f}'\n"),
        ("acct", "class Account:\n    def __init__(self):\n        self.bal = 0\n\n"
                 "    def credit(self, c):\n        self.bal += c\n        return self.bal\n\n"
                 "    def debit(self, c):\n        self.bal -= c\n        return self.bal\n"),
        ("rules", "def approves(bal, amt):\n    return bal >= amt\n"),
        ("report", "def total(rows):\n    return sum(r for r in rows)\n"),
    ):
        w("12-py-midsize", f"ledger/{mod}.py", body)
    w("12-py-midsize", "tests/conftest.py",
      "import os\nimport sys\n\nsys.path.insert(0, os.path.dirname("
      "os.path.dirname(os.path.abspath(__file__))))\n")
    w("12-py-midsize", "tests/test_money.py",
      "import pytest\n\nfrom ledger.money import cents, dollars\n\n\n"
      "@pytest.mark.parametrize('x,c', [(1.0, 100), (0.01, 1), (12.34, 1234),"
      " (0.0, 0), (99.99, 9999), (5.5, 550), (0.005, 1), (100.0, 10000)])\n"
      "def test_cents(x, c):\n    assert cents(x) == c\n\n\n"
      "@pytest.mark.parametrize('c,x', [(100, 1.0), (1, 0.01), (0, 0.0),"
      " (2550, 25.5), (9999, 99.99)])\n"
      "def test_dollars(c, x):\n    assert dollars(c) == x\n")
    w("12-py-midsize", "tests/test_tax.py",
      "import pytest\n\nfrom ledger.tax import vat\n\n\n"
      "@pytest.mark.parametrize('a,r,e', [(100, 0.2, 20.0), (50, 0.1, 5.0),"
      " (0, 0.2, 0.0), (10, 0.5, 5.0), (200, 0.25, 50.0)])\n"
      "def test_vat(a, r, e):\n    assert vat(a, r) == pytest.approx(e)\n")
    w("12-py-midsize", "tests/test_fmt.py",
      "import pytest\n\nfrom ledger.fmt import money\n\n\n"
      "@pytest.mark.parametrize('c,s', [(100, '$1.00'), (0, '$0.00'),"
      " (1234, '$12.34'), (5, '$0.05'), (999999, '$9999.99')])\n"
      "def test_money(c, s):\n    assert money(c) == s\n")
    w("12-py-midsize", "tests/test_acct.py",
      "import pytest\n\nfrom ledger.acct import Account\n\n\n"
      "@pytest.mark.parametrize('amts,end', [([100], 100), ([100, 50], 150),"
      " ([], 0), ([1, 2, 3, 4], 10), ([500, 500], 1000)])\n"
      "def test_credit(amts, end):\n    a = Account()\n"
      "    for m in amts:\n        a.credit(m)\n    assert a.bal == end\n\n\n"
      "@pytest.mark.parametrize('c,d,e', [(100, 40, 60), (0, 10, -10),"
      " (50, 50, 0), (10, 0, 10), (1000, 999, 1)])\n"
      "def test_debit(c, d, e):\n    a = Account()\n    a.credit(c)\n"
      "    a.debit(d)\n    assert a.bal == e\n")
    w("12-py-midsize", "tests/test_rules.py",
      "import pytest\n\nfrom ledger.rules import approves\n\n\n"
      "@pytest.mark.parametrize('b,a,ok', [(100, 50, True), (50, 100, False),"
      " (0, 0, True), (10, 10, True), (9, 10, False)])\n"
      "def test_approves(b, a, ok):\n    assert approves(b, a) is ok\n")
    w("12-py-midsize", "tests/test_report.py",
      "import pytest\n\nfrom ledger.report import total\n\n\n"
      "@pytest.mark.parametrize('rows,e', [([1, 2, 3], 6), ([], 0), ([5], 5),"
      " ([-1, 1], 0), ([10] * 10, 100)])\n"
      "def test_total(rows, e):\n    assert total(rows) == e\n")

    # 13 tests collect but every one is skipped at RUN time (a licence-gated
    #    or hardware-gated suite). pytest exits 0 with no passed/failed line.
    w("13-py-all-skipped-runtime", "gpu.py", "def devices():\n    return []\n")
    w("13-py-all-skipped-runtime", "test_gpu.py",
      "import pytest\n\nfrom gpu import devices\n\n\n"
      "@pytest.mark.skip(reason='no GPU on this runner')\n"
      "def test_devices():\n    assert devices() == []\n")

    # 14 is repo 01 pointed at an interpreter that has no pytest — the
    #    `estimate .` default for anyone who installed fluidfix with pipx.
    #    (no files; see run list)

    # 15 a Go module with `go test` tests.
    w("15-go-module", "go.mod", "module example.com/strs\n\ngo 1.22\n")
    w("15-go-module", "strs.go",
      "package strs\n\nfunc Reverse(s string) string {\n"
      "\tr := []rune(s)\n"
      "\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n"
      "\t\tr[i], r[j] = r[j], r[i]\n\t}\n\treturn string(r)\n}\n")
    w("15-go-module", "strs_test.go",
      "package strs\n\nimport \"testing\"\n\n"
      "func TestReverse(t *testing.T) {\n"
      "\tif Reverse(\"ab\") != \"ba\" { t.Fatal(\"bad\") }\n}\n")

    # 16 a Rust crate with `cargo test` tests.
    w("16-rust-crate", "Cargo.toml",
      '[package]\nname = "adder"\nversion = "0.1.0"\nedition = "2021"\n')
    w("16-rust-crate", "src/lib.rs",
      "pub fn add(a: i32, b: i32) -> i32 { a + b }\n\n"
      "#[cfg(test)]\nmod tests {\n    use super::*;\n"
      "    #[test]\n    fn it_adds() { assert_eq!(add(2, 3), 5); }\n}\n")

    names = sorted(os.listdir(ROOT))
    for n in names:
        nf = sum(len(f) for _, _, f in os.walk(os.path.join(ROOT, n)))
        print(f"{n:34s} {nf:3d} files")
    print(f"\n{len(names)} repos under {ROOT}")


if __name__ == "__main__":
    sys.exit(build())
