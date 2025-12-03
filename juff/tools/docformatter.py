"""docformatter tool wrapper - formats docstrings."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool


class DocformatterTool(BaseTool):
    """Wrapper for docformatter (docstring formatter)."""

    name = "docformatter"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """Build docformatter command-line arguments.

        Args:
            paths: Paths to check/format.
            fix: Whether to apply formatting (True) or just check (False).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Check mode vs fix mode
        if fix:
            args.append("--in-place")
        else:
            args.append("--check")
            args.append("--diff")

        # Get config values
        if self.config:
            line_length = self.config.get_line_length()
            args.extend(["--wrap-summaries", str(line_length)])
            args.extend(["--wrap-descriptions", str(line_length)])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns()
            if excludes:
                for exclude in excludes:
                    args.extend(["--exclude", exclude])

        # Recursive by default
        args.append("--recursive")

        if extra_args:
            args.extend(extra_args)

        # Add paths
        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse docformatter output.

        Args:
            stdout: Standard output from docformatter.
            stderr: Standard error from docformatter.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # In check mode, docformatter shows files that need changes
        # by showing the diff
        needs_formatting = len(re.findall(r"^---\s+", combined, re.MULTILINE))
        # In fix mode, it shows "Fixing" or similar
        fixed = len(re.findall(r"reformatting", combined, re.IGNORECASE))

        issues_found = needs_formatting + fixed
        issues_fixed = fixed

        return issues_found, issues_fixed
