"""Black formatter tool wrapper."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool


class BlackTool(BaseTool):
    """Wrapper for Black code formatter."""

    name = "black"
    mode = "format"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build black command-line arguments.

        Args:
            paths: Paths to format.
            fix: Whether to apply formatting (True) or just check (False).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Check mode vs format mode
        if not fix:
            args.append("--check")
            args.append("--diff")

        # Get config values
        if self.config:
            line_length = self.config.get_line_length()
            args.extend(["--line-length", str(line_length)])

            target_version = self.config.get_target_version()
            if target_version:
                # Convert py311 -> py311, py310 -> py310, etc.
                py_version = target_version.replace("py", "py")
                args.extend(["--target-version", py_version])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                # Black uses regex for exclude
                exclude_pattern = "|".join(excludes)
                args.extend(["--exclude", exclude_pattern])

        # Only use quiet mode when fixing (not checking) - we need output for parsing
        if fix:
            args.append("--quiet")

        if extra_args:
            args.extend(extra_args)

        # Add paths
        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse black output.

        Args:
            stdout: Standard output from black.
            stderr: Standard error from black.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # Check for "would reformat" (check mode) or "reformatted" (fix mode)
        would_reformat = len(re.findall(r"would reformat", combined))
        reformatted = len(re.findall(r"reformatted", combined))

        issues_found = would_reformat + reformatted
        issues_fixed = reformatted

        return issues_found, issues_fixed
