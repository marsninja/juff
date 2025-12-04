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
from juff.tools.docformatter import DocformatterTool
from juff.venv_manager import JuffVenvManager


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


class TestSectionSpecificExcludes:
    """Tests that verify each tool respects section-specific exclude patterns."""

    @pytest.fixture
    def mock_venv_manager(self):
        """Create a mock venv manager."""
        return MagicMock()

    @pytest.fixture
    def config_with_section_excludes(self):
        """Create config with section-specific excludes."""
        config = JuffConfig()
        config._config = {
            "line-length": 88,
            "exclude": [".git", "__pycache__"],
            "lint": {
                "select": ["E", "F", "W"],
                "exclude": ["tests/fixtures", "vendor/"],
            },
            "format": {
                "exclude": ["generated/", "build/"],
            },
        }
        return config

    @pytest.fixture
    def config_lint_only_excludes(self):
        """Create config with only lint-specific excludes (no root-level)."""
        config = JuffConfig()
        config._config = {
            "line-length": 88,
            "lint": {
                "select": ["E", "F"],
                "exclude": ["tests/fixtures"],
            },
            "format": {},
        }
        return config

    @pytest.fixture
    def config_format_only_excludes(self):
        """Create config with only format-specific excludes (no root-level)."""
        config = JuffConfig()
        config._config = {
            "line-length": 88,
            "lint": {},
            "format": {
                "exclude": ["generated/"],
            },
        }
        return config

    def test_flake8_uses_lint_excludes(
        self, mock_venv_manager, config_with_section_excludes
    ):
        """Test that Flake8Tool includes lint-specific excludes."""
        tool = Flake8Tool(mock_venv_manager, config_with_section_excludes)
        args = tool.build_args([Path(".")])

        # Find the --exclude argument
        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        exclude_value = args[exclude_idx + 1]

        # Should include root-level excludes
        assert ".git" in exclude_value
        assert "__pycache__" in exclude_value
        # Should include lint-specific excludes
        assert "tests/fixtures" in exclude_value
        assert "vendor/" in exclude_value
        # Should NOT include format-specific excludes
        assert "generated/" not in exclude_value
        assert "build/" not in exclude_value

    def test_flake8_lint_only_excludes(
        self, mock_venv_manager, config_lint_only_excludes
    ):
        """Test Flake8Tool with only lint-specific excludes."""
        tool = Flake8Tool(mock_venv_manager, config_lint_only_excludes)
        args = tool.build_args([Path(".")])

        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        exclude_value = args[exclude_idx + 1]

        assert "tests/fixtures" in exclude_value

    def test_black_uses_format_excludes(
        self, mock_venv_manager, config_with_section_excludes
    ):
        """Test that BlackTool includes format-specific excludes."""
        tool = BlackTool(mock_venv_manager, config_with_section_excludes)
        args = tool.build_args([Path(".")])

        # Find the --exclude argument
        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        exclude_value = args[exclude_idx + 1]

        # Should include root-level excludes
        assert ".git" in exclude_value
        assert "__pycache__" in exclude_value
        # Should include format-specific excludes (black strips trailing slashes for regex)
        assert "generated" in exclude_value
        assert "build" in exclude_value
        # Should NOT include lint-specific excludes
        assert "tests/fixtures" not in exclude_value
        assert "vendor" not in exclude_value

    def test_black_format_only_excludes(
        self, mock_venv_manager, config_format_only_excludes
    ):
        """Test BlackTool with only format-specific excludes."""
        tool = BlackTool(mock_venv_manager, config_format_only_excludes)
        args = tool.build_args([Path(".")])

        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        exclude_value = args[exclude_idx + 1]

        # black strips trailing slashes when converting to regex
        assert "generated" in exclude_value

    def test_isort_uses_format_excludes(
        self, mock_venv_manager, config_with_section_excludes
    ):
        """Test that IsortTool includes format-specific excludes."""
        tool = IsortTool(mock_venv_manager, config_with_section_excludes)
        args = tool.build_args([Path(".")])

        # isort uses --skip for excludes
        skip_values = [args[i + 1] for i, arg in enumerate(args) if arg == "--skip"]

        # Should include root-level excludes
        assert ".git" in skip_values
        assert "__pycache__" in skip_values
        # Should include format-specific excludes
        assert "generated/" in skip_values
        assert "build/" in skip_values
        # Should NOT include lint-specific excludes
        assert "tests/fixtures" not in skip_values
        assert "vendor/" not in skip_values

    def test_docformatter_uses_format_excludes(
        self, mock_venv_manager, config_with_section_excludes
    ):
        """Test that DocformatterTool includes format-specific excludes."""
        tool = DocformatterTool(mock_venv_manager, config_with_section_excludes)
        args = tool.build_args([Path(".")])

        # docformatter uses --exclude for excludes
        exclude_values = [
            args[i + 1] for i, arg in enumerate(args) if arg == "--exclude"
        ]

        # Should include root-level excludes
        assert ".git" in exclude_values
        assert "__pycache__" in exclude_values
        # Should include format-specific excludes
        assert "generated/" in exclude_values
        assert "build/" in exclude_values
        # Should NOT include lint-specific excludes
        assert "tests/fixtures" not in exclude_values
        assert "vendor/" not in exclude_values

    def test_tool_mode_attributes(self, mock_venv_manager):
        """Test that each tool has the correct mode attribute."""
        config = JuffConfig()
        config._config = {}

        # Lint tools should have mode="lint"
        assert Flake8Tool(mock_venv_manager, config).mode == "lint"
        assert AutoflakeTool(mock_venv_manager, config).mode == "lint"
        assert PyupgradeTool(mock_venv_manager, config).mode == "lint"

        # Format tools should have mode="format"
        assert BlackTool(mock_venv_manager, config).mode == "format"
        assert IsortTool(mock_venv_manager, config).mode == "format"
        assert DocformatterTool(mock_venv_manager, config).mode == "format"

    def test_empty_section_excludes(self, mock_venv_manager):
        """Test tools work correctly when section has no excludes."""
        config = JuffConfig()
        config._config = {
            "exclude": [".git"],
            "lint": {"select": ["E"]},
            "format": {},
        }

        # Flake8 should still get root-level excludes
        flake8 = Flake8Tool(mock_venv_manager, config)
        args = flake8.build_args([Path(".")])
        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        assert ".git" in args[exclude_idx + 1]

        # Black should still get root-level excludes
        black = BlackTool(mock_venv_manager, config)
        args = black.build_args([Path(".")])
        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        assert ".git" in args[exclude_idx + 1]

    def test_no_excludes_at_all(self, mock_venv_manager):
        """Test tools use default excludes when no excludes are defined."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["E"]}}

        flake8 = Flake8Tool(mock_venv_manager, config)
        args = flake8.build_args([Path(".")])
        # Should use DEFAULT_EXCLUDE when no patterns explicitly defined
        assert "--exclude" in args
        exclude_idx = args.index("--exclude")
        assert ".git" in args[exclude_idx + 1]

        black = BlackTool(mock_venv_manager, config)
        args = black.build_args([Path(".")])
        # Black also uses default excludes
        assert "--exclude" in args


class TestToolExcludesIntegration:
    """Integration tests that actually run tools to verify excludes work."""

    # Python file with deliberate lint issues
    BAD_PYTHON_CODE = '''import os
import sys
import unused_import

def bad_function( x,y ):
    z=x+y
    unused_var = 1
    return z
'''

    @pytest.fixture(scope="class")
    def venv_manager(self):
        """Get initialized venv manager or skip tests."""
        manager = JuffVenvManager()
        if not manager.is_initialized():
            pytest.skip("Juff venv not initialized. Run 'juff init' first.")
        return manager

    @pytest.fixture
    def temp_project_flake8(self, tmp_path):
        """Create a temp project for flake8 exclude test."""
        src_dir = tmp_path / "src"
        excluded_dir = tmp_path / "excluded"
        src_dir.mkdir(parents=True)
        excluded_dir.mkdir(parents=True)

        # flake8 uses glob patterns - simple directory name works
        config_content = """
[lint]
select = ["E", "F", "W"]
exclude = ["excluded"]
"""
        (tmp_path / "juff.toml").write_text(config_content)
        (src_dir / "main.py").write_text(self.BAD_PYTHON_CODE)
        (excluded_dir / "skipped.py").write_text(self.BAD_PYTHON_CODE)

        return tmp_path

    @pytest.fixture
    def temp_project_black(self, tmp_path):
        """Create a temp project for black exclude test."""
        src_dir = tmp_path / "src"
        excluded_dir = tmp_path / "excluded"
        src_dir.mkdir(parents=True)
        excluded_dir.mkdir(parents=True)

        # black uses regex - need to escape or use simple pattern
        config_content = """
[format]
exclude = ["excluded"]
"""
        (tmp_path / "juff.toml").write_text(config_content)
        (src_dir / "main.py").write_text(self.BAD_PYTHON_CODE)
        (excluded_dir / "skipped.py").write_text(self.BAD_PYTHON_CODE)

        return tmp_path

    @pytest.fixture
    def temp_project_isort(self, tmp_path):
        """Create a temp project for isort exclude test."""
        src_dir = tmp_path / "src"
        excluded_dir = tmp_path / "excluded"
        src_dir.mkdir(parents=True)
        excluded_dir.mkdir(parents=True)

        # isort uses --skip which takes directory names
        config_content = """
[format]
exclude = ["excluded"]
"""
        (tmp_path / "juff.toml").write_text(config_content)
        (src_dir / "main.py").write_text(self.BAD_PYTHON_CODE)
        (excluded_dir / "skipped.py").write_text(self.BAD_PYTHON_CODE)

        return tmp_path

    def test_flake8_excludes_directory(self, venv_manager, temp_project_flake8):
        """Test that flake8 actually excludes files in excluded directory."""
        config = JuffConfig()
        config.load(start_dir=temp_project_flake8)

        tool = Flake8Tool(venv_manager, config)
        result = tool.run([temp_project_flake8], fix=False)

        # Should find issues in src/main.py
        assert "src/main.py" in result.stdout or "src\\main.py" in result.stdout

        # Should NOT find issues in excluded/skipped.py
        assert "skipped.py" not in result.stdout

    def test_black_excludes_directory(self, venv_manager, temp_project_black):
        """Test that black actually excludes files in excluded directory."""
        config = JuffConfig()
        config.load(start_dir=temp_project_black)

        tool = BlackTool(venv_manager, config)
        result = tool.run([temp_project_black], fix=False)

        output = result.stdout + result.stderr

        # Should report src/main.py needs formatting
        assert "src/main.py" in output or "src\\main.py" in output

        # Should NOT report excluded/skipped.py
        assert "skipped.py" not in output

    def test_isort_excludes_directory(self, venv_manager, temp_project_isort):
        """Test that isort actually excludes files in excluded directory."""
        config = JuffConfig()
        config.load(start_dir=temp_project_isort)

        tool = IsortTool(venv_manager, config)
        result = tool.run([temp_project_isort], fix=False)

        output = result.stdout + result.stderr

        # Should NOT process excluded/skipped.py
        assert "skipped.py" not in output

    def test_lint_only_exclude_not_applied_to_format(self, venv_manager, tmp_path):
        """Test that lint excludes don't affect format tools."""
        # Create directory structure
        generated_dir = tmp_path / "generated"
        generated_dir.mkdir()

        # Config with ONLY lint exclude (not format)
        config_content = """
[lint]
select = ["E", "F"]
exclude = ["generated"]

[format]
# No excludes here
"""
        (tmp_path / "juff.toml").write_text(config_content)
        (generated_dir / "code.py").write_text(self.BAD_PYTHON_CODE)

        config = JuffConfig()
        config.load(start_dir=tmp_path)

        # Flake8 (lint) should exclude generated/
        flake8 = Flake8Tool(venv_manager, config)
        result = flake8.run([tmp_path], fix=False)
        assert "generated" not in result.stdout

        # Black (format) should NOT exclude generated/ (no format exclude)
        black = BlackTool(venv_manager, config)
        result = black.run([tmp_path], fix=False)
        output = result.stdout + result.stderr
        # Black should find the file since it's not excluded for format
        assert "generated" in output or "code.py" in output

    def test_format_only_exclude_not_applied_to_lint(self, venv_manager, tmp_path):
        """Test that format excludes don't affect lint tools."""
        # Create directory structure
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        # Config with ONLY format exclude (not lint)
        config_content = """
[lint]
select = ["E", "F"]
# No excludes here

[format]
exclude = ["build"]
"""
        (tmp_path / "juff.toml").write_text(config_content)
        (build_dir / "output.py").write_text(self.BAD_PYTHON_CODE)

        config = JuffConfig()
        config.load(start_dir=tmp_path)

        # Flake8 (lint) should NOT exclude build/ (no lint exclude)
        flake8 = Flake8Tool(venv_manager, config)
        result = flake8.run([tmp_path], fix=False)
        # Flake8 should find issues in build/output.py
        assert "build" in result.stdout or "output.py" in result.stdout

        # Black (format) should exclude build/
        black = BlackTool(venv_manager, config)
        result = black.run([tmp_path], fix=False)
        output = result.stdout + result.stderr
        assert "build" not in output
        assert "output.py" not in output

    def test_pyupgrade_excludes_directory(self, venv_manager, tmp_path):
        """Test that pyupgrade respects lint excludes when collecting files."""
        src_dir = tmp_path / "src"
        excluded_dir = tmp_path / "excluded"
        src_dir.mkdir()
        excluded_dir.mkdir()

        # Old-style Python code that pyupgrade would want to fix
        old_code = '''
from typing import Optional, List

def foo(x: Optional[str] = None) -> List[str]:
    return []
'''
        config_content = """
[lint]
exclude = ["excluded"]
"""
        (tmp_path / "juff.toml").write_text(config_content)
        (src_dir / "main.py").write_text(old_code)
        (excluded_dir / "skipped.py").write_text(old_code)

        config = JuffConfig()
        config.load(start_dir=tmp_path)

        tool = PyupgradeTool(venv_manager, config)
        result = tool.run([tmp_path], fix=False)

        # Should process src/main.py but NOT excluded/skipped.py
        # pyupgrade processes files and shows "Rewriting" in output
        # The key is that excluded/skipped.py should not appear
        assert "skipped.py" not in result.stdout
        assert "skipped.py" not in result.stderr
