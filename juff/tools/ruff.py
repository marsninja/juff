"""Ruff tool wrapper for ruff-only rules."""

import re
from pathlib import Path

from juff.tools.base import BaseTool

# Rule prefixes that are handled exclusively by ruff
RUFF_ONLY_PREFIXES = ("AIR", "FAST", "NPY", "PGH", "RUF")


class RuffTool(BaseTool):
    """Wrapper for ruff linter (ruff-only rules: AIR, FAST, NPY, PGH, RUF)."""

    name = "ruff"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build ruff command-line arguments.

        Args:
            paths: Paths to check.
            fix: Whether to apply auto-fixes.
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = ["check"]

        if fix:
            args.append("--fix")

        if self.config:
            # Get selected rules and filter to ruff-only
            selected = self.config.get_selected_rules()
            ignored = self.config.get_ignored_rules()

            # Filter to ruff-only rules
            ruff_select = []
            for rule in selected:
                if rule == "ALL":
                    ruff_select.extend(RUFF_ONLY_PREFIXES)
                    break
                if self._is_ruff_only_rule(rule):
                    ruff_select.append(rule)

            ruff_ignore = [r for r in ignored if self._is_ruff_only_rule(r)]

            if ruff_select:
                args.extend(["--select", ",".join(ruff_select)])
            else:
                # If no ruff-only rules selected, select all ruff-only prefixes
                # This ensures we only run ruff for its unique rules
                args.extend(["--select", ",".join(RUFF_ONLY_PREFIXES)])

            if ruff_ignore:
                args.extend(["--ignore", ",".join(ruff_ignore)])

            # Line length
            line_length = self.config.get_line_length()
            args.extend(["--line-length", str(line_length)])

            # Target version
            target_version = self.config.get_target_version()
            args.extend(["--target-version", target_version])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                for pattern in excludes:
                    args.extend(["--exclude", pattern])

        if extra_args:
            args.extend(extra_args)

        args.extend(str(p) for p in paths)

        return args

    def _is_ruff_only_rule(self, rule: str) -> bool:
        """Check if a rule is a ruff-only rule.

        Args:
            rule: Rule code.

        Returns:
            True if this is a ruff-only rule (AIR, FAST, NPY, PGH, RUF).
        """
        return any(rule.startswith(p) for p in RUFF_ONLY_PREFIXES)

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse ruff output.

        Args:
            stdout: Standard output from ruff.
            stderr: Standard error from ruff.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # Count lines matching ruff output format
        # Format: path:line:col: CODE message
        combined = stdout + stderr
        pattern = r"^.+:\d+:\d+: [A-Z]+\d+"
        issues = len(re.findall(pattern, combined, re.MULTILINE))

        # Check for fixed issues
        fixed_match = re.search(r"Fixed (\d+) error", combined)
        fixed = int(fixed_match.group(1)) if fixed_match else 0

        return issues, fixed
