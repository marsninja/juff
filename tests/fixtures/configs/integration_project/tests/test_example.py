# tests/test_example.py - per-file-ignores should suppress S101 here

import pytest


def test_something():
    assert True  # S101: use of assert (should be ignored in tests)
    assert 1 == 1  # S101: another assert


def test_another():
    x = 1
    assert x > 0  # S101: yet another assert
