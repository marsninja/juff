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
        extra_args: list[str] | None = None,
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
            excludes = self.config.get_exclude_patterns(mode=self.mode)
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

            # Note: flake8-annotations options like suppress-none-returning
            # are config-file-only and cannot be passed via CLI

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
        # Sorted by specificity (longer prefixes first to avoid false matches)
        flake8_prefixes = (
            # Specific prefixes (must come before single-letter)
            "ASYNC",  # flake8-async
            "ANN",  # flake8-annotations
            "ARG",  # flake8-unused-arguments
            "BLE",  # flake8-blind-except
            "C90",  # mccabe complexity
            "C4",  # flake8-comprehensions
            "COM",  # flake8-commas
            "CPY",  # flake8-copyright
            "DJ",  # flake8-django
            "DTZ",  # flake8-datetimez
            "EM",  # flake8-errmsg
            "ERA",  # flake8-eradicate
            "EXE",  # flake8-executable
            "FA",  # flake8-future-annotations
            "FBT",  # flake8-boolean-trap
            "FIX",  # flake8-fixme
            "ICN",  # flake8-import-conventions
            "INP",  # flake8-no-pep420
            "INT",  # flake8-gettext
            "ISC",  # flake8-implicit-str-concat
            "LOG",  # flake8-logging
            "PD",  # pandas-vet
            "PIE",  # flake8-pie
            "PT",  # flake8-pytest-style
            "PTH",  # flake8-use-pathlib
            "PYI",  # flake8-pyi
            "RET",  # flake8-return
            "RSE",  # flake8-raise
            "SIM",  # flake8-simplify
            "SLF",  # flake8-self
            "SLOT",  # flake8-slots
            "T10",  # flake8-debugger
            "T20",  # flake8-print
            "TCH",  # flake8-type-checking
            "TD",  # flake8-todos
            "TID",  # flake8-tidy-imports
            "TRY",  # tryceratops
            "YTT",  # flake8-2020
            # Single-letter prefixes (must come last)
            "A",  # flake8-builtins
            "B",  # flake8-bugbear
            "C",  # mccabe (fallback for C without number)
            "D",  # flake8-docstrings
            "E",  # pycodestyle errors
            "F",  # pyflakes
            "G",  # flake8-logging-format
            "N",  # pep8-naming
            "Q",  # flake8-quotes
            "S",  # flake8-bandit
            "T",  # flake8-debugger / flake8-print (fallback)
            "W",  # pycodestyle warnings
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
        extra_args: list[str] | None = None,
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
