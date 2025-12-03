# Fixture file that intentionally breaks many different lint rules
# This file is used to test rule selection detection
# fmt: off
# type: ignore
# noqa: CPY001 (no copyright header)

# ===== F: pyflakes =====
import os  # F401: unused import
import sys  # F401: unused import (but sys.exit used below)
import json  # F401: unused import
from typing import List, Dict  # UP006: use list, dict instead of List, Dict

# ===== I: isort - unsorted imports =====
import re
import ast

# ===== E: pycodestyle errors =====
# E501: line too long - this is a very long line that exceeds the typical 88 character limit set by most formatters and linters
x=1  # E225: missing whitespace around operator

# ===== W: pycodestyle warnings =====
y = 2   # W291: trailing whitespace (there are spaces after the 2)


# W293: blank line contains whitespace (the line above has spaces)

def bad_function(a,b,c):  # E231: missing whitespace after ','
    """Function with many issues."""
    # F841: unused variable
    unused_var = 42

    # ===== S: flake8-bandit (security) =====
    # S101: use of assert (security issue in production)
    assert a is not None

    # ===== T20: flake8-print =====
    # T201: print statement
    print("debugging")

    # ===== SIM: flake8-simplify =====
    # SIM102: nested if can be collapsed
    if a:
        if b:
            pass

    # SIM108: use ternary instead of if-else
    if c:
        result = 1
    else:
        result = 2

    # ===== C4: flake8-comprehensions =====
    # C411: unnecessary list call around list comprehension
    values = list([x for x in range(10)])

    # ===== RET: flake8-return =====
    # RET504: unnecessary assignment before return
    final_result = a + b
    return final_result


# ===== B: flake8-bugbear =====
# B006: mutable default argument
def bad_defaults(items=[]):
    """Function with mutable default."""
    items.append(1)
    return items


# ===== ANN: flake8-annotations =====
# ANN001: missing type annotation for argument
# ANN201: missing return type annotation
def no_type_hints(x, y):
    """Function without type hints."""
    return x + y


# ===== N: pep8-naming =====
class BadClass:
    """Class with issues."""

    def __init__(self,value):  # E231: missing whitespace
        self.value=value  # E225: missing whitespace around operator

    # N802: function name should be lowercase (camelCase used)
    def getValue(self):
        return self.value

    # ===== ARG: flake8-unused-arguments =====
    # ARG002: unused method argument
    def method_with_unused_arg(self, unused):
        """Method that doesn't use its argument."""
        return self.value

    # ===== SLF: flake8-self =====
    def access_private(self, other):
        # SLF001: private member accessed
        return other._private_value


# E302: expected 2 blank lines
def another_function():
    pass


# ===== DTZ: flake8-datetimez =====
# DTZ005: datetime.now() without timezone
from datetime import datetime
now = datetime.now()


# ===== EM: flake8-errmsg =====
# EM101: raw string in exception
def raises_with_raw_string():
    raise ValueError("This is a raw string error message")


# ===== TRY: tryceratops =====
# TRY003: avoid specifying long messages outside exception class
def long_exception():
    raise ValueError(
        "This is a very long error message that should be defined as a constant or in an exception class"
    )


# ===== PTH: flake8-use-pathlib =====
# PTH109: use Path.cwd() instead of os.getcwd
current_dir = os.getcwd()


# ===== PERF: perflint =====
# PERF401: use list comprehension instead of manual append
def slow_loop():
    result = []
    for i in range(10):
        result.append(i * 2)
    return result


# ===== PIE: flake8-pie =====
# PIE790: unnecessary pass
class EmptyClass:
    """Empty class."""
    pass


# ===== FBT: flake8-boolean-trap =====
# FBT001: boolean positional argument
def boolean_trap(flag: bool):
    """Boolean trap function."""
    if flag:
        return "yes"
    return "no"


# ===== ERA: flake8-eradicate =====
# ERA001: commented out code
# def old_function():
#     return "old"


# ===== BLE: flake8-blind-except =====
# BLE001: blind except
def blind_except():
    try:
        risky_operation = 1 / 0
    except:
        pass


# E711: comparison to None
def none_comparison(x):
    if x == None:
        return True
    return False


# E712: comparison to True
def bool_comparison(x):
    if x == True:
        return "yes"
    return "no"


# W503/W504: line break before/after binary operator
result = (1
    + 2
    + 3)


# ===== Q: flake8-quotes =====
# Q000: single quotes (depending on config)
single_quoted = 'single quotes'


# ===== COM: flake8-commas =====
# COM812: trailing comma missing
data = {
    "key1": "value1",
    "key2": "value2"
}


# ===== UP: pyupgrade =====
# UP007: use X | None instead of Union[X, None]
from typing import Union
OptionalInt = Union[int, None]


# ===== A: flake8-builtins =====
# A001: shadowing builtin
list = [1, 2, 3]


# ===== ISC: flake8-implicit-str-concat =====
# ISC001: implicitly concatenated string
long_string = (
    "first part"
    "second part"
)


# ===== G: flake8-logging-format =====
# G004: logging with f-string
import logging
logger = logging.getLogger(__name__)
def log_with_fstring(x):
    logger.info(f"Value: {x}")


# ===== RUF: ruff-specific =====
# RUF005: consider unpacking instead of concatenation
combined = [1, 2] + [3, 4]


# ===== T10: flake8-debugger =====
# T100: debugger statement
def has_debugger():
    breakpoint()  # T100: debugger call
    return True


# ===== C90: mccabe complexity =====
# C901: function is too complex
def complex_function(a, b, c, d, e, f, g, h):
    """Function with high cyclomatic complexity."""
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
                    else:
                        return 2
                else:
                    return 3
            else:
                return 4
        else:
            return 5
    elif f:
        if g:
            return 6
        elif h:
            return 7
        else:
            return 8
    else:
        return 9


# ===== D: flake8-docstrings (pydocstyle) =====
# D100: missing docstring in public module (this module has it at top)
# D103: missing docstring in public function
def no_docstring():
    return 42


# ===== FIX: flake8-fixme =====
# FIX001: contains FIXME
# FIXME: this needs to be fixed later
def todo_function():
    # TODO: implement this properly
    pass


# ===== TD: flake8-todos =====
# TD001: invalid TODO tag format
# TD002: missing author in TODO
# todo: lowercase todo


# ===== TCH: flake8-type-checking =====
# TCH001: move import into TYPE_CHECKING block
from typing import TYPE_CHECKING
from pathlib import Path  # TCH003: should be in TYPE_CHECKING block if only used for annotations
def uses_path_annotation(p: Path) -> None:
    pass


# ===== RSE: flake8-raise =====
# RSE102: unnecessary parentheses on raised exception
def raises_with_parens():
    raise ValueError()


# ===== YTT: flake8-2020 =====
# YTT101: sys.version[:3] comparison
import sys
if sys.version[:3] == "3.1":  # YTT101
    pass


# ===== TID: flake8-tidy-imports =====
# TID252: relative imports are banned (depending on config)
# from . import sibling  # Would trigger TID252


# ===== LOG: flake8-logging =====
# LOG001: use logging.getLogger() not logging.Logger()
bad_logger = logging.Logger("bad")


# ===== INP: flake8-no-pep420 =====
# INP001: implicit namespace package (missing __init__.py)
# This is checked at directory level, not file level


# ===== PYI: flake8-pyi =====
# PYI rules only apply to .pyi stub files


# ===== EXE: flake8-executable =====
# EXE001: shebang present but file not executable
# #!/usr/bin/env python  # Would trigger if uncommented


# ===== ASYNC: flake8-async =====
# ASYNC100: async function without await
async def async_no_await():
    return 42


# ===== FA: flake8-future-annotations =====
# FA100: missing from __future__ import annotations
# (We intentionally don't have it at the top)


# ===== ICN: flake8-import-conventions =====
# ICN001: unconventional import alias
import numpy as npy  # Should be `np` not `npy`


# ===== PD: pandas-vet =====
# PD002: inplace=True should be avoided
# import pandas as pd
# df.drop(columns=['a'], inplace=True)  # Would trigger PD002


# ===== SLOT: flake8-slots =====
# SLOT000: subclass of str without __slots__
class MyStr(str):
    pass


# ===== PLW: pylint warnings =====
# PLW0120: else clause on loop without break
def loop_with_else():
    for i in range(10):
        pass
    else:
        return True


# ===== PLC: pylint convention =====
# PLC0414: useless import alias
import os as os  # PLC0414


# ===== PLE: pylint error =====
# PLE0101: return in __init__
class BadInit:
    def __init__(self):
        return None  # PLE0101


# ===== PLR: pylint refactor =====
# PLR0913: too many arguments
def too_many_args(a, b, c, d, e, f, g, h, i, j):
    return a + b + c + d + e + f + g + h + i + j


# ===== FURB: refurb =====
# FURB118: use operator.itemgetter
items = [(1, 'a'), (2, 'b')]
sorted_items = sorted(items, key=lambda x: x[0])  # FURB118


# ===== DOC: pydoclint =====
# DOC201: return value not documented
def returns_without_doc(x: int) -> int:
    """Does something.

    Args:
        x: Input value.
    """
    return x * 2


# ===== FLY: flynt =====
# FLY002: use f-string instead of format
name = "world"
greeting = "Hello, {}".format(name)  # FLY002


# ===== NPY: numpy rules (ruff-only) =====
# NPY001: deprecated numpy type alias
# import numpy as np
# x: np.int  # Would trigger NPY001


# ===== PGH: pygrep-hooks (ruff-only) =====
# PGH001: no eval
eval("1 + 1")  # PGH001


# ===== AIR: Airflow rules (ruff-only) =====
# AIR rules are specific to Airflow DAGs


# ===== FAST: FastAPI rules (ruff-only) =====
# FAST rules are specific to FastAPI apps


# ===== INT: flake8-gettext =====
# INT001: format string in gettext call
# _("Hello %s") % name  # Would trigger INT001


if __name__ == "__main__":
    bad_function(1, 2, 3)
    sys.exit(0)
