"""flynt tool wrapper - converts string formatting to f-strings."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool


class FlyntTool(BaseTool):
    """Wrapper for flynt (f-string converter)."""

    name = "flynt"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build flynt command-line arguments.

        Args:
            paths: Paths to check/convert.
            fix: Whether to apply conversions (True) or just check (False).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Check mode vs fix mode
        if not fix:
            args.append("--dry-run")
            args.append("--fail-on-change")

        # Get config values
        if self.config:
            line_length = self.config.get_line_length()
            args.extend(["--line-length", str(line_length)])

            # Get target version for transform limits
            target_version = self.config.get_target_version()
            if target_version:
                # flynt uses --transform-concats only for py36+
                pass  # Default behavior is fine

        # Verbose output for parsing
        args.append("--verbose")

        if extra_args:
            args.extend(extra_args)

        # Add paths
        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse flynt output.

        Args:
            stdout: Standard output from flynt.
            stderr: Standard error from flynt.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # flynt reports conversions made
        converted = len(re.findall(r"converted", combined, re.IGNORECASE))
        # In dry-run mode, it shows "would convert"
        would_convert = len(re.findall(r"would convert", combined, re.IGNORECASE))

        issues_found = converted + would_convert
        issues_fixed = converted

        return issues_found, issues_fixed
