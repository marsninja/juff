"""Pytest fixtures for Juff tests."""

import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_toml(temp_dir):
    """Create a sample juff.toml config file."""
    config_content = """
line-length = 100
target-version = "py310"
exclude = [".git", "__pycache__"]

[lint]
select = ["E", "F", "W", "B"]
ignore = ["E501"]
fixable = ["ALL"]
unfixable = ["B"]

[format]
quote-style = "double"
"""
    config_path = temp_dir / "juff.toml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_pyproject_toml(temp_dir):
    """Create a sample pyproject.toml with [tool.juff] section."""
    config_content = """
[tool.poetry]
name = "test-project"
version = "0.1.0"

[tool.juff]
line-length = 120
target-version = "py311"

[tool.juff.lint]
select = ["E", "F"]
ignore = ["E203"]
"""
    config_path = temp_dir / "pyproject.toml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    code = '''
import os
import sys
import unused_import

def hello_world():
    x = 1
    y = 2
    return x+y

class MyClass:
    def __init__(self):
        pass
'''
    file_path = temp_dir / "sample.py"
    file_path.write_text(code)
    return file_path
