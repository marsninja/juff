# File with old Python syntax (pyupgrade)
from typing import Optional, List, Dict, Tuple

def old_style_typing(x: list[int]) -> dict[str, tuple[int, int]]:
    """Function with old-style type hints."""
    result: dict[str, tuple[int, int]] = {}
    for i in x:
        result[str(i)] = (i, i * 2)
    return result

# Old style string formatting
name = "world"
greeting = "Hello, %s!" % name
greeting2 = f"Hello, {name}!"

# Old style super()
class Parent:
    def greet(self):
        return "Hello"

class Child(Parent):
    def greet(self):
        return super().greet() + " from child"
