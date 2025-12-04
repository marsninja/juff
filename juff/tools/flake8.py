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

            # flake8-annotations options
            ann_config = self.config.get_flake8_annotations_config()
            if ann_config.get("suppress-none-returning", False):
                args.append("--suppress-none-returning")
            if ann_config.get("suppress-dummy-args", False):
                args.append("--suppress-dummy-args")
            if ann_config.get("allow-untyped-defs", False):
                args.append("--allow-untyped-defs")
            if ann_config.get("allow-untyped-nested", False):
                args.append("--allow-untyped-nested")
            if ann_config.get("mypy-init-return", False):
                args.append("--mypy-init-return")

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

    def run(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> "ToolResult":
        """Run flake8 and filter output to only selected rules.

        Some flake8 plugins don't respect --select, so we filter the output
        to only include rules that match the selected rule prefixes.
        Also handles per-file-ignores since flake8 doesn't understand "ALL".
        """
        from juff.tools.base import ToolResult

        result = super().run(paths, fix=fix, extra_args=extra_args)

        # Filter stdout to only include selected rules
        if self.config:
            selected = self.config.get_selected_rules()
            ignored = self.config.get_ignored_rules()
            if selected:
                filtered_stdout = self._filter_output(result.stdout, selected, ignored)
                issues_found, _ = self.parse_output(filtered_stdout, result.stderr)
                return ToolResult(
                    tool_name=result.tool_name,
                    returncode=result.returncode,
                    stdout=filtered_stdout,
                    stderr=result.stderr,
                    files_processed=result.files_processed,
                    issues_found=issues_found,
                    issues_fixed=0,
                )

        return result

    def _filter_output(self, stdout: str, selected: list[str], ignored: list[str]) -> str:
        """Filter flake8 output to only include selected rules.

        Args:
            stdout: Raw flake8 output.
            selected: List of selected rule prefixes.
            ignored: List of ignored rule prefixes.

        Returns:
            Filtered output containing only selected (and not ignored) rules.
        """
        filtered_lines = []
        # Match lines like: path:line:col: CODE message
        pattern = re.compile(r"^(.+):(\d+):(\d+): ([A-Z]+\d*)(.*)$")

        for line in stdout.splitlines():
            match = pattern.match(line)
            if match:
                file_path = match.group(1)
                code = match.group(4)

                # Check per-file-ignores first (handles "ALL" properly)
                if self.config and self._is_rule_ignored_for_file(code, file_path):
                    continue

                # Check if code matches any selected prefix
                if self._code_matches_selection(code, selected, ignored):
                    filtered_lines.append(line)
            else:
                # Keep non-error lines (summaries, etc.)
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _is_rule_ignored_for_file(self, code: str, file_path: str) -> bool:
        """Check if a rule code should be ignored for a specific file.

        Args:
            code: Error code (e.g., 'E501', 'F401').
            file_path: Path to the file.

        Returns:
            True if the rule should be ignored for this file.
        """
        if not self.config:
            return False

        return self.config.is_rule_ignored_for_file(code, Path(file_path))

    def _code_matches_selection(self, code: str, selected: list[str], ignored: list[str]) -> bool:
        """Check if an error code matches the selection criteria.

        Args:
            code: Error code (e.g., 'E501', 'FBT001').
            selected: List of selected rule prefixes.
            ignored: List of ignored rule prefixes.

        Returns:
            True if the code should be included.
        """
        # First check if explicitly ignored
        for ignore in ignored:
            if self._prefix_matches_code(ignore, code):
                return False

        # Check if code matches any selected prefix
        for sel in selected:
            if sel == "ALL":
                return True
            if self._prefix_matches_code(sel, code):
                return True

        return False

    def _prefix_matches_code(self, prefix: str, code: str) -> bool:
        """Check if a rule prefix matches an error code.

        Single-letter prefixes (E, F, W, etc.) only match codes where
        the prefix is followed by a digit (e.g., E matches E501 but not ERA001).
        Multi-letter prefixes match as normal startswith.

        Special handling for flake8 plugins that use different namespaces than ruff:
        - E8xx (flake8-eradicate) maps to ERA in ruff
        - E7xx includes some codes not in ruff (E704)

        Args:
            prefix: Rule prefix (e.g., 'E', 'F', 'ANN', 'E501').
            code: Error code (e.g., 'E501', 'FBT001', 'ANN001').

        Returns:
            True if the prefix matches the code.
        """
        if code == prefix:
            return True

        if not code.startswith(prefix):
            return False

        # For single-letter prefixes, require next char to be a digit
        # This prevents 'F' from matching 'FBT001' (should only match 'F401')
        if len(prefix) == 1 and prefix.isalpha():
            if len(code) > 1:
                if not code[1].isdigit():
                    return False
                # Special case: E8xx codes are from flake8-eradicate (ERA in ruff)
                # Only match if 'ERA' or 'E8' is explicitly in the prefix
                if prefix == "E" and code.startswith("E8"):
                    return False  # Require 'ERA' or 'E8' to be explicitly selected
            else:
                return False

        return True

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
