"""Tests for Juff tool wrappers."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from juff.config import JuffConfig
from juff.tools.base import BaseTool, ToolResult
from juff.tools.flake8 import Flake8Tool, AutoflakeTool
from juff.tools.black import BlackTool
from juff.tools.isort import IsortTool
from juff.tools.pyupgrade import PyupgradeTool


class TestToolResult:
    """Tests for ToolResult class."""

    def test_success_when_returncode_zero(self):
        """Test success property when returncode is 0."""
        result = ToolResult(
            tool_name="test",
            returncode=0,
            stdout="",
            stderr="",
        )
        assert result.success is True

    def test_not_success_when_returncode_nonzero(self):
        """Test success property when returncode is non-zero."""
        result = ToolResult(
            tool_name="test",
            returncode=1,
            stdout="",
            stderr="",
        )
        assert result.success is False

    def test_repr(self):
        """Test string representation."""
        result = ToolResult(
            tool_name="flake8",
            returncode=1,
            stdout="",
            stderr="",
            issues_found=5,
            issues_fixed=2,
        )
        repr_str = repr(result)
        assert "flake8" in repr_str
        assert "rc=1" in repr_str
        assert "issues=5" in repr_str
        assert "fixed=2" in repr_str


class TestFlake8Tool:
    """Tests for Flake8Tool."""

    @pytest.fixture
    def mock_venv_manager(self):
        """Create a mock venv manager."""
        return MagicMock()

    @pytest.fixture
    def flake8_tool(self, mock_venv_manager):
        """Create a Flake8Tool instance."""
        config = JuffConfig()
        config._config = {
            "line-length": 100,
            "lint": {
                "select": ["E", "F", "W"],
                "ignore": ["E501"],
            },
            "exclude": [".git", "__pycache__"],
        }
        return Flake8Tool(mock_venv_manager, config)

    def test_name(self, flake8_tool):
        """Test tool name."""
        assert flake8_tool.name == "flake8"

    def test_build_args_basic(self, flake8_tool):
        """Test basic argument building."""
        paths = [Path("src/")]
        args = flake8_tool.build_args(paths)

        assert "--max-line-length" in args
        assert "100" in args
        # Path gets converted to string in args
        assert any("src" in str(arg) for arg in args)

    def test_build_args_with_select(self, flake8_tool):
        """Test argument building with select rules."""
        paths = [Path(".")]
        args = flake8_tool.build_args(paths)

        assert "--select" in args

    def test_build_args_with_ignore(self, flake8_tool):
        """Test argument building with ignore rules."""
        paths = [Path(".")]
        args = flake8_tool.build_args(paths)

        assert "--ignore" in args
        # E501 should be in the ignore list
        ignore_idx = args.index("--ignore")
        assert "E501" in args[ignore_idx + 1]

    def test_build_args_with_exclude(self, flake8_tool):
        """Test argument building with exclude patterns."""
        paths = [Path(".")]
        args = flake8_tool.build_args(paths)

        assert "--exclude" in args

    def test_build_args_extra_args(self, flake8_tool):
        """Test argument building with extra args."""
        paths = [Path(".")]
        args = flake8_tool.build_args(paths, extra_args=["--show-source"])

        assert "--show-source" in args

    def test_parse_output_counts_issues(self, flake8_tool):
        """Test parsing flake8 output for issue counts."""
        stdout = """src/main.py:10:1: E302 expected 2 blank lines, found 1
src/main.py:15:80: E501 line too long (85 > 79 characters)
src/utils.py:5:1: F401 'os' imported but unused
"""
        issues_found, issues_fixed = flake8_tool.parse_output(stdout, "")

        assert issues_found == 3
        assert issues_fixed == 0  # flake8 doesn't fix


class TestBlackTool:
    """Tests for BlackTool."""

    @pytest.fixture
    def mock_venv_manager(self):
        """Create a mock venv manager."""
        return MagicMock()

    @pytest.fixture
    def black_tool(self, mock_venv_manager):
        """Create a BlackTool instance."""
        config = JuffConfig()
        config._config = {
            "line-length": 88,
            "target-version": "py311",
        }
        return BlackTool(mock_venv_manager, config)

    def test_name(self, black_tool):
        """Test tool name."""
        assert black_tool.name == "black"

    def test_build_args_check_mode(self, black_tool):
        """Test argument building in check mode."""
        paths = [Path("src/")]
        args = black_tool.build_args(paths, fix=False)

        assert "--check" in args
        assert "--diff" in args

    def test_build_args_fix_mode(self, black_tool):
        """Test argument building in fix mode."""
        paths = [Path("src/")]
        args = black_tool.build_args(paths, fix=True)

        assert "--check" not in args

    def test_build_args_line_length(self, black_tool):
        """Test line length argument."""
        paths = [Path(".")]
        args = black_tool.build_args(paths)

        assert "--line-length" in args
        assert "88" in args

    def test_parse_output_would_reformat(self, black_tool):
        """Test parsing output with 'would reformat'."""
        stdout = ""
        stderr = "would reformat src/main.py\nwould reformat src/utils.py\n"

        issues_found, issues_fixed = black_tool.parse_output(stdout, stderr)

        assert issues_found == 2
        assert issues_fixed == 0

    def test_parse_output_reformatted(self, black_tool):
        """Test parsing output with 'reformatted'."""
        stdout = ""
        stderr = "reformatted src/main.py\nreformatted src/utils.py\n"

        issues_found, issues_fixed = black_tool.parse_output(stdout, stderr)

        assert issues_found == 2
        assert issues_fixed == 2


class TestIsortTool:
    """Tests for IsortTool."""

    @pytest.fixture
    def mock_venv_manager(self):
        """Create a mock venv manager."""
        return MagicMock()

    @pytest.fixture
    def isort_tool(self, mock_venv_manager):
        """Create an IsortTool instance."""
        config = JuffConfig()
        config._config = {"line-length": 88}
        return IsortTool(mock_venv_manager, config)

    def test_name(self, isort_tool):
        """Test tool name."""
        assert isort_tool.name == "isort"

    def test_build_args_check_mode(self, isort_tool):
        """Test argument building in check mode."""
        paths = [Path("src/")]
        args = isort_tool.build_args(paths, fix=False)

        assert "--check-only" in args
        assert "--diff" in args

    def test_build_args_fix_mode(self, isort_tool):
        """Test argument building in fix mode."""
        paths = [Path("src/")]
        args = isort_tool.build_args(paths, fix=True)

        assert "--check-only" not in args

    def test_build_args_black_profile(self, isort_tool):
        """Test that black profile is used by default."""
        paths = [Path(".")]
        args = isort_tool.build_args(paths)

        assert "--profile=black" in args


class TestPyupgradeTool:
    """Tests for PyupgradeTool."""

    @pytest.fixture
    def mock_venv_manager(self):
        """Create a mock venv manager."""
        return MagicMock()

    @pytest.fixture
    def pyupgrade_tool(self, mock_venv_manager):
        """Create a PyupgradeTool instance."""
        config = JuffConfig()
        config._config = {"target-version": "py310"}
        return PyupgradeTool(mock_venv_manager, config)

    def test_name(self, pyupgrade_tool):
        """Test tool name."""
        assert pyupgrade_tool.name == "pyupgrade"

    def test_build_args_target_version(self, pyupgrade_tool):
        """Test argument building with target version."""
        paths = [Path("src/main.py")]
        args = pyupgrade_tool.build_args(paths)

        assert "--py310-plus" in args

    def test_parse_output_rewriting(self, pyupgrade_tool):
        """Test parsing output with rewriting."""
        stdout = "Rewriting src/main.py\nRewriting src/utils.py\n"

        issues_found, issues_fixed = pyupgrade_tool.parse_output(stdout, "")

        assert issues_found == 2
        assert issues_fixed == 2


class TestAutoflakeTool:
    """Tests for AutoflakeTool."""

    @pytest.fixture
    def mock_venv_manager(self):
        """Create a mock venv manager."""
        return MagicMock()

    @pytest.fixture
    def autoflake_tool(self, mock_venv_manager):
        """Create an AutoflakeTool instance."""
        return AutoflakeTool(mock_venv_manager)

    def test_name(self, autoflake_tool):
        """Test tool name."""
        assert autoflake_tool.name == "autoflake"

    def test_build_args_check_mode(self, autoflake_tool):
        """Test argument building in check mode."""
        paths = [Path("src/")]
        args = autoflake_tool.build_args(paths, fix=False)

        assert "--check" in args
        assert "--in-place" not in args

    def test_build_args_fix_mode(self, autoflake_tool):
        """Test argument building in fix mode."""
        paths = [Path("src/")]
        args = autoflake_tool.build_args(paths, fix=True)

        assert "--in-place" in args
        assert "--check" not in args

    def test_build_args_removes_unused(self, autoflake_tool):
        """Test that unused import/variable removal is enabled."""
        paths = [Path(".")]
        args = autoflake_tool.build_args(paths)

        assert "--remove-all-unused-imports" in args
        assert "--remove-unused-variables" in args
