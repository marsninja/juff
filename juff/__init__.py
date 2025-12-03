"""Juff - A faithful Python-first drop-in replacement for ruff.

Juff uses the original visionary Python tools (flake8, black, pyupgrade, isort, etc.)
by managing them in a dedicated virtual environment, providing a faithful Python-first
implementation rather than reimplementing their functionality.
"""

__version__ = "0.1.0"

from juff.venv_manager import JuffVenvManager

__all__ = ["__version__", "JuffVenvManager"]
