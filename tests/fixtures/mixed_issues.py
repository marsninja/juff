# File with multiple types of issues
import sys
import os  # unsorted
import json  # unused
from typing import List  # old style typing

def bad_function(x,y):  # needs formatting
    unused_var = 42  # F841 unused variable
    return x+y

class BadClass:
    def __init__(self,value):
        self.value=value

    def method( self ):  # E211 whitespace
        return self.value
