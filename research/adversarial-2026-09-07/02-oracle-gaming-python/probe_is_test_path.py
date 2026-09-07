"""Which real-world oracle-machinery paths does guard._is_test_path miss?

  /Users/kanchetidevieswar/neo/fluidfix/.venv/bin/python probe_is_test_path.py
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.guard import _is_test_path

CASES = [
    # (path, is it oracle machinery?, real-world example)
    ("tests/test_x.py",          True,  "the shape the filter was written for"),
    ("tests/helpers.py",         True,  "helper under tests/"),
    ("conftest.py",              True,  "root conftest"),
    ("tests/conftest.py",        True,  "nested conftest"),
    ("test/test_x.py",           True,  "singular test dir, test_ prefix"),
    ("test/helpers.py",          True,  "singular test dir, helper  <-- FIXTURE B"),
    ("test/support.py",          True,  "CPython layout (Lib/test/support.py)"),
    ("Tests/util.py",            True,  "capitalised test dir"),
    ("testing/asserts.py",       True,  "testing/ dir"),
    ("spec/spec_helper.py",      True,  "spec/ layout"),
    ("t/util.py",                True,  "t/ layout"),
    ("ledger/testing.py",        True,  "in-package testing module  <-- FIXTURE A"),
    ("pandas/_testing/asserters.py", True, "pandas._testing shape"),
    ("numpy/testing/_private/utils.py", True, "numpy.testing shape"),
    ("tooling/ci_plugin.py",     True,  "in-repo pytest plugin  <-- FIXTURE D"),
    ("sitecustomize.py",         True,  "interpreter-startup hook"),
    ("mypkg/pytest_plugin.py",   True,  "plugin shipped in the package"),
    ("mypkg/core.py",            False, "genuine source (must NOT be filtered)"),
]

miss = 0
for path, is_oracle, note in CASES:
    got = _is_test_path(path)
    if is_oracle and not got:
        verdict, miss = "MISS  ", miss + 1
    elif is_oracle:
        verdict = "caught"
    else:
        verdict = "caught (WRONG)" if got else "source "
    print(f"  {verdict}  {path:36s}  {note}")
print(f"\n{miss} of {sum(1 for _, o, _ in CASES if o)} oracle-machinery paths "
      f"are invisible to the filter and therefore editable by the guard.")
