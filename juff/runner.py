"""Runner module for Juff.

This module orchestrates the underlying tools to perform linting and formatting
operations, aggregating results and handling tool coordination.
"""

from pathlib import Path
from typing import Optional

from juff.config import JuffConfig
from juff.tools.add_trailing_comma import AddTrailingCommaTool
from juff.tools.base import ToolResult
from juff.tools.black import BlackTool
from juff.tools.docformatter import DocformatterTool
from juff.tools.flake8 import AutoflakeTool, Flake8Tool
from juff.tools.flynt import FlyntTool
from juff.tools.isort import IsortTool
from juff.tools.pyupgrade import PyupgradeTool
from juff.venv_manager import JuffVenvManager


class JuffRunner:
    """Orchestrates Juff tools for linting and formatting."""

    def __init__(
        self,
        config: JuffConfig | None = None,
        venv_manager: JuffVenvManager | None = None,
    ):
        """Initialize the runner.

        Args:
            config: Juff configuration. If None, loads from default locations.
            venv_manager: Venv manager instance. If None, creates default.
        """
        self.config = config or JuffConfig()
        self.venv_manager = venv_manager or JuffVenvManager()

        # Initialize tools
        self.flake8 = Flake8Tool(self.venv_manager, self.config)
        self.autoflake = AutoflakeTool(self.venv_manager, self.config)
        self.black = BlackTool(self.venv_manager, self.config)
        self.isort = IsortTool(self.venv_manager, self.config)
        self.pyupgrade = PyupgradeTool(self.venv_manager, self.config)
        self.flynt = FlyntTool(self.venv_manager, self.config)
        self.docformatter = DocformatterTool(self.venv_manager, self.config)
        self.add_trailing_comma = AddTrailingCommaTool(self.venv_manager, self.config)

    def lint(self, paths: list[Path], fix: bool = False) -> list[ToolResult]:
        """Run linting on the specified paths.

        Args:
            paths: Paths to lint.
            fix: Whether to apply auto-fixes.

        Returns:
            List of ToolResult objects from each tool.
        """
        # Ensure venv is initialized
        self.venv_manager.ensure_initialized()

        # Filter excluded files
        filtered_paths = self._filter_excluded_paths(paths, mode="lint")
        if not filtered_paths:
            return []

        results = []

        # Determine which tools to run based on selected rules
        tools_needed = self.config.get_tools_for_rules()
        selected_rules = self.config.get_selected_rules()

        # If fixing, run fix tools first in proper order
        if fix:
            # 1. autoflake - remove unused imports/variables (F401, F841)
            result = self.autoflake.run(filtered_paths, fix=True)
            results.append(result)

            # 2. pyupgrade - upgrade Python syntax (UP rules)
            if "pyupgrade" in tools_needed or "UP" in selected_rules:
                result = self.pyupgrade.run(filtered_paths, fix=True)
                results.append(result)

            # 3. flynt - convert to f-strings (also UP031, UP032)
            if "pyupgrade" in tools_needed or "UP" in selected_rules:
                try:
                    result = self.flynt.run(filtered_paths, fix=True)
                    results.append(result)
                except FileNotFoundError:
                    pass  # flynt not installed, skip

            # 4. add-trailing-comma (COM rules)
            if "COM" in selected_rules or any(r.startswith("COM") for r in selected_rules):
                try:
                    result = self.add_trailing_comma.run(filtered_paths, fix=True)
                    results.append(result)
                except FileNotFoundError:
                    pass  # add-trailing-comma not installed, skip

        # Always run flake8 for linting (it's the core linter)
        if "flake8" in tools_needed or not tools_needed:
            result = self.flake8.run(filtered_paths, fix=False)
            results.append(result)

        # Run pyupgrade in check mode if not fixing but UP rules selected
        if not fix and "pyupgrade" in tools_needed:
            result = self.pyupgrade.run(filtered_paths, fix=False)
            results.append(result)

        return results

    def _filter_excluded_paths(
        self, paths: list[Path], mode: str | None = None
    ) -> list[Path]:
        """Filter out excluded paths based on config.

        Args:
            paths: List of paths to filter.
            mode: Optional mode ('lint' or 'format') to include section-specific excludes.

        Returns:
            List of paths that are not excluded.
        """
        filtered = []
        for path in paths:
            if path.is_file():
                if not self.config.is_file_excluded(path, mode=mode):
                    filtered.append(path)
            elif path.is_dir():
                # For directories, we'll let the tools handle exclusion
                # but we can still filter at the top level
                if not self.config.is_file_excluded(path, mode=mode):
                    filtered.append(path)
        return filtered if filtered else paths  # Return original if all filtered

    def format(self, paths: list[Path], check_only: bool = False) -> list[ToolResult]:
        """Run formatting on the specified paths.

        Args:
            paths: Paths to format.
            check_only: If True, only check without applying changes.

        Returns:
            List of ToolResult objects from each tool.
        """
        # Ensure venv is initialized
        self.venv_manager.ensure_initialized()

        # Filter excluded files
        filtered_paths = self._filter_excluded_paths(paths, mode="format")
        if not filtered_paths:
            return []

        results = []
        selected_rules = self.config.get_selected_rules()

        # Run isort first (import sorting) - if I rules selected
        if "I" in selected_rules or any(r.startswith("I") for r in selected_rules) or not selected_rules:
            result = self.isort.run(filtered_paths, fix=not check_only)
            results.append(result)

        # Run black (code formatting)
        result = self.black.run(filtered_paths, fix=not check_only)
        results.append(result)

        # Run docformatter if D rules selected and fixing
        if not check_only and ("D" in selected_rules or any(r.startswith("D") for r in selected_rules)):
            try:
                result = self.docformatter.run(filtered_paths, fix=True)
                results.append(result)
            except FileNotFoundError:
                pass  # docformatter not installed, skip

        return results

    def check_and_format(
        self, paths: list[Path], fix: bool = False
    ) -> list[ToolResult]:
        """Run both linting and formatting.

        Args:
            paths: Paths to check and format.
            fix: Whether to apply fixes and formatting.

        Returns:
            List of ToolResult objects from all tools.
        """
        results = []

        # Format first (if fixing)
        if fix:
            results.extend(self.format(paths, check_only=False))

        # Then lint
        results.extend(self.lint(paths, fix=fix))

        # If not fixing, also check formatting
        if not fix:
            results.extend(self.format(paths, check_only=True))

        return results


def run_check(
    paths: list[Path],
    fix: bool = False,
    config_path: Path | None = None,
) -> int:
    """Convenience function to run linting checks.

    Args:
        paths: Paths to check.
        fix: Whether to apply fixes.
        config_path: Optional path to configuration file.

    Returns:
        Exit code (0 if no issues, 1 if issues found).
    """
    config = JuffConfig(config_path=config_path)
    config.load()

    runner = JuffRunner(config=config)
    results = runner.lint(paths, fix=fix)

    total_issues = sum(r.issues_found for r in results)
    return 0 if total_issues == 0 else 1


def run_format(
    paths: list[Path],
    check_only: bool = False,
    config_path: Path | None = None,
) -> int:
    """Convenience function to run formatting.

    Args:
        paths: Paths to format.
        check_only: If True, only check without applying changes.
        config_path: Optional path to configuration file.

    Returns:
        Exit code (0 if no changes needed, 1 if changes needed/made).
    """
    config = JuffConfig(config_path=config_path)
    config.load()

    runner = JuffRunner(config=config)
    results = runner.format(paths, check_only=check_only)

    total_issues = sum(r.issues_found for r in results)
    return 0 if total_issues == 0 else 1
