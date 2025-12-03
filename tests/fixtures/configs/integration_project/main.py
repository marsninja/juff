# main.py - should trigger various rules based on config

import os  # F401: unused import (should be reported unless ignored)

def example_function(a,b,c,d,e,f,g):  # E501: line might be long, PLR0913: too many args
    x=1  # E225: missing whitespace
    unused_var = 2  # F841: unused variable
    return a + b

# Long line that exceeds 80 chars but maybe not 100 chars - this line is exactly 85 characters!
