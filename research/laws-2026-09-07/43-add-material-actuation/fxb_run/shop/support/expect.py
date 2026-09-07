"""Assertion helpers shared by the whole suite."""


def expect_equal(got, want):
    assert got == want


def expect_true(got):
    assert got


def expect_close(got, want, tol=1e-9):
    assert abs(got - want) <= tol


def expect_ge(got, want):
    assert got <= want
