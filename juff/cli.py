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
from juff.logging import LogLevel, debug, get_logger, set_up_logging
from juff.runner import JuffRunner
from juff.venv_manager import JuffVenvManager

# Module logger
logger = get_logger("cli")

# All output formats supported (matching ruff)
OUTPUT_FORMATS = [
    "text", "full", "concise", "grouped",  # Human-readable
    "json", "json-lines",                   # Structured
    "github", "gitlab", "azure",            # CI/CD
    "junit", "sarif", "rdjson", "pylint",   # Standard formats
]


def _warn_unimplemented(feature: str) -> None:
    """Warn about unimplemented feature."""
    print(f"warning: '{feature}' is not yet implemented in juff", file=sys.stderr)


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

    # === Global Options ===
    parser.add_argument(
        "--version",
        action="version",
        version=f"juff {__version__}",
    )

    parser.add_argument(
        "--config",
        action="append",
        dest="config_options",
        metavar="CONFIG_OPTION",
        help="Path to config file or inline TOML 'key=value' (can repeat)",
    )

    parser.add_argument(
        "--isolated",
        action="store_true",
        help="Ignore all configuration files",
    )

    # Logging level group (mutually exclusive at global level concept, but argparse
    # handles this per-subcommand, so we add them globally for convenience)
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Print diagnostics, but nothing else",
    )
    parser.add_argument(
        "-s", "--silent",
        action="store_true",
        help="Disable all logging (exit 1 if diagnostics found)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check command (linting)
    check_parser = subparsers.add_parser(
        "check",
        help="Run linting checks on files",
        description="Lint Python files using flake8 and plugins.",
    )
    _add_common_args(check_parser)

    # === Fixing Options ===
    check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix auto-fixable issues",
    )
    check_parser.add_argument(
        "--no-fix",
        action="store_true",
        help=argparse.SUPPRESS,  # Hidden, overrides --fix
    )
    check_parser.add_argument(
        "--unsafe-fixes",
        action="store_true",
        help="Include fixes that may not retain original intent",
    )
    check_parser.add_argument(
        "--no-unsafe-fixes",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    check_parser.add_argument(
        "--show-fixes",
        action="store_true",
        help="Show enumeration of all fixed lint violations",
    )
    check_parser.add_argument(
        "--no-show-fixes",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    check_parser.add_argument(
        "--diff",
        action="store_true",
        help="Output diffs for changed files",
    )
    check_parser.add_argument(
        "--fix-only",
        action="store_true",
        help="Apply fixes but don't report leftover violations",
    )
    check_parser.add_argument(
        "--no-fix-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    check_parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Run in watch mode, re-run on file changes",
    )
    check_parser.add_argument(
        "--add-noqa",
        nargs="?",
        const=True,
        default=False,
        metavar="REASON",
        help="Add noqa directives to silence violations",
    )

    # === Rule Selection ===
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
        "--extend-select",
        type=str,
        help="Additional rule codes to enable on top of selected",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--extend-ignore",
        type=str,
        help="Additional rule codes to ignore (deprecated)",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--per-file-ignores",
        type=str,
        help="File pattern to code mappings (pattern:codes,...)",
        metavar="PATTERN=CODES",
    )
    check_parser.add_argument(
        "--extend-per-file-ignores",
        type=str,
        help="Additional per-file ignores",
        metavar="PATTERN=CODES",
    )
    check_parser.add_argument(
        "--fixable",
        type=str,
        help="Rules eligible for auto-fix",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--unfixable",
        type=str,
        help="Rules ineligible for auto-fix",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--extend-fixable",
        type=str,
        help="Additional fixable rules",
        metavar="RULES",
    )
    check_parser.add_argument(
        "--extend-unfixable",
        type=str,
        help="Additional unfixable rules (deprecated)",
        metavar="RULES",
    )

    # === Output Options ===
    check_parser.add_argument(
        "--output-format",
        choices=OUTPUT_FORMATS,
        default="full",
        help="Output format for results",
    )
    check_parser.add_argument(
        "-o", "--output-file",
        type=Path,
        help="File to write output to",
        metavar="PATH",
    )

    # === File Selection ===
    check_parser.add_argument(
        "--extend-exclude",
        type=str,
        help="Additional exclusion patterns",
        metavar="PATTERNS",
    )
    check_parser.add_argument(
        "--respect-gitignore",
        action="store_true",
        default=True,
        help="Respect .gitignore exclusions (default)",
    )
    check_parser.add_argument(
        "--no-respect-gitignore",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    check_parser.add_argument(
        "--force-exclude",
        action="store_true",
        help="Enforce exclusions for explicitly passed paths",
    )
    check_parser.add_argument(
        "--no-force-exclude",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    # === Configuration ===
    check_parser.add_argument(
        "--preview",
        action="store_true",
        help="Enable preview mode (unstable rules/fixes)",
    )
    check_parser.add_argument(
        "--no-preview",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    check_parser.add_argument(
        "--dummy-variable-rgx",
        type=str,
        help="Regex matching dummy variables",
        metavar="REGEX",
    )

    # === Behavior ===
    check_parser.add_argument(
        "-e", "--exit-zero",
        action="store_true",
        help="Exit with status 0 even upon detecting violations",
    )
    check_parser.add_argument(
        "--exit-non-zero-on-fix",
        action="store_true",
        help="Exit non-zero if any files were modified via fix",
    )
    check_parser.add_argument(
        "--statistics",
        action="store_true",
        help="Show counts for every rule with violations",
    )
    check_parser.add_argument(
        "--stdin-filename",
        type=Path,
        help="Filename for stdin input",
        metavar="PATH",
    )
    check_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache reads",
    )
    check_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Path to cache directory",
        metavar="PATH",
    )
    check_parser.add_argument(
        "--extension",
        action="append",
        help="Map file extension to language (ext:lang)",
        metavar="EXT:LANG",
    )
    check_parser.add_argument(
        "--ignore-noqa",
        action="store_true",
        help="Ignore all noqa comments",
    )
    check_parser.add_argument(
        "--show-files",
        action="store_true",
        help="Show files that would be checked",
    )
    check_parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Show settings for a given file",
    )

    # Format command
    format_parser = subparsers.add_parser(
        "format",
        help="Format Python files",
        description="Format Python files using black and isort.",
    )
    _add_common_args(format_parser)

    # === Format Mode ===
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

    # === Configuration ===
    format_parser.add_argument(
        "--preview",
        action="store_true",
        help="Enable unstable formatting",
    )
    format_parser.add_argument(
        "--no-preview",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    format_parser.add_argument(
        "--range",
        type=str,
        help="Format specific range (line:col-line:col)",
        metavar="RANGE",
    )

    # === File Selection ===
    format_parser.add_argument(
        "--extend-exclude",
        type=str,
        help="Additional exclusion patterns",
        metavar="PATTERNS",
    )
    format_parser.add_argument(
        "--respect-gitignore",
        action="store_true",
        default=True,
        help="Respect .gitignore exclusions (default)",
    )
    format_parser.add_argument(
        "--no-respect-gitignore",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    format_parser.add_argument(
        "--force-exclude",
        action="store_true",
        help="Enforce exclusions for explicitly passed paths",
    )
    format_parser.add_argument(
        "--no-force-exclude",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    # === I/O ===
    format_parser.add_argument(
        "--stdin-filename",
        type=Path,
        help="Filename for stdin input",
        metavar="PATH",
    )
    format_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache reads",
    )
    format_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Path to cache directory",
        metavar="PATH",
    )
    format_parser.add_argument(
        "--extension",
        action="append",
        help="Map file extension to language (ext:lang)",
        metavar="EXT:LANG",
    )

    # === Exit Behavior ===
    format_parser.add_argument(
        "--exit-non-zero-on-format",
        action="store_true",
        help="Exit non-zero if any files were modified",
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
    version_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format",
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
        nargs="?",  # Make optional (mutually exclusive with --all)
        help="Rule code (e.g., E501, F401)",
    )
    rule_parser.add_argument(
        "--all",
        action="store_true",
        help="Show all rules",
    )
    rule_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    # === New Commands (ruff parity) ===

    # Config command
    config_cmd_parser = subparsers.add_parser(
        "config",
        help="List or describe configuration options",
        description="Show available configuration options and their values.",
    )
    config_cmd_parser.add_argument(
        "option",
        nargs="?",
        help="Specific config key to describe (e.g., lint.select)",
    )
    config_cmd_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    # Linter command
    linter_parser = subparsers.add_parser(
        "linter",
        help="List all supported upstream linters",
        description="Show all linters and their rule prefixes.",
    )
    linter_parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    # Server command (LSP)
    server_parser = subparsers.add_parser(
        "server",
        help="Run the language server",
        description="Start Juff as a language server (LSP).",
    )
    server_parser.add_argument(
        "--preview",
        action="store_true",
        help="Enable preview mode for LSP",
    )
    server_parser.add_argument(
        "--no-preview",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    # Analyze command with subcommands
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze code structure",
        description="Analyze Python code structure and dependencies.",
    )
    analyze_subparsers = analyze_parser.add_subparsers(
        dest="analyze_command",
        help="Analysis commands",
    )

    # analyze graph subcommand
    graph_parser = analyze_subparsers.add_parser(
        "graph",
        help="Generate import dependency map",
        description="Generate a map of Python file dependencies.",
    )
    graph_parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="Files or directories to analyze",
    )
    graph_parser.add_argument(
        "--direction",
        choices=["dependencies", "dependents"],
        default="dependencies",
        help="Direction of import map",
    )
    graph_parser.add_argument(
        "--detect-string-imports",
        action="store_true",
        help="Detect imports from string literals",
    )
    graph_parser.add_argument(
        "--preview",
        action="store_true",
        help="Enable preview mode",
    )
    graph_parser.add_argument(
        "--no-preview",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    graph_parser.add_argument(
        "--target-version",
        type=str,
        help="Minimum Python version (py37-py314)",
        metavar="VERSION",
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

    # Only print summary if there are issues (ruff-like behavior)
    # This prevents noisy output when pre-commit runs juff on multiple file batches
    if total_issues > 0:
        if args.fix:
            print(f"\nFound {total_issues} issue(s), fixed {total_fixed}.")
        else:
            print(f"\nFound {total_issues} issue(s).")

    return 1 if total_issues > total_fixed else 0


def cmd_format(args: argparse.Namespace, config: JuffConfig) -> int:
    """Run the format command."""
    import re

    runner = JuffRunner(config=config)

    # Override config with CLI args
    if args.line_length:
        config._config = config._config or {}
        config._config["line-length"] = args.line_length

    results = runner.format(args.paths, check_only=args.check)

    # Collect all output for parsing
    all_stdout = ""
    all_stderr = ""
    for result in results:
        all_stdout += result.stdout
        all_stderr += result.stderr

    combined = all_stdout + all_stderr

    # Show diff output if requested
    for result in results:
        if result.stdout and (args.diff or args.verbose):
            print(result.stdout, end="")

    if not args.quiet:
        if args.check:
            # Check mode - look for "would be reformatted"
            would_match = re.search(r"(\d+) files? would be reformatted", combined)
            unchanged_match = re.search(r"(\d+) files? (would be )?left unchanged", combined)

            would_reformat = int(would_match.group(1)) if would_match else 0
            unchanged = int(unchanged_match.group(1)) if unchanged_match else 0

            if would_reformat > 0:
                if unchanged > 0:
                    print(f"{would_reformat} file(s) would be reformatted, {unchanged} file(s) left unchanged.")
                else:
                    print(f"{would_reformat} file(s) would be reformatted.")
                return 1
            else:
                if unchanged > 0:
                    print(f"{unchanged} file(s) already formatted.")
                else:
                    print("All files are properly formatted!")
        else:
            # Fix mode - look for "reformatted"
            reformatted_match = re.search(r"(\d+) files? reformatted", combined)
            unchanged_match = re.search(r"(\d+) files? left unchanged", combined)

            reformatted = int(reformatted_match.group(1)) if reformatted_match else 0
            unchanged = int(unchanged_match.group(1)) if unchanged_match else 0

            if reformatted > 0:
                if unchanged > 0:
                    print(f"{reformatted} file(s) reformatted, {unchanged} file(s) left unchanged.")
                else:
                    print(f"{reformatted} file(s) reformatted.")
            else:
                if unchanged > 0:
                    print(f"{unchanged} file(s) left unchanged.")
                else:
                    print("No files needed reformatting.")

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
    import json

    output_format = getattr(args, "output_format", "text")

    if output_format == "json":
        version_data = {
            "version": __version__,
            "tools": {},
        }
        manager = JuffVenvManager()
        if manager.is_initialized():
            result = manager.run_tool("flake8", ["--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_data["tools"]["flake8"] = result.stdout.strip()
            result = manager.run_tool("black", ["--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_data["tools"]["black"] = result.stdout.strip()
            result = manager.run_tool("isort", ["--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_data["tools"]["isort"] = result.stdout.strip().split("\n")[0]
        print(json.dumps(version_data, indent=2))
    else:
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
    import json
    from juff.config import RULE_PREFIX_MAPPING

    # Handle --all flag
    if getattr(args, "all", False):
        if args.output_format == "json":
            rules_data = []
            for prefix, tool in sorted(RULE_PREFIX_MAPPING.items()):
                rules_data.append({"prefix": prefix, "tool": tool})
            print(json.dumps(rules_data, indent=2))
        else:
            print("Available rule prefixes:")
            print()
            for prefix, tool in sorted(RULE_PREFIX_MAPPING.items()):
                print(f"  {prefix:8} - {tool}")
        return 0

    # Require code if --all not provided
    if not args.code:
        print("error: Either provide a rule code or use --all", file=sys.stderr)
        return 1

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
        if args.output_format == "json":
            print(json.dumps({
                "code": code,
                "prefix": matched_prefix,
                "tool": tool,
            }, indent=2))
        else:
            print(f"Rule: {code}")
            print(f"Tool: {tool}")
            print(f"\nThis rule is provided by the '{tool}' package.")
            print(f"For detailed documentation, refer to the {tool} documentation.")
    else:
        print(f"Unknown rule: {code}")
        return 1

    return 0


# === New Command Handlers (ruff parity) ===

def cmd_config(args: argparse.Namespace) -> int:
    """Show configuration options."""
    import json

    # Define available config options
    CONFIG_OPTIONS = {
        "line-length": {"type": "int", "default": 88, "description": "Line length limit"},
        "target-version": {"type": "str", "default": "py311", "description": "Target Python version"},
        "indent-width": {"type": "int", "default": 4, "description": "Indentation width"},
        "preview": {"type": "bool", "default": False, "description": "Enable preview mode"},
        "fix": {"type": "bool", "default": False, "description": "Auto-fix by default"},
        "unsafe-fixes": {"type": "bool", "default": False, "description": "Enable unsafe fixes"},
        "exclude": {"type": "list", "default": [], "description": "Exclusion patterns"},
        "extend-exclude": {"type": "list", "default": [], "description": "Additional exclusion patterns"},
        "lint.select": {"type": "list", "default": ["E", "F", "W"], "description": "Rules to enable"},
        "lint.ignore": {"type": "list", "default": [], "description": "Rules to ignore"},
        "lint.fixable": {"type": "list", "default": ["ALL"], "description": "Rules eligible for fix"},
        "lint.unfixable": {"type": "list", "default": [], "description": "Rules ineligible for fix"},
        "lint.per-file-ignores": {"type": "dict", "default": {}, "description": "Per-file rule ignores"},
        "format.indent-style": {"type": "str", "default": "space", "description": "Indent style (space/tab)"},
        "format.quote-style": {"type": "str", "default": "double", "description": "Quote style"},
        "format.line-ending": {"type": "str", "default": "auto", "description": "Line ending style"},
    }

    if args.option:
        # Show specific option
        opt = args.option
        if opt in CONFIG_OPTIONS:
            info = CONFIG_OPTIONS[opt]
            if args.output_format == "json":
                print(json.dumps({opt: info}, indent=2))
            else:
                print(f"{opt}:")
                print(f"  Type: {info['type']}")
                print(f"  Default: {info['default']}")
                print(f"  Description: {info['description']}")
        else:
            print(f"Unknown config option: {opt}", file=sys.stderr)
            return 1
    else:
        # Show all options
        if args.output_format == "json":
            print(json.dumps(CONFIG_OPTIONS, indent=2))
        else:
            print("Available configuration options:")
            print()
            for opt, info in sorted(CONFIG_OPTIONS.items()):
                print(f"  {opt}")
                print(f"    Type: {info['type']}, Default: {info['default']}")
                print(f"    {info['description']}")
                print()

    return 0


def cmd_linter(args: argparse.Namespace) -> int:
    """Show supported linters."""
    import json
    from juff.config import RULE_PREFIX_MAPPING

    # Build linter info from RULE_PREFIX_MAPPING
    linters = {}
    for prefix, tool in RULE_PREFIX_MAPPING.items():
        if tool not in linters:
            linters[tool] = {"prefixes": [], "description": ""}
        linters[tool]["prefixes"].append(prefix)

    # Add descriptions
    descriptions = {
        "flake8": "Core linting (pyflakes, pycodestyle, mccabe) and plugins",
        "isort": "Import sorting",
        "black": "Code formatting",
        "pyupgrade": "Python syntax upgrades",
        "pylint": "Comprehensive Python linter",
        "pydoclint": "Docstring linting",
        "refurb": "Code modernization suggestions",
        "perflint": "Performance linting",
        "flynt": "F-string conversion",
        "ruff": "Ruff-specific rules (delegated)",
    }
    for tool in linters:
        linters[tool]["description"] = descriptions.get(tool, "")

    if args.output_format == "json":
        print(json.dumps(linters, indent=2))
    else:
        print("Supported linters:")
        print()
        for tool, info in sorted(linters.items()):
            prefixes = ", ".join(sorted(info["prefixes"]))
            print(f"  {tool}")
            print(f"    Prefixes: {prefixes}")
            if info["description"]:
                print(f"    {info['description']}")
            print()

    return 0


def cmd_server(args: argparse.Namespace) -> int:
    """Run the language server (LSP)."""
    _warn_unimplemented("server command (LSP)")
    print("The language server is not yet implemented in juff.", file=sys.stderr)
    print("For LSP support, consider using ruff-lsp or ruff server.", file=sys.stderr)
    return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run analysis commands."""
    if not hasattr(args, "analyze_command") or args.analyze_command is None:
        print("error: analyze requires a subcommand (e.g., 'analyze graph')", file=sys.stderr)
        return 1

    if args.analyze_command == "graph":
        return cmd_analyze_graph(args)

    print(f"Unknown analyze subcommand: {args.analyze_command}", file=sys.stderr)
    return 1


def cmd_analyze_graph(args: argparse.Namespace) -> int:
    """Generate import dependency graph."""
    _warn_unimplemented("analyze graph command")
    print("Import dependency analysis is not yet implemented in juff.", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point for Juff CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Determine log level from args (priority: silent > quiet > verbose > default)
    log_level = LogLevel.DEFAULT
    if getattr(args, "silent", False):
        log_level = LogLevel.SILENT
    elif getattr(args, "quiet", False):
        log_level = LogLevel.QUIET
    elif getattr(args, "verbose", False):
        log_level = LogLevel.VERBOSE

    # Initialize logging
    set_up_logging(log_level)

    debug("Juff version: %s", __version__, logger_name="cli")
    debug("Command: %s", args.command, logger_name="cli")
    debug("Working directory: %s", Path.cwd(), logger_name="cli")

    if args.command is None:
        parser.print_help()
        return 0

    # Determine the start directory for config search
    # If paths are provided, start from the first path (or its parent if it's a file)
    config_start_dir = None
    if hasattr(args, "paths") and args.paths:
        first_path = Path(args.paths[0]).resolve()
        if first_path.is_file():
            config_start_dir = first_path.parent
        elif first_path.is_dir():
            config_start_dir = first_path
        debug("Config search starting from target path: %s", config_start_dir, logger_name="cli")

    # Handle --isolated flag (ignore all config files)
    if getattr(args, "isolated", False):
        debug("Isolated mode: ignoring all configuration files", logger_name="cli")
        config = JuffConfig()
        config._config = {}
        config._project_root = Path.cwd()
    else:
        # Handle --config options (can be file path or inline TOML)
        config_path = None
        config_options = getattr(args, "config_options", None)
        if config_options:
            # Check if first option is a file path
            first_opt = config_options[0]
            if Path(first_opt).exists() or first_opt.endswith(".toml"):
                config_path = Path(first_opt)
                config_options = config_options[1:]  # Remaining are inline overrides

        config = JuffConfig(config_path=config_path)
        config.load(start_dir=config_start_dir)

        # Apply inline TOML overrides (not yet fully implemented)
        if config_options:
            for opt in config_options:
                if "=" in opt:
                    debug("Inline config override: %s", opt, logger_name="cli")
                    # Basic key=value parsing (full TOML parsing would be more complex)
                    _warn_unimplemented(f"inline config override: {opt}")

    # Dispatch to command handler
    handlers = {
        "check": lambda: cmd_check(args, config),
        "format": lambda: cmd_format(args, config),
        "init": lambda: cmd_init(args),
        "clean": lambda: cmd_clean(args),
        "update": lambda: cmd_update(args),
        "version": lambda: cmd_version(args),
        "rule": lambda: cmd_rule(args),
        # New commands (ruff parity)
        "config": lambda: cmd_config(args),
        "linter": lambda: cmd_linter(args),
        "server": lambda: cmd_server(args),
        "analyze": lambda: cmd_analyze(args),
    }

    handler = handlers.get(args.command)
    if handler:
        return handler()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
