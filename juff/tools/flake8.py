"""Flake8 tool wrapper."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool


class Flake8Tool(BaseTool):
    """Wrapper for flake8 linter."""

    name = "flake8"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """Build flake8 command-line arguments.

        Args:
            paths: Paths to check.
            fix: Not applicable for flake8 (use autoflake for fixes).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Get config values
        if self.config:
            line_length = self.config.get_line_length()
            args.extend(["--max-line-length", str(line_length)])

            # Build select/ignore from config
            selected = self.config.get_selected_rules()
            ignored = self.config.get_ignored_rules()

            if selected and "ALL" not in selected:
                # Filter to flake8-compatible rules (E, W, F, etc.)
                flake8_rules = [r for r in selected if self._is_flake8_rule(r)]
                if flake8_rules:
                    args.extend(["--select", ",".join(flake8_rules)])

            if ignored:
                flake8_ignores = [r for r in ignored if self._is_flake8_rule(r)]
                if flake8_ignores:
                    args.extend(["--ignore", ",".join(flake8_ignores)])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns()
            if excludes:
                args.extend(["--exclude", ",".join(excludes)])

            # Per-file ignores (flake8 native support)
            per_file_ignores = self.config.get_per_file_ignores()
            if per_file_ignores:
                # Format: --per-file-ignores=path:codes,path2:codes2
                pfi_parts = []
                for pattern, rules in per_file_ignores.items():
                    if rules:
                        rules_str = ",".join(rules)
                        pfi_parts.append(f"{pattern}:{rules_str}")
                if pfi_parts:
                    args.extend(["--per-file-ignores", ",".join(pfi_parts)])

            # flake8-annotations options
            if self.config.get_flake8_annotations_suppress_none_returning():
                args.append("--suppress-none-returning")

        # Add extra args
        if extra_args:
            args.extend(extra_args)

        # Add paths
        args.extend(str(p) for p in paths)

        return args

    def _is_flake8_rule(self, rule: str) -> bool:
        """Check if a rule is handled by flake8.

        Args:
            rule: Rule code.

        Returns:
            True if this is a flake8 rule.
        """
        # All rule prefixes handled by flake8 and its plugins
        flake8_prefixes = (
            "E",  # pycodestyle errors
            "W",  # pycodestyle warnings
            "F",  # pyflakes
            "C",  # mccabe complexity / flake8-comprehensions
            "C4",  # flake8-comprehensions
            "N",  # pep8-naming
            "B",  # flake8-bugbear
            "A",  # flake8-builtins
            "G",  # flake8-logging-format
            "S",  # flake8-bandit
            "T",  # flake8-debugger / flake8-print
            "T10",  # flake8-debugger
            "T20",  # flake8-print
            "D",  # flake8-docstrings
            "Q",  # flake8-quotes
            "ANN",  # flake8-annotations
            "SIM",  # flake8-simplify
            "PIE",  # flake8-pie
            "COM",  # flake8-commas
            "ERA",  # flake8-eradicate
            "EXE",  # flake8-executable
            "ISC",  # flake8-implicit-str-concat
            "INP",  # flake8-no-pep420
            "PT",  # flake8-pytest-style
            "RET",  # flake8-return
            "SLF",  # flake8-self
            "TID",  # flake8-tidy-imports
            "TCH",  # flake8-type-checking
            "PTH",  # flake8-use-pathlib
            "ASYNC",  # flake8-async
            "BLE",  # flake8-blind-except
            "FBT",  # flake8-boolean-trap
            "RSE",  # flake8-raise
            "INT",  # flake8-gettext
            "TRY",  # tryceratops
            "ARG",  # flake8-unused-arguments
            "DTZ",  # flake8-datetimez
            "EM",  # flake8-errmsg
            "FA",  # flake8-future-annotations
        )
        return any(rule.startswith(p) for p in flake8_prefixes)

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse flake8 output.

        Args:
            stdout: Standard output from flake8.
            stderr: Standard error from flake8.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # Count lines that match the flake8 output format
        # Format: path:line:col: code message
        pattern = r"^.+:\d+:\d+: [A-Z]\d+"
        issues = len(re.findall(pattern, stdout, re.MULTILINE))
        return issues, 0  # flake8 doesn't fix


class AutoflakeTool(BaseTool):
    """Wrapper for autoflake (fixes F401, F841)."""

    name = "autoflake"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """Build autoflake command-line arguments.

        Args:
            paths: Paths to check/fix.
            fix: Whether to apply fixes in-place.
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = [
            "--remove-all-unused-imports",
            "--remove-unused-variables",
        ]

        if fix:
            args.append("--in-place")
        else:
            args.append("--check")

        # Recursive by default
        args.append("--recursive")

        if extra_args:
            args.extend(extra_args)

        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse autoflake output.

        Args:
            stdout: Standard output from autoflake.
            stderr: Standard error from autoflake.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # autoflake shows files that would be changed
        # or have been changed
        issues = stdout.count("Removing")
        return issues, issues if "--in-place" in str(stdout + stderr) else 0
