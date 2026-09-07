#!/usr/bin/env python
"""Measure guard._is_test_path against real-world test-file layouts.

_is_test_path is the ONLY thing that keeps fluidfix's candidate set from
containing the project's own oracle.  oracle.py:97-105 says so in words:
"Python is less exposed (`_is_test_path` keeps test files out of the
candidate set)".  coracle.py imports the SAME function and applies it to
C/C++ trees (coracle.py:441, 714, 732).

Each row is a path spelling that occurs in a real project layout.  We ask:
does the whitelist recognise it as a test path?
"""
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.guard import _is_test_path                       # noqa: E402

# (path, is-really-a-test-file, where this spelling is seen)
CASES = [
    # --- the four spellings the whitelist knows ------------------------
    ("tests/test_foo.py",            True,  "pytest default"),
    ("src/foo_test.py",              True,  "google python style"),
    ("tests/helpers.py",             True,  "dir named `tests`"),
    ("conftest.py",                  True,  "pytest conftest"),
    # --- spellings it does not know -----------------------------------
    ("test/foo.py",                  True,  "dir named `test` (singular)"),
    ("testing/foo.py",               True,  "django/numpy `testing`"),
    ("spec/foo_spec.py",             True,  "rspec-style"),
    ("t/harness.py",                 True,  "perl-ish `t/`"),
    ("unit_tests/runner.py",         True,  "coracle.py:125 knows this one"),
    ("check/main.c",                 True,  "coracle.py:125 knows this one"),
    ("src/test_util.c",              False, "C: test_ prefix, .c not .py"),
    ("test/joint_test.c",            True,  "Box2D-shaped C test"),
    ("test/main.c",                  True,  "cglm-shaped C test"),
    ("unit/vec3_test.c",             True,  "C `_test.c` suffix"),
    ("src/main_test.go",             True,  "go convention"),
    ("Tests/FooTests.py",            True,  "capitalised `Tests` dir"),
    ("src/tests_helper.py",          True,  "prefix `tests_`"),
]

if __name__ == "__main__":
    esc = 0
    print(f"{'path':<28} {'really a test?':<15} {'whitelisted?':<13} verdict")
    for p, truth, note in CASES:
        got = _is_test_path(p)
        v = "ok" if got == truth else ("ESCAPES" if truth else "over-broad")
        if v == "ESCAPES":
            esc += 1
        print(f"{p:<28} {str(truth):<15} {str(got):<13} {v:<11} {note}")
    print(f"\n{esc} of {len(CASES)} layouts are real test files that ESCAPE "
          f"the whitelist")
    # exactly which of the four clauses fired, per spelling
    print("\nthe four clauses, verbatim (guard.py:114-115):")
    print('  base.startswith("test_") | base.endswith("_test.py") '
          '| "tests" in parts[:-1] | base == "conftest.py"')
