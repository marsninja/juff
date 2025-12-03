"""Perflint tool wrapper.

Perflint is a pylint plugin that provides performance-related linting rules (PERF).
It runs through pylint with the perflint plugin loaded.
"""

import re
from pathlib import Path

from juff.tools.base import BaseTool


class PerflintTool(BaseTool):
    """Wrapper for perflint (PERF rules via pylint plugin)."""

    name = "pylint"  # Runs through pylint

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build pylint command-line arguments with perflint plugin.

        Args:
            paths: Paths to check.
            fix: Not applicable for perflint (it doesn't auto-fix).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = [
            "--load-plugins=perflint",
            "--output-format=text",
            "--msg-template={path}:{line}:{column}: {msg_id} {msg}",
            # Only enable perflint rules (W8xxx codes)
            "--disable=all",
            "--enable=W8",
        ]

        if self.config:
            # Get ignored PERF rules
            ignored = self.config.get_ignored_rules()
            perf_disable = [r for r in ignored if r.startswith("PERF")]

            if perf_disable:
                # Convert PERF to W8 codes
                w8_disable = [self._convert_to_w8_code(r) for r in perf_disable]
                args.extend(["--disable", ",".join(w8_disable)])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                for pattern in excludes:
                    args.extend(["--ignore-patterns", pattern])

        if extra_args:
            args.extend(extra_args)

        args.extend(str(p) for p in paths)

        return args

    def _convert_to_w8_code(self, rule: str) -> str:
        """Convert PERF rule to perflint W8 code.

        Args:
            rule: Ruff-style PERF code (e.g., PERF101).

        Returns:
            Perflint-style W8 code (e.g., W8101).
        """
        # PERF101 -> W8101
        if rule.startswith("PERF"):
            return "W8" + rule[4:]
        return rule

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse perflint/pylint output.

        Args:
            stdout: Standard output from pylint.
            stderr: Standard error from pylint.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # Count lines matching pylint W8 output format
        pattern = r"^.+:\d+:\d+: W8\d+"
        issues = len(re.findall(pattern, stdout, re.MULTILINE))
        return issues, 0  # perflint doesn't auto-fix
