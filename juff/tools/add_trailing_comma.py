"""add-trailing-comma tool wrapper."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool, ToolResult


class AddTrailingCommaTool(BaseTool):
    """Wrapper for add-trailing-comma."""

    name = "add-trailing-comma"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """Build add-trailing-comma command-line arguments.

        Args:
            paths: Paths to check/fix.
            fix: Whether to apply fixes. Note: add-trailing-comma always modifies.
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Get config values
        if self.config:
            target_version = self.config.get_target_version()
            if target_version:
                # Convert py311 -> --py311-plus
                version_flag = f"--{target_version}-plus"
                args.append(version_flag)
        else:
            args.append("--py311-plus")

        if extra_args:
            args.extend(extra_args)

        # Add paths - add-trailing-comma works on individual files
        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse add-trailing-comma output.

        Args:
            stdout: Standard output from add-trailing-comma.
            stderr: Standard error from add-trailing-comma.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # add-trailing-comma shows "Rewriting" for files it modifies
        rewritten = len(re.findall(r"Rewriting", combined))

        return rewritten, rewritten

    def run(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: Optional[list[str]] = None,
    ) -> ToolResult:
        """Run add-trailing-comma on the specified paths.

        Note: add-trailing-comma doesn't have a native check mode,
        so we handle this by not running in check-only mode.

        Args:
            paths: Paths to check/fix.
            fix: Whether to apply fixes.
            extra_args: Additional arguments.

        Returns:
            ToolResult with the outcome.
        """
        if not fix:
            # In check-only mode, we can't really run add-trailing-comma
            # without modifying files, so return empty result
            return ToolResult(
                tool_name=self.name,
                returncode=0,
                stdout="",
                stderr="",
                files_processed=0,
                issues_found=0,
                issues_fixed=0,
            )

        # Collect all Python files
        all_files = []
        for path in paths:
            if path.is_file() and path.suffix == ".py":
                all_files.append(path)
            elif path.is_dir():
                all_files.extend(path.rglob("*.py"))

        if not all_files:
            return ToolResult(
                tool_name=self.name,
                returncode=0,
                stdout="",
                stderr="",
                files_processed=0,
                issues_found=0,
                issues_fixed=0,
            )

        # Build args for all files
        args = self.build_args(all_files, fix=fix, extra_args=extra_args)

        result = self.venv_manager.run_tool(
            self.name,
            args,
            capture_output=True,
            text=True,
        )

        issues_found, issues_fixed = self.parse_output(result.stdout, result.stderr)

        return ToolResult(
            tool_name=self.name,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            files_processed=len(all_files),
            issues_found=issues_found,
            issues_fixed=issues_fixed,
        )
