"""Tests for Juff CLI."""

import pytest
from pathlib import Path

from juff.cli import create_parser, main


class TestCLIParser:
    """Tests for CLI argument parsing."""

    def test_version_flag(self, capsys):
        """Test --version flag."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])

        assert exc_info.value.code == 0

    def test_check_command_basic(self):
        """Test basic check command parsing."""
        parser = create_parser()
        args = parser.parse_args(["check", "."])

        assert args.command == "check"
        assert args.paths == [Path(".")]
        assert args.fix is False

    def test_check_command_with_fix(self):
        """Test check command with --fix flag."""
        parser = create_parser()
        args = parser.parse_args(["check", "--fix", "src/"])

        assert args.command == "check"
        assert args.fix is True
        assert args.paths == [Path("src/")]

    def test_check_command_with_select(self):
        """Test check command with --select option."""
        parser = create_parser()
        args = parser.parse_args(["check", "--select", "E,F,W", "."])

        assert args.select == "E,F,W"

    def test_check_command_with_ignore(self):
        """Test check command with --ignore option."""
        parser = create_parser()
        args = parser.parse_args(["check", "--ignore", "E501,W503", "."])

        assert args.ignore == "E501,W503"

    def test_check_command_multiple_paths(self):
        """Test check command with multiple paths."""
        parser = create_parser()
        args = parser.parse_args(["check", "src/", "tests/", "lib/"])

        assert args.paths == [Path("src/"), Path("tests/"), Path("lib/")]

    def test_format_command_basic(self):
        """Test basic format command parsing."""
        parser = create_parser()
        args = parser.parse_args(["format", "."])

        assert args.command == "format"
        assert args.paths == [Path(".")]
        assert args.check is False

    def test_format_command_check_mode(self):
        """Test format command with --check flag."""
        parser = create_parser()
        args = parser.parse_args(["format", "--check", "."])

        assert args.command == "format"
        assert args.check is True

    def test_format_command_with_diff(self):
        """Test format command with --diff flag."""
        parser = create_parser()
        args = parser.parse_args(["format", "--diff", "."])

        assert args.diff is True

    def test_init_command(self):
        """Test init command parsing."""
        parser = create_parser()
        args = parser.parse_args(["init"])

        assert args.command == "init"
        assert args.force is False

    def test_init_command_force(self):
        """Test init command with --force flag."""
        parser = create_parser()
        args = parser.parse_args(["init", "--force"])

        assert args.command == "init"
        assert args.force is True

    def test_clean_command(self):
        """Test clean command parsing."""
        parser = create_parser()
        args = parser.parse_args(["clean"])

        assert args.command == "clean"

    def test_update_command(self):
        """Test update command parsing."""
        parser = create_parser()
        args = parser.parse_args(["update"])

        assert args.command == "update"

    def test_version_command(self):
        """Test version command parsing."""
        parser = create_parser()
        args = parser.parse_args(["version"])

        assert args.command == "version"
        assert args.verbose is False

    def test_version_command_verbose(self):
        """Test version command with --verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["version", "--verbose"])

        assert args.command == "version"
        assert args.verbose is True

    def test_rule_command(self):
        """Test rule command parsing."""
        parser = create_parser()
        args = parser.parse_args(["rule", "E501"])

        assert args.command == "rule"
        assert args.code == "E501"

    def test_common_args_line_length(self):
        """Test --line-length common argument."""
        parser = create_parser()
        args = parser.parse_args(["check", "--line-length", "120", "."])

        assert args.line_length == 120

    def test_common_args_target_version(self):
        """Test --target-version common argument."""
        parser = create_parser()
        args = parser.parse_args(["check", "--target-version", "py310", "."])

        assert args.target_version == "py310"

    def test_common_args_exclude(self):
        """Test --exclude common argument."""
        parser = create_parser()
        args = parser.parse_args(["check", "--exclude", ".git,__pycache__", "."])

        assert args.exclude == ".git,__pycache__"

    def test_common_args_quiet(self):
        """Test --quiet common argument."""
        parser = create_parser()
        args = parser.parse_args(["check", "-q", "."])

        assert args.quiet is True

    def test_common_args_verbose(self):
        """Test --verbose common argument."""
        parser = create_parser()
        args = parser.parse_args(["check", "-v", "."])

        assert args.verbose is True

    def test_config_argument(self):
        """Test --config argument."""
        parser = create_parser()
        args = parser.parse_args(["--config", "custom.toml", "check", "."])

        assert args.config == Path("custom.toml")

    def test_no_command_returns_zero(self):
        """Test that no command shows help and returns 0."""
        result = main([])
        assert result == 0


class TestRuleCommand:
    """Tests for the rule command."""

    def test_rule_command_known_rule(self, capsys):
        """Test rule command with known rule."""
        from juff.cli import cmd_rule
        import argparse

        args = argparse.Namespace(code="E501")
        result = cmd_rule(args)

        captured = capsys.readouterr()
        assert result == 0
        assert "E501" in captured.out
        assert "flake8" in captured.out

    def test_rule_command_isort_rule(self, capsys):
        """Test rule command with isort rule."""
        from juff.cli import cmd_rule
        import argparse

        args = argparse.Namespace(code="I001")
        result = cmd_rule(args)

        captured = capsys.readouterr()
        assert result == 0
        assert "isort" in captured.out

    def test_rule_command_unknown_rule(self, capsys):
        """Test rule command with unknown rule."""
        from juff.cli import cmd_rule
        import argparse

        args = argparse.Namespace(code="UNKNOWN999")
        result = cmd_rule(args)

        captured = capsys.readouterr()
        assert result == 1
        assert "Unknown rule" in captured.out
