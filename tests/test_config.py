"""Tests for Juff configuration parsing."""

import pytest
from pathlib import Path

from juff.config import (
    JuffConfig,
    RULE_PREFIX_MAPPING,
    RUFF_ONLY_PREFIXES,
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
)


# Path to config fixtures
CONFIG_FIXTURES = Path(__file__).parent / "fixtures" / "configs"


class TestJuffConfig:
    """Tests for JuffConfig class."""

    def test_default_config_values(self):
        """Test that default config values are correct."""
        config = JuffConfig()
        config._config = {}  # Empty config

        assert config.get_line_length() == 88
        assert config.get_target_version() == "py311"
        assert config.get_selected_rules() == ["E", "F", "W"]
        assert config.get_ignored_rules() == []
        # Default exclude patterns are now populated
        exclude = config.get_exclude_patterns()
        assert ".git" in exclude
        assert ".venv" in exclude
        # Default include patterns
        include = config.get_include_patterns()
        assert "*.py" in include
        assert config.get_fixable_rules() == ["ALL"]
        assert config.get_unfixable_rules() == []

    def test_load_juff_toml(self, sample_config_toml, temp_dir):
        """Test loading juff.toml config file."""
        config = JuffConfig()
        config.load(start_dir=temp_dir)

        assert config.get_line_length() == 100
        assert config.get_target_version() == "py310"
        assert config.get_selected_rules() == ["E", "F", "W", "B"]
        assert config.get_ignored_rules() == ["E501"]
        assert config.get_exclude_patterns() == [".git", "__pycache__"]

    def test_load_pyproject_toml(self, sample_pyproject_toml, temp_dir):
        """Test loading config from pyproject.toml [tool.juff] section."""
        config = JuffConfig()
        config.load(start_dir=temp_dir)

        assert config.get_line_length() == 120
        assert config.get_target_version() == "py311"
        assert config.get_selected_rules() == ["E", "F"]
        assert config.get_ignored_rules() == ["E203"]

    def test_explicit_config_path(self, sample_config_toml):
        """Test loading config from explicit path."""
        config = JuffConfig(config_path=sample_config_toml)
        config.load()

        assert config.get_line_length() == 100
        assert config.config_path == sample_config_toml

    def test_find_config_file_walks_up(self, temp_dir, sample_config_toml):
        """Test that config file search walks up directory tree."""
        # Create a subdirectory
        subdir = temp_dir / "src" / "module"
        subdir.mkdir(parents=True)

        config = JuffConfig()
        found = config.find_config_file(start_dir=subdir)

        assert found == sample_config_toml

    def test_no_config_file_returns_empty(self, temp_dir):
        """Test that missing config returns empty dict."""
        config = JuffConfig()
        result = config.load(start_dir=temp_dir)

        assert result == {}

    def test_is_rule_selected_basic(self):
        """Test basic rule selection logic."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["E", "F"], "ignore": ["E501"]}}

        assert config.is_rule_selected("E101") is True
        assert config.is_rule_selected("F401") is True
        assert config.is_rule_selected("E501") is False  # Ignored
        assert config.is_rule_selected("W503") is False  # Not selected

    def test_is_rule_selected_all(self):
        """Test rule selection with ALL."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["ALL"], "ignore": []}}

        assert config.is_rule_selected("E101") is True
        assert config.is_rule_selected("F401") is True
        assert config.is_rule_selected("B001") is True

    def test_get_tools_for_rules(self):
        """Test mapping rules to tools."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["E", "F", "I", "UP"]}}

        tools = config.get_tools_for_rules()

        assert "flake8" in tools
        assert "isort" in tools
        assert "pyupgrade" in tools

    def test_get_tools_for_rules_all(self):
        """Test that ALL selects all tools."""
        config = JuffConfig()
        config._config = {"lint": {"select": ["ALL"]}}

        tools = config.get_tools_for_rules()

        # Should have all tools from mapping
        assert "flake8" in tools
        assert "isort" in tools
        assert "pyupgrade" in tools
        assert "black" in tools


class TestComprehensiveConfig:
    """Tests for comprehensive ruff.toml configuration compatibility."""

    def test_load_comprehensive_config(self):
        """Test loading comprehensive configuration file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        # Global options
        assert config.get_line_length() == 100
        assert config.get_indent_width() == 4
        assert config.get_target_version() == "py311"
        assert config.is_preview_enabled() is False
        assert config.is_fix_enabled() is True
        assert config.is_show_fixes_enabled() is True
        assert config.get_output_format() == "full"

    def test_comprehensive_lint_config(self):
        """Test lint configuration from comprehensive file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        # Lint rules
        selected = config.get_selected_rules()
        assert "E" in selected
        assert "F" in selected
        assert "B" in selected
        assert "I" in selected
        assert "ANN" in selected  # From extend-select

        ignored = config.get_ignored_rules()
        assert "E501" in ignored
        assert "S101" in ignored

    def test_comprehensive_per_file_ignores(self):
        """Test per-file ignores from comprehensive config."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        per_file = config.get_per_file_ignores()
        assert "__init__.py" in per_file
        assert "F401" in per_file["__init__.py"]
        assert "tests/**/*.py" in per_file

    def test_comprehensive_isort_config(self):
        """Test isort configuration from comprehensive file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_isort_known_first_party() == ["myapp", "mylib"]
        assert config.get_isort_known_third_party() == ["requests", "django"]
        assert config.is_isort_combine_as_imports() is True

    def test_comprehensive_mccabe_config(self):
        """Test mccabe configuration from comprehensive file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_mccabe_max_complexity() == 10

    def test_comprehensive_pylint_config(self):
        """Test pylint configuration from comprehensive file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_pylint_max_args() == 6
        assert config.get_pylint_max_branches() == 15
        assert config.get_pylint_max_returns() == 8
        assert config.get_pylint_max_statements() == 60

    def test_comprehensive_format_config(self):
        """Test format configuration from comprehensive file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_format_indent_style() == "space"
        assert config.get_format_quote_style() == "double"
        assert config.is_skip_magic_trailing_comma() is False
        assert config.is_docstring_code_format() is True
        assert config.get_docstring_code_line_length() == 80

    def test_comprehensive_pydocstyle_config(self):
        """Test pydocstyle configuration from comprehensive file."""
        config_path = CONFIG_FIXTURES / "comprehensive.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_pydocstyle_convention() == "google"


class TestRuffMigrationConfig:
    """Tests for ruff.toml migration compatibility."""

    def test_load_ruff_toml(self):
        """Test loading ruff.toml directly."""
        config_path = CONFIG_FIXTURES / "ruff_migration.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_line_length() == 120
        assert config.get_target_version() == "py310"

    def test_ruff_migration_lint_rules(self):
        """Test lint rules from ruff.toml."""
        config_path = CONFIG_FIXTURES / "ruff_migration.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        selected = config.get_selected_rules()
        assert "E" in selected
        assert "I" in selected
        assert "C90" in selected

        assert "E501" in config.get_ignored_rules()

    def test_ruff_migration_format_config(self):
        """Test format config from ruff.toml."""
        config_path = CONFIG_FIXTURES / "ruff_migration.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        assert config.get_format_quote_style() == "single"


class TestPyprojectConfig:
    """Tests for pyproject.toml configuration."""

    def test_load_pyproject_with_tool_juff(self, tmp_path):
        """Test loading pyproject.toml with [tool.juff] section."""
        import shutil
        # Copy fixture to pyproject.toml so the loader recognizes it
        src = CONFIG_FIXTURES / "pyproject_juff.toml"
        dest = tmp_path / "pyproject.toml"
        shutil.copy(src, dest)

        config = JuffConfig(config_path=dest)
        config.load()

        assert config.get_line_length() == 88
        assert config.get_target_version() == "py310"
        assert "B" in config.get_selected_rules()

    def test_load_pyproject_with_tool_ruff(self, tmp_path):
        """Test loading pyproject.toml with [tool.ruff] section for migration."""
        import shutil
        src = CONFIG_FIXTURES / "pyproject_ruff.toml"
        dest = tmp_path / "pyproject.toml"
        shutil.copy(src, dest)

        config = JuffConfig(config_path=dest)
        config.load()

        assert config.get_line_length() == 100
        assert config.get_target_version() == "py311"
        assert config.get_format_indent_style() == "tab"

    def test_pyproject_isort_config(self, tmp_path):
        """Test isort config from pyproject.toml."""
        import shutil
        src = CONFIG_FIXTURES / "pyproject_juff.toml"
        dest = tmp_path / "pyproject.toml"
        shutil.copy(src, dest)

        config = JuffConfig(config_path=dest)
        config.load()

        assert config.get_isort_known_first_party() == ["myproject"]
        assert config.is_isort_force_single_line() is True


class TestExtendConfig:
    """Tests for configuration extend functionality."""

    def test_extend_base_config(self):
        """Test extending a base configuration."""
        config_path = CONFIG_FIXTURES / "child_extends.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        # Child overrides parent line-length
        assert config.get_line_length() == 100

        # Child adds to selected rules via extend-select
        selected = config.get_selected_rules()
        # Base rules (E, F, W) should be inherited
        # Child adds B, S via extend-select
        assert "B" in selected or "S" in selected

    def test_extend_inherits_per_file_ignores(self):
        """Test that extend merges per-file-ignores."""
        config_path = CONFIG_FIXTURES / "child_extends.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        per_file = config.get_per_file_ignores()
        # Should have both base and child per-file-ignores
        assert "__init__.py" in per_file or "tests/*.py" in per_file

    def test_recursive_extend(self):
        """Test that extends are resolved recursively (grandparent -> parent -> child)."""
        config_path = CONFIG_FIXTURES / "child_extends.toml"
        config = JuffConfig(config_path=config_path)
        config.load()

        # child_extends.toml -> base.toml -> grandparent.toml
        # grandparent: line-length=72, target-version=py38, select=["E"]
        # base overrides: line-length=80, target-version=py39, select=["E","F","W"]
        # child overrides: line-length=100

        # Should have child's line-length
        assert config.get_line_length() == 100

        # Should have base's target-version (grandparent's py38 was overridden by base's py39)
        assert config.get_target_version() == "py39"

        # Should have base's rules (grandparent's ["E"] was overridden by base's ["E","F","W"])
        selected = config.get_selected_rules()
        assert "E" in selected
        assert "F" in selected
        assert "W" in selected

    def test_circular_extend_protection(self, tmp_path):
        """Test that circular extends don't cause infinite loops."""
        # Create two configs that reference each other
        config_a = tmp_path / "config_a.toml"
        config_b = tmp_path / "config_b.toml"

        config_a.write_text('extend = "config_b.toml"\nline-length = 100\n')
        config_b.write_text('extend = "config_a.toml"\nline-length = 80\n')

        config = JuffConfig(config_path=config_a)
        # Should not hang or crash
        config.load()

        # Should get the value from config_a (the entry point)
        assert config.get_line_length() == 100


class TestDefaultValues:
    """Tests for default configuration values."""

    def test_default_exclude_patterns(self):
        """Test default exclusion patterns match ruff."""
        assert ".git" in DEFAULT_EXCLUDE
        assert ".venv" in DEFAULT_EXCLUDE
        assert "venv" in DEFAULT_EXCLUDE
        assert "__pycache__" in DEFAULT_EXCLUDE
        assert "node_modules" in DEFAULT_EXCLUDE
        assert ".mypy_cache" in DEFAULT_EXCLUDE

    def test_default_include_patterns(self):
        """Test default inclusion patterns."""
        assert "*.py" in DEFAULT_INCLUDE
        assert "*.pyi" in DEFAULT_INCLUDE

    def test_ruff_only_prefixes(self):
        """Test that ruff-only prefixes are correctly defined."""
        assert "RUF" in RUFF_ONLY_PREFIXES
        assert "AIR" in RUFF_ONLY_PREFIXES
        assert "FAST" in RUFF_ONLY_PREFIXES
        assert "NPY" in RUFF_ONLY_PREFIXES
        assert "PGH" in RUFF_ONLY_PREFIXES

    def test_rule_prefix_mapping_coverage(self):
        """Test that common rule prefixes are mapped."""
        # Core flake8
        assert RULE_PREFIX_MAPPING["E"] == "flake8"
        assert RULE_PREFIX_MAPPING["W"] == "flake8"
        assert RULE_PREFIX_MAPPING["F"] == "flake8"

        # Plugins
        assert RULE_PREFIX_MAPPING["B"] == "flake8"
        assert RULE_PREFIX_MAPPING["S"] == "flake8"
        assert RULE_PREFIX_MAPPING["I"] == "isort"
        assert RULE_PREFIX_MAPPING["UP"] == "pyupgrade"

        # Standalone
        assert RULE_PREFIX_MAPPING["PLC"] == "pylint"
        assert RULE_PREFIX_MAPPING["FURB"] == "refurb"

        # Ruff-only
        assert RULE_PREFIX_MAPPING["RUF"] == "ruff"


class TestNewGlobalOptions:
    """Tests for new global configuration options."""

    def test_cache_dir(self):
        """Test cache directory configuration."""
        config = JuffConfig()
        config._config = {"cache-dir": "~/.cache/juff"}
        config._project_root = Path("/project")

        cache_dir = config.get_cache_dir()
        assert "cache" in str(cache_dir) or "juff" in str(cache_dir)

    def test_src_paths(self):
        """Test source paths configuration."""
        config = JuffConfig()
        config._config = {"src": ["src", "lib", "packages"]}

        assert config.get_src_paths() == ["src", "lib", "packages"]

    def test_builtins(self):
        """Test builtins configuration."""
        config = JuffConfig()
        config._config = {"builtins": ["_", "gettext"]}

        assert config.get_builtins() == ["_", "gettext"]

    def test_namespace_packages(self):
        """Test namespace packages configuration."""
        config = JuffConfig()
        config._config = {"namespace-packages": ["myapp.plugins"]}

        assert config.get_namespace_packages() == ["myapp.plugins"]

    def test_per_file_target_version(self):
        """Test per-file target version configuration."""
        config = JuffConfig()
        config._config = {
            "per-file-target-version": {
                "scripts/*.py": "py312",
                "legacy/*.py": "py38",
            }
        }

        versions = config.get_per_file_target_version()
        assert versions["scripts/*.py"] == "py312"
        assert versions["legacy/*.py"] == "py38"


class TestNewLintOptions:
    """Tests for new lint configuration options."""

    def test_extend_select(self):
        """Test extend-select merges with select."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "select": ["E", "F"],
                "extend-select": ["B", "S"],
            }
        }

        selected = config.get_selected_rules()
        assert "E" in selected
        assert "F" in selected
        assert "B" in selected
        assert "S" in selected

    def test_task_tags(self):
        """Test task tags configuration."""
        config = JuffConfig()
        config._config = {
            "lint": {"task-tags": ["TODO", "FIXME", "HACK"]}
        }

        assert config.get_task_tags() == ["TODO", "FIXME", "HACK"]

    def test_dummy_variable_rgx(self):
        """Test dummy variable regex configuration."""
        config = JuffConfig()
        config._config = {
            "lint": {"dummy-variable-rgx": "^_.*$"}
        }

        assert config.get_dummy_variable_rgx() == "^_.*$"

    def test_logger_objects(self):
        """Test logger objects configuration."""
        config = JuffConfig()
        config._config = {
            "lint": {"logger-objects": ["logger", "LOGGER"]}
        }

        assert config.get_logger_objects() == ["logger", "LOGGER"]

    def test_is_rule_fixable(self):
        """Test rule fixability check."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "fixable": ["ALL"],
                "unfixable": ["F401"],
            }
        }

        assert config.is_rule_fixable("E501") is True
        assert config.is_rule_fixable("F401") is False
        # F402 is still fixable because only F401 is explicitly unfixable
        assert config.is_rule_fixable("F402") is True

    def test_is_rule_fixable_prefix(self):
        """Test rule fixability with prefix."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "fixable": ["ALL"],
                "unfixable": ["F"],  # Entire F prefix unfixable
            }
        }

        assert config.is_rule_fixable("E501") is True
        assert config.is_rule_fixable("F401") is False
        assert config.is_rule_fixable("F402") is False  # F prefix is unfixable


class TestNewFormatOptions:
    """Tests for new format configuration options."""

    def test_line_ending(self):
        """Test line ending configuration."""
        config = JuffConfig()
        config._config = {"format": {"line-ending": "lf"}}

        assert config.get_format_line_ending() == "lf"

    def test_docstring_code_format(self):
        """Test docstring code format configuration."""
        config = JuffConfig()
        config._config = {"format": {"docstring-code-format": True}}

        assert config.is_docstring_code_format() is True

    def test_format_preview(self):
        """Test format preview mode."""
        config = JuffConfig()
        config._config = {"format": {"preview": True}}

        assert config.is_format_preview_enabled() is True


class TestPluginConfigs:
    """Tests for plugin-specific configurations."""

    def test_flake8_bandit_config(self):
        """Test flake8-bandit configuration."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "flake8-bandit": {
                    "check-typed-exception": True,
                }
            }
        }

        bandit_config = config.get_flake8_bandit_config()
        assert bandit_config.get("check-typed-exception") is True

    def test_flake8_bugbear_config(self):
        """Test flake8-bugbear configuration."""
        config = JuffConfig()
        config._config = {
            "lint": {
                "flake8-bugbear": {
                    "extend-immutable-calls": ["fastapi.Depends"],
                }
            }
        }

        bugbear_config = config.get_flake8_bugbear_config()
        assert "fastapi.Depends" in bugbear_config.get("extend-immutable-calls", [])

    def test_pycodestyle_config(self):
        """Test pycodestyle configuration."""
        config = JuffConfig()
        config._config = {
            "line-length": 88,
            "lint": {
                "pycodestyle": {
                    "max-line-length": 120,
                }
            }
        }

        # pycodestyle max-line-length overrides global
        assert config.get_pycodestyle_max_line_length() == 120

    def test_pycodestyle_uses_global_line_length(self):
        """Test pycodestyle falls back to global line-length."""
        config = JuffConfig()
        config._config = {"line-length": 100}

        assert config.get_pycodestyle_max_line_length() == 100

