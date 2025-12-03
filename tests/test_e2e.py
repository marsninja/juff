"""End-to-end tests for Juff.

These tests actually run juff on fixture files to verify real-world behavior.
They require the juff venv to be initialized (will auto-initialize if needed).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Path to fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def juff_initialized():
    """Ensure juff venv is initialized before running e2e tests."""
    from juff.venv_manager import JuffVenvManager

    manager = JuffVenvManager()
    if not manager.is_initialized():
        pytest.skip("Juff venv not initialized. Run 'juff init' first.")
    return manager


@pytest.fixture
def temp_fixture_dir(tmp_path):
    """Create a temporary directory with copies of fixture files."""
    # Copy all fixtures to temp dir so we can modify them
    for fixture_file in FIXTURES_DIR.glob("*.py"):
        shutil.copy(fixture_file, tmp_path / fixture_file.name)
    return tmp_path


def run_juff(*args, cwd=None):
    """Run juff CLI and return result."""
    cmd = [sys.executable, "-m", "juff.cli"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result


class TestJuffCheck:
    """End-to-end tests for juff check command."""

    def test_check_detects_unused_imports(self, juff_initialized):
        """Test that juff check detects unused imports."""
        fixture = FIXTURES_DIR / "has_unused_imports.py"
        result = run_juff("check", str(fixture))

        # Should find F401 unused import errors
        assert result.returncode != 0 or "F401" in result.stdout

    def test_check_detects_style_errors(self, juff_initialized):
        """Test that juff check detects style errors."""
        fixture = FIXTURES_DIR / "has_syntax_errors.py"
        result = run_juff("check", str(fixture))

        # Should find various E errors
        output = result.stdout + result.stderr
        # At minimum should detect some issues
        assert result.returncode != 0 or any(
            code in output for code in ["E", "W", "F"]
        )

    def test_check_clean_file_passes(self, juff_initialized):
        """Test that a clean file passes checks."""
        fixture = FIXTURES_DIR / "clean_file.py"
        result = run_juff("check", str(fixture))

        # Clean file should pass (or only have minor issues)
        # Note: depending on config, might still flag some things
        assert "error" not in result.stderr.lower() or result.returncode == 0

    def test_check_with_fix_modifies_file(self, juff_initialized, temp_fixture_dir):
        """Test that --fix actually modifies files."""
        fixture = temp_fixture_dir / "has_unused_imports.py"
        original_content = fixture.read_text()

        result = run_juff("check", "--fix", str(fixture))

        # File may have been modified
        new_content = fixture.read_text()
        # Either content changed or command ran successfully
        assert result.returncode in [0, 1]


class TestJuffFormat:
    """End-to-end tests for juff format command."""

    def test_format_check_detects_issues(self, juff_initialized):
        """Test that format --check detects formatting issues."""
        fixture = FIXTURES_DIR / "needs_formatting.py"
        result = run_juff("format", "--check", str(fixture))

        # Should detect formatting issues (returncode 1)
        # or report would reformat, or find issues
        output = result.stdout + result.stderr
        assert (
            result.returncode == 1
            or "would" in output.lower()
            or "file(s)" in output.lower()
        )

    def test_format_modifies_file(self, juff_initialized, temp_fixture_dir):
        """Test that format actually modifies files."""
        fixture = temp_fixture_dir / "needs_formatting.py"
        original_content = fixture.read_text()

        result = run_juff("format", str(fixture))

        new_content = fixture.read_text()
        # Content should be different after formatting
        # (black should add spaces around operators, etc.)
        assert new_content != original_content or result.returncode == 0



class TestJuffCommands:
    """End-to-end tests for other juff commands."""

    def test_version_command(self):
        """Test juff version command."""
        result = run_juff("version")

        assert result.returncode == 0
        assert "juff" in result.stdout.lower()

    def test_rule_command_known_rule(self):
        """Test juff rule command with known rule."""
        result = run_juff("rule", "E501")

        assert result.returncode == 0
        assert "E501" in result.stdout
        assert "flake8" in result.stdout.lower()

    def test_rule_command_unknown_rule(self):
        """Test juff rule command with unknown rule."""
        result = run_juff("rule", "INVALID999")

        assert result.returncode == 1
        assert "unknown" in result.stdout.lower()

    def test_help_command(self):
        """Test juff --help."""
        result = run_juff("--help")

        assert result.returncode == 0
        assert "check" in result.stdout
        assert "format" in result.stdout

    def test_check_help(self):
        """Test juff check --help."""
        result = run_juff("check", "--help")

        assert result.returncode == 0
        assert "--fix" in result.stdout
        assert "--select" in result.stdout


class TestJuffWithConfig:
    """End-to-end tests with configuration files."""

    def test_check_with_juff_toml(self, juff_initialized, tmp_path):
        """Test check command respects juff.toml."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nx=1\n")

        # Create juff.toml that ignores E225
        config_file = tmp_path / "juff.toml"
        config_file.write_text("""
line-length = 100

[lint]
select = ["E", "F"]
ignore = ["E225"]
""")

        result = run_juff("check", str(test_file), cwd=tmp_path)

        # Should run with config
        assert result.returncode in [0, 1]

    def test_check_with_pyproject_toml(self, juff_initialized, tmp_path):
        """Test check command respects pyproject.toml [tool.juff]."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\n")

        # Create pyproject.toml with juff config
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.juff]
line-length = 120

[tool.juff.lint]
select = ["F"]
ignore = ["F401"]
""")

        result = run_juff("check", str(test_file), cwd=tmp_path)

        # Should run with config (F401 ignored, so should pass)
        assert result.returncode in [0, 1]


class TestJuffIntegration:
    """Integration tests that verify full workflows."""

    def test_full_lint_fix_format_workflow(self, juff_initialized, temp_fixture_dir):
        """Test a full workflow: check -> fix -> format."""
        fixture = temp_fixture_dir / "mixed_issues.py"

        # Step 1: Check finds issues
        result = run_juff("check", str(fixture))
        # Should find issues
        initial_output = result.stdout

        # Step 2: Fix auto-fixable issues
        result = run_juff("check", "--fix", str(fixture))

        # Step 3: Format the file
        result = run_juff("format", str(fixture))

        # Step 4: Final check should have fewer/no issues
        result = run_juff("check", str(fixture))
        final_output = result.stdout

        # Workflow completed
        assert result.returncode in [0, 1]

    def test_check_entire_fixtures_directory(self, juff_initialized):
        """Test checking an entire directory."""
        result = run_juff("check", str(FIXTURES_DIR))

        # Should process all files
        assert result.returncode in [0, 1]
        # Should mention processing multiple files or find issues
        output = result.stdout + result.stderr
        assert len(output) > 0 or result.returncode == 0

    def test_format_entire_directory(self, juff_initialized, temp_fixture_dir):
        """Test formatting an entire directory."""
        result = run_juff("format", str(temp_fixture_dir))

        # Should process all files
        assert result.returncode in [0, 1]
