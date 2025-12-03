"""Tests for advanced Juff configuration features."""

import pytest
from pathlib import Path

from juff.config import JuffConfig


class TestPerFileIgnores:
    """Tests for per-file-ignores functionality."""

    def test_get_per_file_ignores(self, tmp_path):
        """Test getting per-file ignores from config."""
        config_content = """
[lint]
select = ["E", "F"]

[lint.per-file-ignores]
"**/tests/*" = ["E501", "ANN"]
"src/*.py" = ["F401"]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        per_file = config.get_per_file_ignores()
        assert "**/tests/*" in per_file
        assert per_file["**/tests/*"] == ["E501", "ANN"]
        assert per_file["src/*.py"] == ["F401"]

    def test_get_ignored_rules_for_file_global(self, tmp_path):
        """Test that global ignores apply to all files."""
        config_content = """
[lint]
ignore = ["E501"]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        ignored = config.get_ignored_rules_for_file(Path("src/main.py"))
        assert "E501" in ignored

    def test_get_ignored_rules_for_file_with_pattern(self, tmp_path):
        """Test that per-file ignores apply to matching files."""
        config_content = """
[lint]
ignore = ["E501"]

[lint.per-file-ignores]
"**/tests/*" = ["ANN", "SIM105"]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        # Test file in tests directory
        ignored = config.get_ignored_rules_for_file(Path("project/tests/test_main.py"))
        assert "E501" in ignored  # Global
        assert "ANN" in ignored  # Per-file
        assert "SIM105" in ignored  # Per-file

        # Test file not in tests directory
        ignored = config.get_ignored_rules_for_file(Path("src/main.py"))
        assert "E501" in ignored  # Global
        assert "ANN" not in ignored  # Should not apply
        assert "SIM105" not in ignored  # Should not apply

    def test_is_rule_ignored_for_file(self, tmp_path):
        """Test checking if a rule is ignored for a specific file."""
        config_content = """
[lint]
ignore = ["E501"]

[lint.per-file-ignores]
"**/tests/*" = ["ANN"]
"**/fixtures/*" = ["ALL"]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        # Global ignore
        assert config.is_rule_ignored_for_file("E501", Path("src/main.py"))

        # Per-file ignore
        assert config.is_rule_ignored_for_file("ANN001", Path("tests/test_main.py"))
        assert not config.is_rule_ignored_for_file("ANN001", Path("src/main.py"))

        # ALL ignores everything
        assert config.is_rule_ignored_for_file("E501", Path("tests/fixtures/sample.py"))
        assert config.is_rule_ignored_for_file("F401", Path("tests/fixtures/sample.py"))
        assert config.is_rule_ignored_for_file("ANN", Path("tests/fixtures/sample.py"))


class TestPatternMatching:
    """Tests for glob pattern matching."""

    def test_matches_simple_pattern(self, tmp_path):
        """Test simple glob pattern matching."""
        config = JuffConfig()
        config._config = {}

        assert config._matches_pattern("src/main.py", "*.py")
        assert config._matches_pattern("src/main.py", "src/*.py")
        assert not config._matches_pattern("src/main.py", "tests/*.py")

    def test_matches_double_star_pattern(self, tmp_path):
        """Test ** glob pattern matching."""
        config = JuffConfig()
        config._config = {}

        # **/ at the start should match any directory prefix
        assert config._matches_pattern("foo/tests/bar.py", "**/tests/*")
        assert config._matches_pattern("deep/nested/tests/file.py", "**/tests/*")
        assert config._matches_pattern("tests/file.py", "**/tests/*")

    def test_is_file_excluded(self, tmp_path):
        """Test file exclusion checking."""
        config_content = """
exclude = [
    "vendor/",
    "**/node_modules/*",
    "*.generated.py",
]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        assert config.is_file_excluded(Path("vendor/lib.py"))
        assert config.is_file_excluded(Path("src/vendor/lib.py"))
        assert config.is_file_excluded(Path("frontend/node_modules/package/index.py"))
        assert config.is_file_excluded(Path("src/model.generated.py"))
        assert not config.is_file_excluded(Path("src/main.py"))


class TestIsortConfig:
    """Tests for isort configuration."""

    def test_get_isort_known_first_party(self, tmp_path):
        """Test getting known first-party packages."""
        config_content = """
[lint.isort]
known-first-party = ["myproject", "mylib", "myutils"]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        first_party = config.get_isort_known_first_party()
        assert first_party == ["myproject", "mylib", "myutils"]

    def test_get_isort_known_third_party(self, tmp_path):
        """Test getting known third-party packages."""
        config_content = """
[lint.isort]
known-third-party = ["requests", "flask"]
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        third_party = config.get_isort_known_third_party()
        assert third_party == ["requests", "flask"]

    def test_get_isort_config_empty(self):
        """Test getting isort config when not specified."""
        config = JuffConfig()
        config._config = {}

        assert config.get_isort_known_first_party() == []
        assert config.get_isort_known_third_party() == []


class TestFlake8AnnotationsConfig:
    """Tests for flake8-annotations configuration."""

    def test_get_suppress_none_returning_true(self, tmp_path):
        """Test getting suppress-none-returning when true."""
        config_content = """
[lint.flake8-annotations]
suppress-none-returning = true
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        assert config.get_flake8_annotations_suppress_none_returning() is True

    def test_get_suppress_none_returning_false(self, tmp_path):
        """Test getting suppress-none-returning when false."""
        config_content = """
[lint.flake8-annotations]
suppress-none-returning = false
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        assert config.get_flake8_annotations_suppress_none_returning() is False

    def test_get_suppress_none_returning_default(self):
        """Test default value for suppress-none-returning."""
        config = JuffConfig()
        config._config = {}

        assert config.get_flake8_annotations_suppress_none_returning() is False


class TestRuffTomlCompatibility:
    """Tests for ruff.toml format compatibility."""

    def test_full_ruff_config(self, tmp_path):
        """Test loading a full ruff-style configuration."""
        config_content = """
target-version = "py311"
line-length = 88

exclude = [
    "vendor/",
    "generated/",
]

[lint]
select = [
    "E",
    "F",
    "N",
    "C4",
    "I",
    "B",
    "ANN",
    "SIM",
    "UP",
]

ignore = ["E501"]

fixable = ["ALL"]

[lint.per-file-ignores]
"**/tests/*" = ["E501", "ANN", "SIM105", "SIM108", "SIM115"]
"**/fixtures/*" = ["ALL"]

[lint.isort]
known-first-party = ["myproject"]

[lint.flake8-annotations]
suppress-none-returning = true
"""
        config_file = tmp_path / "juff.toml"
        config_file.write_text(config_content)

        config = JuffConfig(config_path=config_file)
        config.load()

        # Check basic settings
        assert config.get_target_version() == "py311"
        assert config.get_line_length() == 88

        # Check exclude
        excludes = config.get_exclude_patterns()
        assert "vendor/" in excludes
        assert "generated/" in excludes

        # Check lint settings
        selected = config.get_selected_rules()
        assert "E" in selected
        assert "F" in selected
        assert "UP" in selected

        ignored = config.get_ignored_rules()
        assert "E501" in ignored

        # Check per-file ignores
        pfi = config.get_per_file_ignores()
        assert "**/tests/*" in pfi
        assert "ANN" in pfi["**/tests/*"]

        # Check isort config
        assert config.get_isort_known_first_party() == ["myproject"]

        # Check flake8-annotations config
        assert config.get_flake8_annotations_suppress_none_returning() is True

        # Check tools needed
        tools = config.get_tools_for_rules()
        assert "flake8" in tools
        assert "isort" in tools
        assert "pyupgrade" in tools
