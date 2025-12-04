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

            # Exclude patterns - black uses regex, not glob
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                # Convert glob patterns to regex patterns for black
                regex_patterns = []
                for pattern in excludes:
                    regex = self._glob_to_regex(pattern)
                    regex_patterns.append(regex)
                if regex_patterns:
                    exclude_pattern = "|".join(regex_patterns)
                    args.extend(["--exclude", exclude_pattern])

        if extra_args:
            args.extend(extra_args)

        # Add paths
        args.extend(str(p) for p in paths)

        return args

    def _glob_to_regex(self, pattern: str) -> str:
        """Convert a glob pattern to a regex pattern for black.

        Args:
            pattern: Glob pattern (e.g., "vendor/", "**/vendor/*", "*.pyc").

        Returns:
            Regex pattern string.
        """
        # Remove leading/trailing slashes for matching
        pattern = pattern.strip("/")

        # Handle common glob patterns
        if pattern.endswith("/**"):
            # "dir/**" -> match dir and anything under it
            dir_part = pattern[:-3]
            return rf"(^|/){re.escape(dir_part)}(/|$)"
        elif "**" in pattern:
            # "**/pattern" or "prefix/**/suffix" - match across directories
            parts = pattern.split("**/")
            regex_parts = [re.escape(p).replace(r"\*", "[^/]*") for p in parts]
            return ".*".join(regex_parts)
        elif pattern.endswith("/"):
            # "dir/" -> match directory
            dir_part = pattern[:-1]
            return rf"(^|/){re.escape(dir_part)}(/|$)"
        elif "*" in pattern:
            # Simple glob with wildcards
            regex = re.escape(pattern).replace(r"\*", "[^/]*")
            return rf"(^|/){regex}$"
        else:
            # Literal path component
            return rf"(^|/){re.escape(pattern)}(/|$)"

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse black output.

        Args:
            stdout: Standard output from black.
            stderr: Standard error from black.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # Try to parse the summary line first (e.g., "76 files reformatted, 364 files left unchanged.")
        summary_match = re.search(r"(\d+) files? reformatted", combined)
        if summary_match:
            reformatted = int(summary_match.group(1))
            return reformatted, reformatted

        # Check for "would reformat" (check mode)
        would_match = re.search(r"(\d+) files? would be reformatted", combined)
        if would_match:
            would_reformat = int(would_match.group(1))
            return would_reformat, 0

        # Fallback: count individual file lines
        would_reformat = len(re.findall(r"would reformat", combined))
        reformatted = len(re.findall(r"reformatted", combined))

        issues_found = would_reformat + reformatted
        issues_fixed = reformatted

        return issues_found, issues_fixed
