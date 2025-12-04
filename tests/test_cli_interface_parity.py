"""Test CLI interface parity with ruff using spec file as source of truth."""

import argparse
import inspect
import json
from pathlib import Path
import pytest
from juff import cli
from juff.cli import create_parser

SPEC_FILE = Path(__file__).parent / "fixtures" / "ruff_cli_spec.json"
CLI_FILE = Path(cli.__file__)


def get_parser_flags(parser: argparse.ArgumentParser) -> set[str]:
    """Extract all option flags from a parser."""
    flags = {"--version"} if any(isinstance(a, argparse._VersionAction) for a in parser._actions) else set()
    for action in parser._actions:
        if action.option_strings:
            flags.update(action.option_strings)
    return flags


def get_subparser(parser: argparse.ArgumentParser, *commands: str) -> argparse.ArgumentParser | None:
    """Navigate to a (nested) subparser by command path."""
    for cmd in commands:
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction) and cmd in action.choices:
                parser = action.choices[cmd]
                break
        else:
            return None
    return parser


def extract_required_flags(spec_options: dict) -> set[str]:
    """Extract all flags from a spec options dict."""
    return {flag for opts in spec_options.values() if isinstance(opts, list) for opt in opts for flag in opt.get("flags", [])}


def find_flag_line(flag: str) -> int | None:
    """Find the line number in cli.py where a flag is defined."""
    source_lines = inspect.getsourcelines(cli)[0]
    search_terms = [f'"{flag}"', f"'{flag}'"]
    for i, line in enumerate(source_lines, start=1):
        if any(term in line for term in search_terms):
            return i
    return None


def validate_spec(parser: argparse.ArgumentParser, spec: dict) -> list[str]:
    """Validate parser against spec, return list of errors."""
    errors = []

    # Global options
    global_flags = get_parser_flags(parser)
    for opt in spec.get("global_options", {}).get("required", []):
        for flag in opt.get("flags", []):
            if flag not in global_flags:
                errors.append(f"global: {flag}")

    # Commands and their options
    for cmd, cmd_spec in spec.get("commands", {}).items():
        subparser = get_subparser(parser, cmd)
        if not subparser:
            errors.append(f"command: {cmd}")
            continue

        cmd_flags = get_parser_flags(subparser)
        for flag in extract_required_flags(cmd_spec.get("options", {})):
            if flag not in cmd_flags:
                errors.append(f"{cmd}: {flag}")

        # Nested subcommands
        for subcmd, subcmd_spec in cmd_spec.get("subcommands", {}).items():
            nested = get_subparser(parser, cmd, subcmd)
            if not nested:
                errors.append(f"subcommand: {cmd} {subcmd}")
                continue
            for flag in extract_required_flags(subcmd_spec.get("options", {})):
                if flag not in get_parser_flags(nested):
                    errors.append(f"{cmd} {subcmd}: {flag}")

    # Output formats
    for cmd, formats in spec.get("output_formats", {}).items():
        subparser = get_subparser(parser, cmd)
        if subparser:
            for action in subparser._actions:
                if "--output-format" in action.option_strings and action.choices:
                    for fmt in set(formats) - set(action.choices):
                        errors.append(f"{cmd} format: {fmt}")

    return errors


def test_cli_parity():
    """Validate juff CLI matches ruff spec."""
    with open(SPEC_FILE) as f:
        spec = json.load(f)

    errors = validate_spec(create_parser(), spec)
    assert not errors, f"Missing CLI elements:\n" + "\n".join(f"  - {e}" for e in errors)


def print_interface_report():
    """Print the CLI interface with source locations."""
    with open(SPEC_FILE) as f:
        spec = json.load(f)

    print(f"CLI Interface Report (source: {CLI_FILE.name})\n{'=' * 60}\n")

    # Global options
    print("GLOBAL OPTIONS")
    print("-" * 40)
    for opt in spec.get("global_options", {}).get("required", []):
        flags = ", ".join(opt.get("flags", []))
        line = find_flag_line(opt["flags"][0]) if opt.get("flags") else None
        loc = f"cli.py:{line}" if line else "not found"
        print(f"  {flags:<25} {loc}")

    # Commands
    for cmd, cmd_spec in spec.get("commands", {}).items():
        print(f"\n{cmd.upper()} COMMAND")
        print("-" * 40)

        for category, opts in cmd_spec.get("options", {}).items():
            if isinstance(opts, list) and opts:
                print(f"  [{category}]")
                for opt in opts:
                    flags = ", ".join(opt.get("flags", []))
                    line = find_flag_line(opt["flags"][0]) if opt.get("flags") else None
                    loc = f"cli.py:{line}" if line else "not found"
                    status = " (hidden)" if opt.get("hidden") else ""
                    print(f"    {flags:<23} {loc}{status}")

        # Subcommands
        for subcmd, subcmd_spec in cmd_spec.get("subcommands", {}).items():
            print(f"  [{subcmd} subcommand]")
            for category, opts in subcmd_spec.get("options", {}).items():
                if isinstance(opts, list):
                    for opt in opts:
                        flags = ", ".join(opt.get("flags", []))
                        line = find_flag_line(opt["flags"][0]) if opt.get("flags") else None
                        loc = f"cli.py:{line}" if line else "not found"
                        print(f"    {flags:<23} {loc}")

    # Summary
    parser = create_parser()
    errors = validate_spec(parser, spec)
    print(f"\n{'=' * 60}")
    print(f"Status: {'PASS' if not errors else 'FAIL'} ({len(errors)} missing)")
    if errors:
        print("Missing:", ", ".join(errors))


if __name__ == "__main__":
    print_interface_report()
