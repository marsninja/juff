"""Integration tests for configuration with real source files.

These tests verify that configuration options correctly affect how
files are processed - testing rule selection, per-file-ignores,
and file exclusions against actual source files.
"""

import pytest
from pathlib import Path

from juff.config import JuffConfig


# Path to integration test project
INTEGRATION_PROJECT = Path(__file__).parent / "fixtures" / "configs" / "integration_project"


class TestConfigFileDecisions:
    """Test that config makes correct decisions for real files."""

    @pytest.fixture
    def config(self):
        """Load the integration project config."""
        config_path = INTEGRATION_PROJECT / "juff.toml"
        cfg = JuffConfig(config_path=config_path)
        cfg.load()
        return cfg

    def test_rule_selection(self, config):
        """Test that selected rules are correct."""
        selected = config.get_selected_rules()

        # E, F, S are selected
        assert "E" in selected
        assert "F" in selected
        assert "S" in selected

        # Other rules are not selected
        assert "B" not in selected
        assert "I" not in selected

    def test_ignored_rules(self, config):
        """Test that E501 is globally ignored."""
        ignored = config.get_ignored_rules()
        assert "E501" in ignored

    def test_init_file_ignores_f401(self, config):
        """Test that __init__.py has F401 ignored via per-file-ignores."""
        init_file = INTEGRATION_PROJECT / "__init__.py"

        # Check that F401 is ignored for __init__.py
        assert config.is_rule_ignored_for_file("F401", init_file)

        # But F841 should NOT be ignored
        assert not config.is_rule_ignored_for_file("F841", init_file)

    def test_test_file_ignores_s101(self, config):
        """Test that test files have S101 ignored via per-file-ignores."""
        test_file = INTEGRATION_PROJECT / "tests" / "test_example.py"

        # Check that S101 is ignored for test files
        assert config.is_rule_ignored_for_file("S101", test_file)

        # But other S rules should NOT be ignored
        assert not config.is_rule_ignored_for_file("S102", test_file)

    def test_main_file_no_special_ignores(self, config):
        """Test that main.py doesn't have special per-file ignores."""
        main_file = INTEGRATION_PROJECT / "main.py"

        # main.py should not have F401 or S101 ignored
        assert not config.is_rule_ignored_for_file("F401", main_file)
        assert not config.is_rule_ignored_for_file("S101", main_file)

        # But E501 should be globally ignored
        assert config.is_rule_ignored_for_file("E501", main_file)

    def test_migrations_excluded(self, config):
        """Test that migrations directory is excluded."""
        migration_file = INTEGRATION_PROJECT / "migrations" / "001_initial.py"

        # migrations/ should be excluded
        assert config.is_file_excluded(migration_file, mode="lint")

    def test_main_not_excluded(self, config):
        """Test that main.py is not excluded."""
        main_file = INTEGRATION_PROJECT / "main.py"

        assert not config.is_file_excluded(main_file, mode="lint")

    def test_test_file_not_excluded(self, config):
        """Test that test files are not excluded."""
        test_file = INTEGRATION_PROJECT / "tests" / "test_example.py"

        assert not config.is_file_excluded(test_file, mode="lint")


class TestRuleSelectionForFiles:
    """Test is_rule_selected with various configurations."""

    def test_selected_rule_not_ignored(self):
        """Test a selected rule that isn't ignored returns True."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "select": ["E", "F"],
                "ignore": ["E501"],
            }
        }

        assert config.is_rule_selected("E225")  # E selected, not ignored
        assert config.is_rule_selected("F401")  # F selected, not ignored
        assert not config.is_rule_selected("E501")  # E selected but ignored
        assert not config.is_rule_selected("B001")  # B not selected

    def test_rule_selected_with_all(self):
        """Test that ALL selects everything."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "select": ["ALL"],
                "ignore": ["S101"],
            }
        }

        assert config.is_rule_selected("E501")
        assert config.is_rule_selected("F401")
        assert config.is_rule_selected("B001")
        assert not config.is_rule_selected("S101")  # Explicitly ignored


class TestPerFileIgnoresWithPatterns:
    """Test per-file-ignores with various glob patterns."""

    def test_double_star_pattern(self):
        """Test that **/*.py pattern matches nested files."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "per-file-ignores": {
                    "tests/**/*.py": ["S101", "ANN"],
                }
            }
        }

        # Should match
        assert config.is_rule_ignored_for_file(
            "S101", Path("tests/test_foo.py")
        )
        assert config.is_rule_ignored_for_file(
            "S101", Path("tests/unit/test_bar.py")
        )
        assert config.is_rule_ignored_for_file(
            "ANN001", Path("tests/integration/deep/test_baz.py")
        )

    def test_single_star_pattern(self):
        """Test that *.py pattern matches files in root."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "per-file-ignores": {
                    "conftest.py": ["F401"],
                    "scripts/*.py": ["T20"],
                }
            }
        }

        assert config.is_rule_ignored_for_file("F401", Path("conftest.py"))
        assert config.is_rule_ignored_for_file("T20", Path("scripts/build.py"))

    def test_exact_filename_pattern(self):
        """Test exact filename matching."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "per-file-ignores": {
                    "__init__.py": ["F401", "F403"],
                }
            }
        }

        # Should match __init__.py anywhere
        assert config.is_rule_ignored_for_file("F401", Path("__init__.py"))
        assert config.is_rule_ignored_for_file("F401", Path("src/__init__.py"))
        assert config.is_rule_ignored_for_file("F403", Path("pkg/sub/__init__.py"))


class TestExcludePatterns:
    """Test file exclusion patterns."""

    def test_default_excludes(self):
        """Test that default excludes work."""
        config = JuffConfig()
        config._config = {}  # Empty config uses defaults

        # Common excluded directories
        assert config.is_file_excluded(Path(".git/config"))
        assert config.is_file_excluded(Path(".venv/lib/python3.11/site.py"))
        assert config.is_file_excluded(Path("node_modules/package/index.py"))
        assert config.is_file_excluded(Path("__pycache__/module.cpython-311.pyc"))

    def test_custom_excludes(self):
        """Test custom exclude patterns."""
        config = JuffConfig()
        config._config = {
            "exclude": ["vendor/", "generated/"],
        }

        assert config.is_file_excluded(Path("vendor/lib.py"))
        assert config.is_file_excluded(Path("generated/models.py"))
        # Default excludes no longer apply when custom excludes are set
        assert not config.is_file_excluded(Path("src/main.py"))

    def test_extend_exclude(self):
        """Test extend-exclude adds to defaults."""
        config = JuffConfig()
        config._config = {
            "extend-exclude": ["legacy/", "migrations/"],
        }

        # Extended excludes
        assert config.is_file_excluded(Path("legacy/old_code.py"))
        assert config.is_file_excluded(Path("migrations/001.py"))

        # Default excludes still apply
        assert config.is_file_excluded(Path(".git/config"))
        assert config.is_file_excluded(Path(".venv/lib/site.py"))

    def test_section_specific_excludes(self):
        """Test lint vs format specific excludes."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "exclude": ["lint_excluded/"],
            },
            "format": {
                "exclude": ["format_excluded/"],
            },
        }

        # Lint-specific exclude
        assert config.is_file_excluded(Path("lint_excluded/foo.py"), mode="lint")
        assert not config.is_file_excluded(Path("lint_excluded/foo.py"), mode="format")

        # Format-specific exclude
        assert config.is_file_excluded(Path("format_excluded/bar.py"), mode="format")
        assert not config.is_file_excluded(Path("format_excluded/bar.py"), mode="lint")


class TestToolSelection:
    """Test that correct tools are selected based on rules."""

    def test_flake8_rules_select_flake8(self):
        """Test that E/W/F rules select flake8."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["E", "W", "F"]}}

        tools = config.get_tools_for_rules()
        assert "flake8" in tools
        assert "isort" not in tools

    def test_isort_rules_select_isort(self):
        """Test that I rules select isort."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["I"]}}

        tools = config.get_tools_for_rules()
        assert "isort" in tools
        assert "flake8" not in tools

    def test_mixed_rules_select_multiple_tools(self):
        """Test that mixed rules select multiple tools."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["E", "I", "UP", "PLC"]}}

        tools = config.get_tools_for_rules()
        assert "flake8" in tools  # E
        assert "isort" in tools  # I
        assert "pyupgrade" in tools  # UP
        assert "pylint" in tools  # PLC

    def test_all_selects_all_tools(self):
        """Test that ALL selects all mapped tools."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["ALL"]}}

        tools = config.get_tools_for_rules()
        assert "flake8" in tools
        assert "isort" in tools
        assert "pyupgrade" in tools
        assert "pylint" in tools
        assert "black" in tools
        assert "ruff" in tools
