# File with old Python syntax (pyupgrade)
from typing import Optional, List, Dict, Tuple

def old_style_typing(x: List[int]) -> Dict[str, Tuple[int, int]]:
    """Function with old-style type hints."""
    result: Dict[str, Tuple[int, int]] = {}
    for i in x:
        result[str(i)] = (i, i * 2)
    return result

# Old style string formatting
name = "world"
greeting = "Hello, %s!" % name
greeting2 = "Hello, {}!".format(name)

# Old style super()
class Parent:
    def greet(self):
        return "Hello"

class Child(Parent):
    def greet(self):
        return super(Child, self).greet() + " from child"
