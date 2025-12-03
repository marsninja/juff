# migrations/001_initial.py - should be excluded from lint per comprehensive.toml extend-exclude
# This file has intentional violations that should NOT be reported if exclude works

import os
import sys
import json  # F401: unused imports

def very_long_function_name_that_creates_a_line_exceeding_any_reasonable_line_length_limit():  # E501
    x=1  # E225
    pass
