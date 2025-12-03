"""Command-line interface for Juff.

This module provides the main CLI entry point for Juff, designed to be
a drop-in replacement for ruff with similar command structure.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from juff import __version__
from juff.config import JuffConfig
from juff.runner import JuffRunner
from juff.venv_manager import JuffVenvManager


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for Juff CLI."""
    parser = argparse.ArgumentParser(
        prog="juff",
        description="A faithful Python-first drop-in replacement for ruff.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  juff check .                 # Lint all files in current directory
  juff check --fix .           # Lint and fix auto-fixable issues
  juff format .                # Format all files
  juff format --check .        # Check formatting without applying
  juff check --select E,F,W .  # Only check specific rules

Configuration:
  Juff looks for configuration in juff.toml, .juff.toml, or pyproject.toml
  (under [tool.juff] section). The format is compatible with ruff.toml.
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"juff {__version__}",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file",
        metavar="PATH",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check command (linting)
    check_parser = subparsers.add_parser(
        "check",
        help="Run linting checks on files",
        description="Lint Python files using flake8 and plugins.",
    )
    _add_common_args(check_parser)
    check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix auto-fixable issues",
    )
    check_parser.add_argument(
        "--select",
        type=str,
        help="Comma-separated list of rule codes to enable",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--ignore",
        type=str,
        help="Comma-separated list of rule codes to ignore",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--output-format",
        choices=["text", "json", "github", "grouped"],
        default="text",
        help="Output format for results",
    )

    # Format command
    format_parser = subparsers.add_parser(
        "format",
        help="Format Python files",
        description="Format Python files using black and isort.",
    )
    _add_common_args(format_parser)
    format_parser.add_argument(
        "--check",
        action="store_true",
        help="Check formatting without applying changes",
    )
    format_parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diff of formatting changes",
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize Juff environment",
        description="Initialize the Juff virtual environment and install tools.",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-initialization even if already initialized",
    )

    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean Juff environment",
        description="Remove the Juff virtual environment and cached data.",
    )

    # Update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update Juff tools",
        description="Update all tools in the Juff environment to latest versions.",
    )

    # Version command (shows tool versions)
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information",
        description="Show Juff and underlying tool versions.",
    )
    version_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all installed package versions",
    )

    # Rule command
    rule_parser = subparsers.add_parser(
        "rule",
        help="Show information about a rule",
        description="Display detailed information about a specific rule.",
    )
    rule_parser.add_argument(
        "code",
        type=str,
        help="Rule code (e.g., E501, F401)",
    )

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a subparser."""
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="Paths to check/format (default: current directory)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated patterns to exclude",
        metavar="PATTERNS",
    )
    parser.add_argument(
        "--line-length",
        type=int,
        help="Line length limit (default: 88)",
        metavar="N",
    )
    parser.add_argument(
        "--target-version",
        type=str,
        help="Target Python version (e.g., py311)",
        metavar="VERSION",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )


def cmd_check(args: argparse.Namespace, config: JuffConfig) -> int:
    """Run the check (lint) command."""
    runner = JuffRunner(config=config)

    # Override config with CLI args
    if args.select:
        config._config = config._config or {}
        config._config.setdefault("lint", {})["select"] = args.select.split(",")
    if args.ignore:
        config._config = config._config or {}
        config._config.setdefault("lint", {})["ignore"] = args.ignore.split(",")
    if args.line_length:
        config._config = config._config or {}
        config._config["line-length"] = args.line_length

    results = runner.lint(args.paths, fix=args.fix)

    # Output results
    total_issues = sum(r.issues_found for r in results)
    total_fixed = sum(r.issues_fixed for r in results)

    for result in results:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr and not args.quiet:
            print(result.stderr, end="", file=sys.stderr)

    if not args.quiet:
        if total_issues > 0:
            if args.fix:
                print(f"\nFound {total_issues} issue(s), fixed {total_fixed}.")
            else:
                print(f"\nFound {total_issues} issue(s).")
        else:
            print("\nAll checks passed!")

    return 1 if total_issues > total_fixed else 0


def cmd_format(args: argparse.Namespace, config: JuffConfig) -> int:
    """Run the format command."""
    runner = JuffRunner(config=config)

    # Override config with CLI args
    if args.line_length:
        config._config = config._config or {}
        config._config["line-length"] = args.line_length

    results = runner.format(args.paths, check_only=args.check)

    # Output results
    total_issues = sum(r.issues_found for r in results)
    total_fixed = sum(r.issues_fixed for r in results)

    for result in results:
        if result.stdout and (args.diff or args.verbose):
            print(result.stdout, end="")
        if result.stderr and not args.quiet:
            print(result.stderr, end="", file=sys.stderr)

    if not args.quiet:
        if args.check:
            if total_issues > 0:
                print(f"\n{total_issues} file(s) would be reformatted.")
                return 1
            else:
                print("\nAll files are properly formatted!")
        else:
            if total_fixed > 0:
                print(f"\nReformatted {total_fixed} file(s).")
            else:
                print("\nNo files needed reformatting.")

    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize the Juff environment."""
    manager = JuffVenvManager()

    print("Initializing Juff environment...")
    print(f"  Location: {manager.venv_path}")

    try:
        manager.ensure_initialized(force=args.force)
        print("\nJuff environment initialized successfully!")
        print("\nInstalled tools:")
        print("  - flake8 (with plugins)")
        print("  - black")
        print("  - isort")
        print("  - pyupgrade")
        print("  - autoflake")
        return 0
    except Exception as e:
        print(f"\nError initializing environment: {e}", file=sys.stderr)
        return 1


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean the Juff environment."""
    import shutil

    manager = JuffVenvManager()

    if not manager.juff_home.exists():
        print("Juff environment not found, nothing to clean.")
        return 0

    print(f"Removing Juff environment at {manager.juff_home}...")
    try:
        shutil.rmtree(manager.juff_home)
        print("Juff environment cleaned successfully!")
        return 0
    except Exception as e:
        print(f"Error cleaning environment: {e}", file=sys.stderr)
        return 1


def cmd_update(args: argparse.Namespace) -> int:
    """Update all tools in the Juff environment."""
    manager = JuffVenvManager()

    print("Updating Juff tools...")
    try:
        manager.update_all_packages()
        print("All tools updated successfully!")
        return 0
    except Exception as e:
        print(f"Error updating tools: {e}", file=sys.stderr)
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """Show version information."""
    print(f"juff {__version__}")

    manager = JuffVenvManager()
    if manager.is_initialized():
        if args.verbose:
            print("\nInstalled packages:")
            print(manager.list_installed_packages())
        else:
            # Show key tool versions
            print("\nKey tools:")
            result = manager.run_tool("flake8", ["--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  flake8: {result.stdout.strip()}")

            result = manager.run_tool("black", ["--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  black: {result.stdout.strip()}")

            result = manager.run_tool("isort", ["--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.strip().split("\n")[0]
                print(f"  isort: {version_line}")
    else:
        print("\nJuff environment not initialized. Run 'juff init' first.")

    return 0


def cmd_rule(args: argparse.Namespace) -> int:
    """Show information about a rule."""
    from juff.config import RULE_PREFIX_MAPPING

    code = args.code.upper()

    # Find matching prefix - must match prefix exactly and be followed by a digit
    tool = None
    matched_prefix = None

    # Sort prefixes by length (longest first) to match most specific first
    sorted_prefixes = sorted(RULE_PREFIX_MAPPING.keys(), key=len, reverse=True)

    for prefix in sorted_prefixes:
        if code == prefix:
            # Exact match
            tool = RULE_PREFIX_MAPPING[prefix]
            matched_prefix = prefix
            break
        elif code.startswith(prefix) and len(code) > len(prefix):
            # Must be followed by a digit for valid rule codes
            next_char = code[len(prefix)]
            if next_char.isdigit():
                tool = RULE_PREFIX_MAPPING[prefix]
                matched_prefix = prefix
                break

    if tool:
        print(f"Rule: {code}")
        print(f"Tool: {tool}")
        print(f"\nThis rule is provided by the '{tool}' package.")
        print(f"For detailed documentation, refer to the {tool} documentation.")
    else:
        print(f"Unknown rule: {code}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for Juff CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Load configuration
    config = JuffConfig(config_path=args.config if hasattr(args, "config") else None)
    config.load()

    # Dispatch to command handler
    handlers = {
        "check": lambda: cmd_check(args, config),
        "format": lambda: cmd_format(args, config),
        "init": lambda: cmd_init(args),
        "clean": lambda: cmd_clean(args),
        "update": lambda: cmd_update(args),
        "version": lambda: cmd_version(args),
        "rule": lambda: cmd_rule(args),
    }

    handler = handlers.get(args.command)
    if handler:
        return handler()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
