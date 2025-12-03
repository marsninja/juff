"""Pydoclint tool wrapper."""

import re
from pathlib import Path

from juff.tools.base import BaseTool


class PydoclintTool(BaseTool):
    """Wrapper for pydoclint linter (DOC rules)."""

    name = "pydoclint"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build pydoclint command-line arguments.

        Args:
            paths: Paths to check.
            fix: Not applicable for pydoclint (it doesn't auto-fix).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        if self.config:
            # Get pydoclint-specific config
            lint_config = self.config.get_lint_config()
            pydoclint_config = lint_config.get("pydoclint", {})

            # Docstring style (google, numpy, sphinx)
            style = pydoclint_config.get("style", "google")
            args.extend(["--style", style])

            # Check argument types
            if pydoclint_config.get("check-arg-types", True):
                args.append("--check-arg-types=True")
            else:
                args.append("--check-arg-types=False")

            # Check return types
            if pydoclint_config.get("check-return-types", True):
                args.append("--check-return-types=True")
            else:
                args.append("--check-return-types=False")

            # Exclude patterns - pydoclint uses --exclude
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                args.extend(["--exclude", ",".join(excludes)])

        if extra_args:
            args.extend(extra_args)

        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse pydoclint output.

        Args:
            stdout: Standard output from pydoclint.
            stderr: Standard error from pydoclint.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # Count lines matching pydoclint output format
        # Format: path:line: DOCxxx: message
        combined = stdout + stderr
        pattern = r"^.+:\d+: DOC\d+"
        issues = len(re.findall(pattern, combined, re.MULTILINE))
        return issues, 0  # pydoclint doesn't auto-fix
