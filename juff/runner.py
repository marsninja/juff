"""Runner module for Juff.

This module orchestrates the underlying tools to perform linting and formatting
operations, aggregating results and handling tool coordination.
"""

from pathlib import Path
from typing import Optional

from juff.config import JuffConfig, RUFF_ONLY_PREFIXES
from juff.logging import get_logger

# Module logger
logger = get_logger("runner")
from juff.tools.add_trailing_comma import AddTrailingCommaTool
from juff.tools.base import ToolResult
from juff.tools.black import BlackTool
from juff.tools.docformatter import DocformatterTool
from juff.tools.flake8 import AutoflakeTool, Flake8Tool
from juff.tools.flynt import FlyntTool
from juff.tools.isort import IsortTool
from juff.tools.perflint import PerflintTool
from juff.tools.pydoclint import PydoclintTool
from juff.tools.pylint import PylintTool
from juff.tools.pyupgrade import PyupgradeTool
from juff.tools.refurb import RefurbTool
from juff.tools.ruff import RuffTool
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

        # Initialize core tools
        self.flake8 = Flake8Tool(self.venv_manager, self.config)
        self.autoflake = AutoflakeTool(self.venv_manager, self.config)
        self.black = BlackTool(self.venv_manager, self.config)
        self.isort = IsortTool(self.venv_manager, self.config)
        self.pyupgrade = PyupgradeTool(self.venv_manager, self.config)
        self.flynt = FlyntTool(self.venv_manager, self.config)
        self.docformatter = DocformatterTool(self.venv_manager, self.config)
        self.add_trailing_comma = AddTrailingCommaTool(self.venv_manager, self.config)

        # Initialize standalone linters
        self.pylint = PylintTool(self.venv_manager, self.config)
        self.pydoclint = PydoclintTool(self.venv_manager, self.config)
        self.refurb = RefurbTool(self.venv_manager, self.config)
        self.perflint = PerflintTool(self.venv_manager, self.config)

        # Initialize ruff for ruff-only rules
        self.ruff = RuffTool(self.venv_manager, self.config)

    def lint(self, paths: list[Path], fix: bool = False) -> list[ToolResult]:
        """Run linting on the specified paths.

        Args:
            paths: Paths to lint.
            fix: Whether to apply auto-fixes.

        Returns:
            List of ToolResult objects from each tool.
        """
        logger.debug("Starting lint operation on %d path(s), fix=%s", len(paths), fix)

        # Ensure venv is initialized
        self.venv_manager.ensure_initialized()

        # Filter excluded files
        filtered_paths = self._filter_excluded_paths(paths, mode="lint")
        if not filtered_paths:
            logger.debug("No paths remaining after exclusion filter")
            return []

        logger.debug("Processing %d path(s) after exclusion filter", len(filtered_paths))

        results = []

        # Determine which tools to run based on selected rules
        tools_needed = self.config.get_tools_for_rules()
        selected_rules = self.config.get_selected_rules()
        logger.debug("Tools needed for selected rules: %s", ", ".join(sorted(tools_needed)) if tools_needed else "all")

        # If fixing, run fix tools first in proper order
        if fix:
            # 1. autoflake - remove unused imports/variables (F401, F841)
            result = self.autoflake.run(filtered_paths, fix=True)
            results.append(result)

            # 2. pyupgrade - upgrade Python syntax (UP rules)
            if "pyupgrade" in tools_needed or self._has_rule_prefix(selected_rules, "UP"):
                result = self.pyupgrade.run(filtered_paths, fix=True)
                results.append(result)

            # 3. flynt - convert to f-strings (FLY rules, also UP031, UP032)
            if "flynt" in tools_needed or self._has_rule_prefix(selected_rules, ("FLY", "UP")):
                try:
                    result = self.flynt.run(filtered_paths, fix=True)
                    results.append(result)
                except FileNotFoundError:
                    pass  # flynt not installed, skip

            # 4. add-trailing-comma (COM rules)
            if self._has_rule_prefix(selected_rules, "COM"):
                try:
                    result = self.add_trailing_comma.run(filtered_paths, fix=True)
                    results.append(result)
                except FileNotFoundError:
                    pass  # add-trailing-comma not installed, skip

            # 5. ruff fix for ruff-only rules
            if "ruff" in tools_needed or self._has_ruff_only_rules(selected_rules):
                try:
                    result = self.ruff.run(filtered_paths, fix=True)
                    results.append(result)
                except FileNotFoundError:
                    pass  # ruff not installed, skip

        # === Run linters ===

        # Core flake8 linting (handles most rules via plugins)
        if "flake8" in tools_needed or not tools_needed:
            result = self.flake8.run(filtered_paths, fix=False)
            results.append(result)

        # Pylint (PL rules)
        if "pylint" in tools_needed or self._has_rule_prefix(selected_rules, ("PLC", "PLE", "PLR", "PLW")):
            try:
                result = self.pylint.run(filtered_paths, fix=False)
                results.append(result)
            except FileNotFoundError:
                pass  # pylint not installed, skip

        # Pydoclint (DOC rules)
        if "pydoclint" in tools_needed or self._has_rule_prefix(selected_rules, "DOC"):
            try:
                result = self.pydoclint.run(filtered_paths, fix=False)
                results.append(result)
            except FileNotFoundError:
                pass  # pydoclint not installed, skip

        # Refurb (FURB rules)
        if "refurb" in tools_needed or self._has_rule_prefix(selected_rules, "FURB"):
            try:
                result = self.refurb.run(filtered_paths, fix=False)
                results.append(result)
            except FileNotFoundError:
                pass  # refurb not installed, skip

        # Perflint (PERF rules)
        if "perflint" in tools_needed or self._has_rule_prefix(selected_rules, "PERF"):
            try:
                result = self.perflint.run(filtered_paths, fix=False)
                results.append(result)
            except FileNotFoundError:
                pass  # perflint not installed, skip

        # Ruff for ruff-only rules (AIR, FAST, NPY, PGH, RUF)
        if "ruff" in tools_needed or self._has_ruff_only_rules(selected_rules):
            try:
                result = self.ruff.run(filtered_paths, fix=False)
                results.append(result)
            except FileNotFoundError:
                pass  # ruff not installed, skip

        # Run pyupgrade in check mode if not fixing but UP rules selected
        if not fix and "pyupgrade" in tools_needed:
            result = self.pyupgrade.run(filtered_paths, fix=False)
            results.append(result)

        return results

    def _has_rule_prefix(self, rules: list[str], prefixes: str | tuple[str, ...]) -> bool:
        """Check if any rule starts with the given prefix(es).

        Args:
            rules: List of rule codes.
            prefixes: Single prefix or tuple of prefixes to check.

        Returns:
            True if any rule matches.
        """
        if isinstance(prefixes, str):
            prefixes = (prefixes,)
        return any(r.startswith(prefixes) for r in rules) or "ALL" in rules

    def _has_ruff_only_rules(self, rules: list[str]) -> bool:
        """Check if any ruff-only rules are selected.

        Args:
            rules: List of rule codes.

        Returns:
            True if any ruff-only rule is selected.
        """
        if "ALL" in rules:
            return True
        return any(r.startswith(tuple(RUFF_ONLY_PREFIXES)) for r in rules)

    def _filter_excluded_paths(
        self, paths: list[Path], mode: str | None = None
    ) -> list[Path]:
        """Filter out excluded paths based on config.

        Expands directories to individual Python files and applies exclude
        patterns, similar to how ruff handles file discovery.

        Args:
            paths: List of paths to filter.
            mode: Optional mode ('lint' or 'format') to include section-specific excludes.

        Returns:
            List of non-excluded Python files.
        """
        # First, expand directories to individual files
        all_files = self._expand_paths(paths)
        logger.debug("Expanded %d path(s) to %d file(s)", len(paths), len(all_files))

        # Then filter based on exclude patterns
        filtered = []
        for file_path in all_files:
            if not self.config.is_file_excluded(file_path, mode=mode):
                filtered.append(file_path)

        logger.debug("After exclusion filter: %d file(s)", len(filtered))
        return filtered

    def _expand_paths(self, paths: list[Path]) -> list[Path]:
        """Expand directories to individual Python files.

        Args:
            paths: List of paths (files or directories).

        Returns:
            List of Python files.
        """
        include_patterns = self.config.get_include_patterns()
        files = []

        for path in paths:
            if path.is_file():
                # Check if file matches include patterns
                if self._matches_include(path, include_patterns):
                    files.append(path)
            elif path.is_dir():
                # Recursively find all Python files
                for file_path in path.rglob("*"):
                    if file_path.is_file() and self._matches_include(file_path, include_patterns):
                        files.append(file_path)

        return sorted(files)

    def _matches_include(self, file_path: Path, patterns: list[str]) -> bool:
        """Check if a file matches include patterns.

        Args:
            file_path: Path to check.
            patterns: List of include patterns (e.g., ["*.py", "*.pyi"]).

        Returns:
            True if file matches any include pattern.
        """
        import fnmatch
        name = file_path.name
        return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)

    def format(self, paths: list[Path], check_only: bool = False) -> list[ToolResult]:
        """Run formatting on the specified paths.

        Args:
            paths: Paths to format.
            check_only: If True, only check without applying changes.

        Returns:
            List of ToolResult objects from each tool.
        """
        logger.debug("Starting format operation on %d path(s), check_only=%s", len(paths), check_only)

        # Ensure venv is initialized
        self.venv_manager.ensure_initialized()

        # Filter excluded files
        filtered_paths = self._filter_excluded_paths(paths, mode="format")
        if not filtered_paths:
            logger.debug("No paths remaining after exclusion filter")
            return []

        logger.debug("Processing %d path(s) after exclusion filter", len(filtered_paths))

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
