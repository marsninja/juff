"""Base class for tool wrappers."""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from juff.config import JuffConfig
    from juff.venv_manager import JuffVenvManager


class ToolResult:
    """Result from running a tool."""

    def __init__(
        self,
        tool_name: str,
        returncode: int,
        stdout: str,
        stderr: str,
        files_processed: int = 0,
        issues_found: int = 0,
        issues_fixed: int = 0,
    ):
        """Initialize tool result.

        Args:
            tool_name: Name of the tool that was run.
            returncode: Exit code from the tool.
            stdout: Standard output from the tool.
            stderr: Standard error from the tool.
            files_processed: Number of files processed.
            issues_found: Number of issues found.
            issues_fixed: Number of issues fixed (if fix mode).
        """
        self.tool_name = tool_name
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.files_processed = files_processed
        self.issues_found = issues_found
        self.issues_fixed = issues_fixed

    @property
    def success(self) -> bool:
        """Check if the tool ran successfully (no issues found)."""
        return self.returncode == 0

    def __repr__(self) -> str:
        return (
            f"ToolResult({self.tool_name}, rc={self.returncode}, "
            f"issues={self.issues_found}, fixed={self.issues_fixed})"
        )


class BaseTool(ABC):
    """Base class for tool wrappers."""

    name: str = "base"
    mode: str = "lint"  # Default mode for exclude patterns ("lint" or "format")

    def __init__(
        self, venv_manager: "JuffVenvManager", config: Optional["JuffConfig"] = None
    ):
        """Initialize the tool wrapper.

        Args:
            venv_manager: The Juff venv manager instance.
            config: Optional Juff configuration.
        """
        self.venv_manager = venv_manager
        self.config = config

    @abstractmethod
    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build command-line arguments for the tool.

        Args:
            paths: Paths to check/format.
            fix: Whether to apply fixes.
            extra_args: Additional arguments to pass.

        Returns:
            List of command-line arguments.
        """
        pass

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse tool output to extract issue counts.

        Args:
            stdout: Standard output from tool.
            stderr: Standard error from tool.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        pass

    def run(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> ToolResult:
        """Run the tool on the specified paths.

        Args:
            paths: Paths to check/format.
            fix: Whether to apply fixes.
            extra_args: Additional arguments to pass.

        Returns:
            ToolResult with the outcome.
        """
        args = self.build_args(paths, fix=fix, extra_args=extra_args)

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
            files_processed=len(paths),
            issues_found=issues_found,
            issues_fixed=issues_fixed,
        )

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value for this tool.

        Args:
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Configuration value.
        """
        if self.config is None:
            return default

        tool_config = self.config.config.get(self.name, {})
        return tool_config.get(key, default)
