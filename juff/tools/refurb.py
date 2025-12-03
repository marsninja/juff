"""Refurb tool wrapper."""

import re
from pathlib import Path

from juff.tools.base import BaseTool


class RefurbTool(BaseTool):
    """Wrapper for refurb linter (FURB rules)."""

    name = "refurb"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build refurb command-line arguments.

        Args:
            paths: Paths to check.
            fix: Not applicable for refurb (it doesn't auto-fix).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        if self.config:
            # Get selected and ignored rules
            selected = self.config.get_selected_rules()
            ignored = self.config.get_ignored_rules()

            # Filter to FURB rules
            furb_enable = [r for r in selected if r.startswith("FURB")]
            furb_disable = [r for r in ignored if r.startswith("FURB")]

            if furb_enable and "ALL" not in selected:
                for rule in furb_enable:
                    args.extend(["--enable", rule])

            if furb_disable:
                for rule in furb_disable:
                    args.extend(["--disable", rule])

            # Python version
            target_version = self.config.get_target_version()
            # Convert py311 -> 3.11
            if target_version.startswith("py"):
                major = target_version[2]
                minor = target_version[3:]
                python_version = f"{major}.{minor}"
                args.extend(["--python-version", python_version])

        if extra_args:
            args.extend(extra_args)

        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse refurb output.

        Args:
            stdout: Standard output from refurb.
            stderr: Standard error from refurb.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # Count lines matching refurb output format
        # Format: path:line:col [FURBxxx]: message
        combined = stdout + stderr
        pattern = r"^.+:\d+:\d+ \[FURB\d+\]"
        issues = len(re.findall(pattern, combined, re.MULTILINE))
        return issues, 0  # refurb doesn't auto-fix
