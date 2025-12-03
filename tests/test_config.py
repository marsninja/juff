"""Tests for Juff configuration parsing."""

import pytest
from pathlib import Path

from juff.config import JuffConfig


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
        assert config.get_exclude_patterns() == []
        assert config.get_include_patterns() == ["*.py"]
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

