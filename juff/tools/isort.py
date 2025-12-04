"""isort tool wrapper."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool


class IsortTool(BaseTool):
    """Wrapper for isort import sorter."""

    name = "isort"
    mode = "format"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build isort command-line arguments.

        Args:
            paths: Paths to check/sort.
            fix: Whether to apply sorting (True) or just check (False).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Check mode vs fix mode
        if not fix:
            args.append("--check-only")
            args.append("--diff")

        # Get config values
        if self.config:
            line_length = self.config.get_line_length()
            args.extend(["--line-length", str(line_length)])

            # Use black profile for compatibility
            format_config = self.config.get_format_config()
            if format_config.get("quote-style") == "double":
                args.append("--profile=black")

            # Known first-party packages from [lint.isort]
            # isort requires separate -p/--known-first-party for each package
            known_first_party = self.config.get_isort_known_first_party()
            if known_first_party:
                for pkg in known_first_party:
                    args.extend(["-p", pkg])

            # Known third-party packages from [lint.isort]
            known_third_party = self.config.get_isort_known_third_party()
            if known_third_party:
                for pkg in known_third_party:
                    args.extend(["-o", pkg])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                for exclude in excludes:
                    args.extend(["--skip", exclude])

        # Default to black profile for consistency
        if "--profile" not in str(args):
            args.append("--profile=black")

        if extra_args:
            args.extend(extra_args)

        # Add paths
        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse isort output.

        Args:
            stdout: Standard output from isort.
            stderr: Standard error from isort.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # Count files that would be/were modified
        would_sort = len(re.findall(r"would be modified", combined, re.IGNORECASE))
        sorted_files = len(re.findall(r"Fixing", combined))

        # Also check for "Skipped" and error messages
        errors = combined.count("ERROR")

        issues_found = would_sort + sorted_files + errors
        issues_fixed = sorted_files

        return issues_found, issues_fixed
