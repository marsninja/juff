"""pyupgrade tool wrapper."""

import re
from pathlib import Path
from typing import Optional

from juff.tools.base import BaseTool


class PyupgradeTool(BaseTool):
    """Wrapper for pyupgrade (Python syntax upgrader)."""

    name = "pyupgrade"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build pyupgrade command-line arguments.

        Args:
            paths: Paths to check/upgrade.
            fix: Whether to apply upgrades in-place.
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = []

        # Get target Python version from config
        if self.config:
            target_version = self.config.get_target_version()
            if target_version:
                # Convert py311 -> --py311-plus
                version_flag = f"--{target_version}-plus"
                args.append(version_flag)
        else:
            # Default to py311
            args.append("--py311-plus")

        # pyupgrade doesn't have a --check mode, it always shows what would change
        # We need to handle this differently - run without changes first to check

        if extra_args:
            args.extend(extra_args)

        # Add paths - pyupgrade works on individual files
        args.extend(str(p) for p in paths)

        return args

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse pyupgrade output.

        Args:
            stdout: Standard output from pyupgrade.
            stderr: Standard error from pyupgrade.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        combined = stdout + stderr

        # pyupgrade shows "Rewriting" for files it modifies
        rewritten = len(re.findall(r"Rewriting", combined))

        return rewritten, rewritten

    def run(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ):
        """Run pyupgrade on the specified paths.

        Note: pyupgrade doesn't have a native --check mode, so we handle
        check vs fix differently.

        Args:
            paths: Paths to check/upgrade.
            fix: Whether to apply upgrades.
            extra_args: Additional arguments.

        Returns:
            ToolResult with the outcome.
        """
        from juff.tools.base import ToolResult

        # Collect all Python files, respecting excludes
        all_files = []
        for path in paths:
            if path.is_file() and path.suffix == ".py":
                if not self.config or not self.config.is_file_excluded(
                    path, mode=self.mode
                ):
                    all_files.append(path)
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    if not self.config or not self.config.is_file_excluded(
                        py_file, mode=self.mode
                    ):
                        all_files.append(py_file)

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
            issues_fixed=issues_fixed if fix else 0,
        )
