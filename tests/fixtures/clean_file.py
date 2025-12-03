"""A clean Python file with no issues."""

import os
from pathlib import Path


def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def main() -> None:
    """Main entry point."""
    cwd = Path.cwd()
    print(greet("World"))
    print(f"Current directory: {cwd}")


if __name__ == "__main__":
    main()
